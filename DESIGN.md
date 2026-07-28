# 🎶 DuetFlow 双端文件同步引擎 · 完整设计方案 (v2.0)

> **适用场景**：一台 Windows 台式机（主力工作站） + 一台 macOS 笔记本（移动办公）
> **网络环境**：局域网固定 IP（无需公网打洞，出差不触发同步）
> **同步方式**：手动触发（非自动后台调度），通过 SSH / SFTP 传输
> **设计目标**：三路内容合并 + 极致防误删 + 跨平台换行符无感 + 高性能比对

---

## 一、 核心模型：三路合并（Three-way Merge）

同步绝非简单的两路 `source -> target` 覆盖，而是基于**历史基线快照（Baseline）**的三路比对。
比对三方：**Windows 当前目录**、**Mac 当前目录**、**上一次成功同步时的状态（Baseline）**。

| 序号 | A (Windows) 相对基线 | B (Mac) 相对基线 | 状态判定 | 最终动作 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 未变 | 未变 | 一致 | 不动作 |
| 2 | 已修改 | 未变 | Win 是作者 | Win $\rightarrow$ Mac |
| 3 | 未变 | 已修改 | Mac 是作者 | Mac $\rightarrow$ Win |
| 4 | 已修改 | 已修改 | **冲突** | 两端保留，重命名为 `<name>_conflict_<timestamp>.<ext>` |
| 5 | 已删除 | 未变 | Win 主动删除 | Mac 上也移入隔离区 |
| 6 | 未变 | 已删除 | Mac 主动删除 | Win 上也移入隔离区 |
| 7 | 已修改 | 已删除 | **冲突** | 保留修改版本，标记冲突报告，不执行删除 |

> **核心价值**：“删除”被明确记为一种变更状态。归一化整理后旧文件不再永久残留；冲突可精确识别，绝不静默覆盖。

---

## 二、 四重防误删防护体系

针对自动化同步工具最臭名昭著的“误删/抹盘”事故，建立四层绝对防护：

1. **权威单主控（No-Direction）**：
   * 架构上彻底消灭“用户选择源/目标方向”的操作，消除“选反方向导致抹盘”。
   * 无论在 Mac 还是 Windows 上敲下命令，**合并决策引擎与 Baseline 权威存储永远在 Windows 端**。
2. **隔离区机制（Quarantine）**：
   * 任何“判删”文件**绝不直接物理删除**，统一 `mv` 到本地 `.sync_trash/<YYYYMMDD>/` 目录下。
   * 默认保留 30 天，超时且下一次同步仍判删才执行物理删除。30 天内 100% 可手动恢复。
3. **删除配额熔断（Circuit Breaker）**：
   * 单次待删文件数量 **> 总文件数 20%** 或 **> 50 个** 时，系统触发紧急熔断。
   * 立即中止本次同步，打印报警信息，不执行任何删除与传输操作。
4. **Dry-run 预检报告 + 人工确认**：
   * 执行前强制打印变动树报告（显示新增 X 个，修改 Y 个，隔离 Z 个，跳过 N 个）。
   * 用户回车确认后方可真实执行。

---

## 三、 分层比对策略（解决换行符、锁文件与 Office 动态时间戳）

### 1. 文件分类短路逻辑（修复换行符与 Size 冲突）
为了防止 Windows（`CRLF`）与 Mac（`LF`）因换行符导致的尺寸不一致问题，比对引擎按文件类型分流：

```text
               ┌──────── 文件类型判断 ────────┐
               │                            │
         【文本文件】                 【二进制文件】
  (在 text_extensions 中)       (Office/图片/编译产物等)
               │                            │
       1. 忽略 Size 短路             1. Size 比对 (不同 -> 修改)
               │                            │
       2. mtime 差 > 3s              2. mtime 差 > 3s
               │                            │
   3. 全量读取并替换换行符           3. 极速全量 xxhash 比对
      (\r\n -> \n) 再算 xxhash               │
               │                    (取消采样哈希，全量仅需 2ms)
    哈希相同 -> 判未修改                      │
    哈希不同 -> 判已修改              哈希相同 -> 判未修改
                                     哈希不同 -> 判已修改
```

### 2. 独占锁异常捕获（Word/Excel 打开状态）
扫描时对所有文件读取操作加 `try-except (PermissionError, OSError)`：
* 若文件被 Office 等软件独占锁住，标记为 `status: "SKIPPED_LOCKED"`。
* 本次同步**跳过该文件**（不传输、不删除、更新 Baseline 时保留上次状态），并在报告里打印 Warning。

---

## 四、 传输与架构（基于 Pure Python SFTP）

抛弃外部 `rsync.exe` 依赖，采用 Python 原生网络栈，解决 Windows 端路径格式转换与依赖缺失问题：

* **依赖库**：`paramiko` (SFTP/SSH) + `xxhash` + `pyyaml`
* **执行流程**：
  1. 两端 Python 扫描器各自生成本地 `FileManifest`（文件清单字典）。
  2. Mac 端清单经由 SFTP/SSH 传输给 Windows 主控端。
  3. Windows 本地内存运行三路合并，对比三方状态，输出 `ActionPlan`（动作清单）。
  4. 控制台打印 Dry-run 报告，等待用户确认。
  5. 用户确认后，Windows 端调用 `paramiko` SFTP 执行批量上传 (`put`)、下载 (`get`) 或本地/远程移入隔离区。

---

## 五、 网络与触发架构（局域网固定 IP）

* **网络配置**：Mac 绑定局域网固定 IP，Windows 开启 OpenSSH Server，两端配置 SSH 免密公钥互信。
* **双向发起，脑在 Windows**：
  * **在 Windows 端发起**：本地跑 Merge $\rightarrow$ 提示确认 $\rightarrow$ SFTP 读写 Mac。
  * **在 Mac 端发起**：通过 SSH 远程触发 Windows 上的引擎 `ssh desktop "python engine.py --client-mode"`，Windows 算好报告传回 Mac Terminal 显示，确认后由主控端驱动执行。

---

## 六、 排除规则（Exclude Policy）

核心原则：**只同步“工作区源码与文档”，绝不同步“版本历史、依赖产物与设备状态”**。

| 类别 | 排除项 | 处理原因 |
| :--- | :--- | :--- |
| 版本控制 | `**/.git`, `**/.git/**` | 绝对不同步！Git 历史靠 `git push/pull`，不同步对象库以防损坏 |
| AI Agent | `**/.cursor`, `**/.claude`, `**/.codebuddy` | 设备相关的本地上下文与工具状态 |
| 依赖/产物 | `**/node_modules`, `**/__pycache__`, `**/.venv` | 体积巨大且平台敏感，应由包管理器重建 |
| 密钥敏感 | `**/.env` | 避免明文密钥跨端同步泄漏 |
| 系统垃圾 | `**/.DS_Store`, `**/._*`, `**/Thumbs.db` | macOS / Windows 系统产生的隐藏元数据垃圾 |

---

## 七、 状态存储与“冷启动”保护

### 1. 基线存储格式
* 存储文件：`baseline.json.gz`（Gzip 压缩 JSON，体积几十 KB，传输秒级）。
* 数据结构：
  ```json
  {
    "version": "2.0",
    "updated_at": "2026-07-27T17:00:00",
    "files": {
      "src/main.py": {
        "size": 1024,
        "mtime": 1722000000.0,
        "hash": "a1b2c3d4e5f6...",
        "is_text": true
      }
    }
  }
  ```

### 2. 冷启动保护（Baseline 缺失/第一次运行）
* 若检测到 `baseline.json.gz` 不存在：
  * **自动禁止三路合并**（防止将已存在文件误判为删除）。
  * 强制切入 **初始化模式（`--init`）**：执行双向并集合并（A 有 B 无 $\rightarrow$ 拷给 B；B 有 A 无 $\rightarrow$ 拷给 A；两端都有 $\rightarrow$ 比较 mtime 保留最新的）。
  * 首次同步完成后，生成第一份 `baseline.json.gz`，解锁后续正常的三路合并。

---

## 八、 边界场景防护设计

1. **文件名大小写重命名（如 `Readme.md` $\rightarrow$ `README.md`）**：
   * 合并字典以 **小写路径（`path.lower()`）** 为 Key 进行比对。
   * 若小写 Key 相同但原始路径不同，判定为原地重命名（Rename），禁止执行“删旧推新”动作。
2. **文件名非法字符预检**：
   * 扫描时预检 Windows 禁用的特殊字符（`\ : * ? " < > |`）。若 Mac 端存在非法字符文件，单列入“跳过并报警清单”，不中断主流程。
3. **磁盘空间预估**：
   * 传输前计算 `transfer_list` 总体积，检查两端剩余磁盘空间，不足预留 10% 余量时直接熔断退出。

---

## 九、 配置文件管理与 SSH 免密机制

### 1. 配置文件安全隔离策略
* **`config.example.yaml`**：提交至 Git 仓库作为模板，包含完整默认设置。
* **`config.yaml`**：包含真实 IP/主机别名、工作区路径等敏感信息，列入 `.gitignore`，**严禁提交至版本库**。
* **缺配置自动补全**：程序启动时若检测到 `config.yaml` 不存在，将自动从 `config.example.yaml` 复制一份或者生成默认配置文件，并提示用户配置。

### 2. SSH 免密与 `~/.ssh/config` 解析
* **原生支持 `~/.ssh/config`**：使用 Paramiko 的 `SSHConfig()` 模块解析系统本地 SSH 配置文件。`ssh.host` 可直接填写在 `~/.ssh/config` 中定义的 Host 别名（如 `macbook`），系统自动读取对应的主机名、端口、用户名及密钥文件。
* **默认密钥免密认证**：默认优先使用 `~/.ssh/id_rsa` 进行公钥认证，无需在控制台手动输入密码。

### 3. 配置文件样例 (`config.example.yaml`)

```yaml
ssh:
  # 支持直接填 IP (如 "192.168.1.101") 或 ~/.ssh/config 中的 Host 别名 (如 "macbook")
  host: "192.168.1.101"
  port: 22
  user: "your_mac_username"
  # 私钥路径：缺省自动使用 ~/.ssh/id_rsa
  # key_path: "~/.ssh/id_rsa"

sync_paths:
  windows_root: "D:/Workspaces/Projects"
  mac_root: "/Users/your_mac_username/Workspaces/Projects"

exclude:
  - "**/.git"
  - "**/.git/**"
  - "**/.cursor"
  - "**/.claude"
  - "**/node_modules"
  - "**/__pycache__"
  - "**/.venv"
  - "**/.env"
  - "**/.DS_Store"
  - "**/._*"
  - "**/Thumbs.db"

text_extensions:
  - ".py"
  - ".md"
  - ".txt"
  - ".json"
  - ".yaml"
  - ".yml"
  - ".csv"
  - ".sh"
  - ".toml"
  - ".ini"

safety:
  quarantine_days: 30
  circuit_breaker:
    max_ratio: 0.20
    max_count: 50

baseline:
  authority: "desktop"
  file_name: "baseline.json.gz"
```

---

## 十、 目录架构规范 (Folder Architecture)

```text
DuetFlow/
├── assets/                                 # 静态图片与应用图标资源
│   ├── app_icon_source.png                 # 图标设计源图
│   ├── icon.ico                            # Windows 专用图标
│   ├── icon.icns                           # macOS 专用图标
│   ├── windows_master.png
│   └── ChatGPT Image 2026年7月28日 13_15_59 (1).af
├── duetflow/                               # 核心 Python 源码包
│   ├── __init__.py
│   ├── cli.py                              # macOS 审美 Rich 终端界面与 CLI 入口
│   ├── config.py                           # 配置文件读取、缺失自动补全、~/.ssh/config 解析
│   ├── scanner.py                          # 目录扫描器
│   ├── merge.py                            # 三路合并引擎
│   ├── trash.py                            # 隔离区与熔断安全盾
│   └── sftp.py                             # Paramiko SSH/SFTP 传输封装
├── scripts/                                # 运维与脚本工具
│   ├── generate_icons.py                   # 从源图生成双端图标 (.ico & .icns)
│   └── create_shortcut.py                  # 一键在两端桌面生成关联图标的快捷方式
├── config.example.yaml                     # 配置模板（被 git 追踪）
├── config.yaml                             # 用户本地配置（被 .gitignore 忽略，缺省自动生成）
├── .gitignore                              # Git 忽略配置
├── DESIGN.md                               # 设计方案文档 (v2.2)
├── README.md                               # 项目 Readme 说明
└── LICENSE                                 # 开源协议
```

---

## 十一、 双端图标、快捷方式与 macOS 级别 UI 审美设计

### 1. 双端 Icon 图标策略 (Dual-Platform Icons)
为了在 Windows 和 macOS 都能提供原生的视觉体验，采用“同一源图片，生成双端专用格式”方案：
* **源图片**：`assets/app_icon_source.png` (高清 1024x1024 PNG)。
* **生成脚本 (`scripts/generate_icons.py`)**：
  - 调用 `Pillow` 自动缩放并导出 **Windows 图标**：`assets/icon.ico` (含 16/32/48/64/128/256 复合分辨率)。
  - 自动缩放并导出 **macOS 图标**：`assets/icon.icns`（或 `icon_mac.png`），全面兼容 macOS Dock 栏与访达系统。

### 2. 一键生成桌面快捷方式 (`scripts/create_shortcut.py`)
软件提供快速部署脚本，用户在任意平台运行即可生成关联桌面图标的快捷方式：
* **Windows 端**：通过 WScript / COM 组件在桌面生成 `DuetFlow.lnk`，快捷方式关联 `assets/icon.ico` 图标。点击后自动拉起 Python 交互终端并运行引擎。
* **macOS 端**：在桌面生成具有执行权限的 `DuetFlow.command` 终端快捷方式，关联 `assets/icon.icns` 图标。

### 3. macOS 级别的精致 UI 审美规范 (macOS Design System)
作为一款高频使用的跨端同步工具，界面必须达到 macOS Human Interface Guidelines (HIG) 的极致审美标准：
* **控制台 UI (Rich CLI Engine)**：
  - **色彩调色盘**：使用 Apple 经典暗黑模式调色板（经典太空灰底色、柔和天蓝高亮、苹果成功绿 `RGB(52, 199, 89)`、警戒黄 `RGB(255, 204, 0)`）。
  - **卡片布局**：三路合并报告与配置文件提示一律使用 `Rich` 库的圆角边框面板（`Panel(box=ROUNDED)`）。
  - **微动画进度条**：使用光滑的块状分段进度条，并配合平滑动效，避免锯齿与繁杂字符。
* **图形界面扩展 (GUI Extension)**：
  - 若后续推出 GUI 模式，严格遵循 macOS 设计规范：大圆角半透明玻璃拟物质感 (Glassmorphism)、无缝支持浅色/深色主题动态切换、矢量图标与高对比度精细排版。

---

## 十二、 交付与落地节奏

1. **第一阶段（扫描与比对内核）**：
   * 实现本地与远程文件扫描器（含 Exclude 过滤、`PermissionError` 独占锁捕获、文本归一化 xxhash 计算）。
2. **第二阶段（三路合并引擎与 Baseline 管理）**：
   * 实现三路合并逻辑字典、`baseline.json.gz` 事务写与冷启动 `--init` 模式。
3. **第三阶段（防误删与安全盾）**：
   * 实现隔离区移动逻辑、熔断检查（20%/50个）、大小写同化检测、Dry-run 报告格式化输出。
4. **第四阶段（Paramiko SFTP 传输层与脚本工具）**：
   * 实现纯 Python SFTP 文件的批量传输与隔离区远程操作。
   * 完成 `scripts/generate_icons.py` 与 `scripts/create_shortcut.py` 双端部署工具。
5. **第五阶段（小范围真实目录验证）**：
   * 在测试文件夹跑通全部用例（新增、修改、冲突、主动删除、文件锁定、大小写重命名），验证无误后全量上线。

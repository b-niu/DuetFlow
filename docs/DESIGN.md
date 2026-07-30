# DuetFlow 双端文件同步引擎设计方案

## 一、 核心模型：三路合并（Three-way Merge）

同步机制基于历史基线快照（Baseline）执行三路比对。
比对三方包括：Windows 当前目录、macOS 当前目录及历史同步快照（Baseline）。

| 序号 | Windows 相对基线 | macOS 相对基线 | 状态判定 | 执行动作 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 未变 | 未变 | 一致 | 无操作 |
| 2 | 已修改 | 未变 | Windows 端修改 | Windows $\rightarrow$ macOS |
| 3 | 未变 | 已修改 | macOS 端修改 | macOS $\rightarrow$ Windows |
| 4 | 已修改 | 已修改 | 冲突 | 双端保留，重命名为 `<name>_conflict_<timestamp>.<ext>` |
| 5 | 已删除 | 未变 | Windows 端删除 | macOS 端文件移入隔离区 |
| 6 | 未变 | 已删除 | macOS 端删除 | Windows 端文件移入隔离区 |
| 7 | 已修改 | 已删除 | 冲突 | 保留修改版本，标记冲突报告，不执行删除 |

文件删除将被记录为变更状态，被删除文件不通过覆盖方式处理。冲突文件通过重命名方式并行保留。

---

## 二、 防误删防护体系

系统包含四层防护机制：

1. **固定主控设计**：
   合并决策逻辑与 Baseline 存储集中在 Windows 端执行，避免方向选择错误。
2. **隔离区机制（Quarantine）**：
   被删除文件移入本地 `.sync_trash/<YYYYMMDD>/` 目录。
   隔离区文件保留 30 天，超时后通过后续同步任务清理。
3. **删除配额熔断（Circuit Breaker）**：
   待隔离文件数量超过总文件数 20% 且超过 5 个，或绝对数量超过 50 个时，系统触发熔断并中止任务。
4. **Dry-run 预检报告与确认**：
   传输前生成变动统计报告，获得用户确认后执行传输。

---

## 三、 分层比对策略

### 1. 文件分类比对逻辑
系统根据文件扩展名选择比对路径：

- **文本文件**（在 `text_extensions` 列表中）：
  不依赖文件大小比对。时间戳差异超过 3 秒时，全量读取文件，将 `\r\n` 替换为 `\n` 后计算 xxhash。哈希值一致判定为未修改，不一致判定为已修改。
- **二进制文件**：
  优先进行文件大小比对，大小不同直接判定为已修改。时间戳差异超过 3 秒时计算 xxhash，哈希值一致判定为未修改，不一致判定为已修改。

### 2. 独占锁处理
扫描过程中遇到权限错误或文件占用异常时，标记文件状态为 `SKIPPED_LOCKED`。
同步过程跳过该文件，保留 Baseline 中的原有记录。

---

## 四、 传输与架构

系统基于 `paramiko` (SFTP/SSH)、`xxhash` 及 `pyjson5` 实现，不依赖外部 `rsync` 进程：

1. 双端扫描器生成各自的 `FileManifest` 清单字典。
2. macOS 端清单通过 SSH 传输至 Windows 主控端。
3. Windows 端执行三路合并计算，生成 `ActionPlan`。
4. 控制台或 GUI 展示 Dry-run 报告。
5. 确认后由 Windows 端通过 SFTP 执行文件上传、下载及隔离区移动操作。

---

## 五、 网络与触发架构

- **网络配置**：两端通过局域网连接，配置 SSH 公钥认证。
- **控制逻辑**：
  - **Windows 端发起**：运行合并计算，通过 SFTP 读写远端文件。
  - **macOS 端发起**：通过 SSH 触发 Windows 端的执行脚本，计算完成后将结果返回至终端显示，确认后由 Windows 端驱动执行。

---

## 六、 排除规则（Exclude Policy）

系统根据配置忽略非必要文件与目录：

| 类别 | 排除项 | 原因 |
| :--- | :--- | :--- |
| 版本控制 | `**/.git`, `**/.git/**` | 避免破坏 Git 仓库内部对象 |
| 开发工具 | `**/.cursor`, `**/.claude`, `**/.codebuddy` | 本地环境状态与上下文缓存 |
| 依赖与产物 | `**/node_modules`, `**/__pycache__`, `**/.venv` | 依赖平台且可通过包管理器重建 |
| 敏感配置 | `**/.env` | 保护本地密钥配置 |
| 系统文件 | `**/.DS_Store`, `**/._*`, `**/Thumbs.db` | 操作系统生成的元数据垃圾 |

---

## 七、 状态存储与初始化

### 1. 基线存储格式
数据持久化于 `baseline.json.gz` 文件，内容格式如下：

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

### 2. 初始化模式（`--init`）
`baseline.json.gz` 不存在时，系统切入初始化模式：
- 暂停三路合并逻辑。
- 执行双向并集合并：单端存在的文件直接同步至对端；双端均存在的文件保留修改时间更近的版本。
- 同步完成后生成 `baseline.json.gz`。

---

## 八、 边界场景处理

1. **文件名大小写变更**：
   比对路径统一转换为小写格式。小写路径一致但原始路径不一致时，执行重命名处理。
2. **非法字符过滤**：
   包含 Windows 非法字符（`\ : * ? " < > |`）的文件标记为 `SKIPPED_ILLEGAL_CHAR` 并跳过处理。
3. **磁盘空间检查**：
   传输前校验目标磁盘剩余空间，空间不足时终止任务。

---

## 九、 配置与认证

### 1. 配置文件结构
- `config.example.json5`：配置模板。
- `config.json5`：本地配置文件。
- `connections.json`：连接历史记录。
- `state.json`：运行状态数据。

### 2. SSH 认证
系统支持读取 `~/.ssh/config` 配置，优先使用本地密钥文件进行身份验证。

---

## 十、 目录结构

```
DuetFlow/
├── assets/           # 静态资源
├── docs/             # 项目文档
├── duetflow/         # 源码包
├── scripts/          # 工具脚本
├── config.example.json5
├── config.json5
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 十一、 图标与界面支持

### 1. 图标生成脚本 (`scripts/generate_icons.py`)
- 生成 Windows 格式图标：`assets/icon.ico`。
- 生成 macOS 格式图标：`assets/icon.icns`。

### 2. 桌面快捷方式生成 (`scripts/create_shortcut.py`)
- Windows 端：生成 `DuetFlow.lnk` 快捷方式。
- macOS 端：生成 `DuetFlow.command` 脚本快捷方式。

### 3. 界面表现
- **命令行界面**：使用 `rich` 库输出结构化表格与日志。
- **图形界面**：基于 PySide6 构建。

# 🎶 DuetFlow

> **两端如一，合奏无间** —— 专为 **Windows 台式机（主力） + macOS 笔记本（移动办公）** 打造的安全、极速、手动触发式三路文件同步引擎。

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)]()

---

## ✨ 为什么选择 DuetFlow？

传统同步工具（如两路 rsync）往往面临以下痛点：
- ❌ **误删灾难**：把一端删掉的文件误当作“最新状态”覆盖到另一端，导致数据永久丢失。
- ❌ **换行符打架**：Windows (`CRLF`) 与 Mac (`LF`) 相互推送，引发无限死循环。
- ❌ **Office 时间戳污染**：仅打开 Word/Excel 就会刷新修改时间，引发无谓的大全量重传。
- ❌ **环境配置繁琐**：Windows 原生缺少 rsync，路径转换易报错。

**DuetFlow** 通过 **三路合并（Three-way Merge）** 与 **四重防误删防护**，从底层架构上完美解决了上述问题。

---

## 🚀 核心特性

- **🧠 真·三路合并（Three-way Merge）**：基于 `Baseline`（历史成功快照）比对，精准识别新增、修改、冲突以及**主动删除**。
- **🛡️ 四重防误删安全盾**：
  - **角色死锁**：Windows 固化为权威主控端，架构上消灭“选错同步方向”。
  - **30 天隔离区 (`.sync_trash`)**：所有被删文件先移动至隔离区，保留 30 天，随时 100% 恢复。
  - **熔断机制**：单次待删文件比例 > 20% 或数量 > 50 个时触发熔断，拒绝执行危险操作。
  - **Dry-run 报告确认**：同步前打印完整的变动树报告，人工回车确认后才执行。
- **🔑 极简 SSH 免密与智能配置**：
  - 原生支持解析系统 `~/.ssh/config` 配置的 Host 别名。
  - 默认使用 `~/.ssh/id_rsa` 免密私钥连接，告别繁琐密码输入。
  - `config.yaml` 本地配置彻底与版本库隔离（自动忽略），缺失时自动补全默认模板。
- **⚡ 极速哈希比对引擎**：
  - 采用 **xxhash** 算法（GB/s 级比对速度）。
  - **文本归一化哈希**：自动吸收跨平台 `CRLF` / `LF` 换行符差异，代码比对无干扰。
  - **优雅避锁**：自动识别被 Word/Excel 锁定的文件并跳过，绝不崩溃。
- **🍎 macOS 极简高级审美**：终端界面基于 `Rich` 打造圆角卡片、平滑进度条与 Apple 经典高质感配色。
- **🔌 原生跨平台传输与一键快捷方式**：
  - 纯 Python 栈（Paramiko SFTP），零外部软件依赖。
  - 内置双端图标转换器（生成 `.ico` 与 `.icns`）与一键桌面快捷方式创建脚本。

---

## 🏗️ 架构概览

```text
[ macOS (Laptop) ]                             [ Windows (Desktop) ]
 (移动办公/从节点)                               (主力工作站/权威主控)
        │                                                │
        │ 1. 扫描生成文件清单                               │ 1. 扫描生成文件清单
        └────────────── SSH / SFTP 传输 ─────────────────┘
                                 │
                   2. 主控端内存做【三路合并比对】
                  (Windows + Mac + Baseline.json)
                                 │
                   3. 生成 Dry-run 报告并等待确认
                                 │
                        [ 用户回车确认执行 ]
                                 │
                   4. 执行传输 / 移入隔离区 / 更新 Baseline
```

---

## 📁 目录结构

```text
DuetFlow/
├── assets/                                 # 静态图片与应用图标资源 (.ico & .icns)
├── duetflow/                               # 核心 Python 源码包
│   ├── __init__.py
│   ├── cli.py                              # macOS 审美 Rich 终端界面与 CLI 入口
│   ├── config.py                           # 配置解析 (包含 ~/.ssh/config)
│   ├── scanner.py                          # 文件扫描引擎
│   ├── merge.py                            # 三路合并内核
│   ├── trash.py                            # 隔离区与熔断防护
│   └── sftp.py                             # SFTP 网络传输层
├── scripts/                                # 部署与辅助工具脚本
│   ├── generate_icons.py                   # 自动从源图生成 .ico 和 .icns
│   └── create_shortcut.py                  # 一键生成 Windows/macOS 桌面快捷方式
├── pyproject.toml                           # 项目依赖 (uv) 与 Ruff Linter/Formatter 配置
├── config.example.yaml                     # 配置模板 (Git 追踪)
├── config.yaml                             # 本地配置 (Git 忽略，缺失自动生成)
├── .gitignore                              # Git 忽略文件
├── DESIGN.md                               # 完整设计方案文档
└── README.md                               # 项目 Readme
```

---

## 🛠️ 快速开始

### 1. 环境与依赖安装 (使用 uv)

本项目采用 **[uv](https://github.com/astral-sh/uv)** 管理环境与依赖，配置已默认开启清华大学 PyPI 镜像源 (`tuna`)：

```bash
# 一键同步并安装所有依赖环境
uv sync
```

### 2. 代码检查与格式化 (Ruff)

```bash
# 格式化代码与自动排序 import
uv run ruff format .

# Linter 检查
uv run ruff check .
```

### 3. 生成双端图标与桌面快捷方式

运行脚本自动将源图片导出为 `.ico`（Windows 专用）与 `.icns`（macOS 专用），并在当前系统桌面一键生成快捷方式：

```bash
# 1. 生成双端图标
uv run python scripts/generate_icons.py

# 2. 创建桌面快捷方式
uv run python scripts/create_shortcut.py
```


### 3. 初始化配置

首次运行程序时，若检测到根目录下缺失 `config.yaml`，系统将自动从 `config.example.yaml` 复制一份配置模板。

你也可以手动复制并修改配置：

```bash
cp config.example.yaml config.yaml
```

在 `config.yaml` 中指定你的 macOS 主机（支持填写 `~/.ssh/config` 中的别名如 `macbook`，或者直接填写 IP 地址）及同步路径。

### 4. 运行同步

```bash
python -m duetflow.cli
```

---

## 📄 License

[MIT License](LICENSE)


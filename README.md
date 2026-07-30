<div align="center">

# 🎶 DuetFlow

**Two-Device File Synchronization Engine for Windows & macOS**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square)](https://github.com/astral-sh/ruff)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg?style=flat-square)](README.md)

---

[English](#-english) • [中文](#-中文) • [日本語](#-日本語)

</div>

<br />

> [!CAUTION]
> **WARNING & DISCLAIMER / 免责声明 / 免責事項**
> 
> - **English**: This project is a personal hobby tool created by an amateur developer. Please use it with extreme caution and inspect the source code to verify safety before running. The author is not responsible for any file deletion, data loss, or system issues.
> - **中文**: 本项目仅为个人兴趣开发的小工具，作者编程水平有限。请务必谨慎使用并在运行前检查源码安全性。若因使用本软件导致文件删除或数据丢失，作者不承担任何责任。
> - **日本語**: 本プロジェクトは個人的な趣味で開発されたツールであり、技術には限界があります。使用の際は十分注意し、実行前にコードを確認してください。ファイル削除やデータ損失が発生した場合、作者は一切の責任を負いません。

---

## 🌐 Language Navigation / 语言导航

- [📖 English Documentation](#-english)
- [📖 中文文档](#-中文)
- [📖 日本語ドキュメント](#-日本語)

---

## 🇺🇸 English

DuetFlow is a specialized file synchronization engine designed for seamless work folder sync between **Windows (Primary Desk)** and **macOS (Laptop)**.

### 🏗️ Architecture & Requirements

Do I need to install or run DuetFlow on macOS?  
**No! macOS does NOT need to run or install DuetFlow.**

- **Single-Controller Architecture**: Windows acts as the central controller running the GUI/CLI and three-way merge engine.
- **macOS Requirements**: Simply enable **Remote Login (SSH)** on macOS (`System Settings -> Sharing -> Remote Login`).
- **Initiating Synchronization**:
  - **Mode A (Recommended - Zero Config on Windows)**: Run the DuetFlow GUI on Windows. It connects to macOS via SSH/SFTP to perform the sync.
  - **Mode B (Remote Triggering from macOS)**: Enable OpenSSH Server on Windows. You can then trigger the sync from your macOS terminal via `ssh windows_ip "uv run python -m duetflow.cli"`.

### 🛡️ Safety & Precautions

> [!WARNING]
> - **Perform Initial Backups**: Create an offline backup of your critical directories before the first sync.
> - **Review Cold-Start Merges**: On initial run without `baseline.json.gz`, the engine uses a timestamp-based union strategy. Carefully inspect the Dry-run list before confirming.
> - **Protect Credentials**: Keep `config.json5` and `connections.json` out of public version control via `.gitignore`.

### ⚡ Key Features
- **Three-Way Merge**: Differentiates between file modification and file deletion to prevent accidental data loss.
- **Quarantine System**: Deleted files are safely moved to `.sync_trash/YYYYMMDD/` (retained for 30 days) instead of permanent deletion.
- **Circuit Breaker**: Emergency shutdown triggers if deleted files exceed 20% or >50 files.
- **Line Ending Normalization**: Automatically normalizes CRLF/LF endings for text files to prevent false hash mismatches.
- **Exclusive Lock Skip**: Automatically skips locked files (e.g. Word/Excel) without throwing errors.

### 🚀 Getting Started

```bash
# 1. Install dependencies
uv sync

# 2. Launch GUI Application
uv run python -m duetflow.gui

# 3. Launch CLI Mode (Optional)
uv run python -m duetflow.cli

# 4. Run Test Suite
uv run pytest
```

On initial launch, `config.json5` will be created automatically from `config.example.json5`. Configure your local and remote root paths inside `config.json5` or directly within the GUI.

---

## 🇨🇳 中文

DuetFlow 是专门设计用于 **Windows 工作站** 与 **macOS 笔记本** 之间的双端文件同步引擎。

### 🏗️ 系统架构与环境准备

Mac 端是否需要运行或安装本软件？  
**不需要！Mac 端完全不需要运行、甚至不需要安装本软件。**

- **单主控架构设计**：Windows 端作为指挥官与计算大脑，运行 GUI/CLI 界面与三路合并引擎。
- **Mac 端环境要求**：只需在 macOS 中开启系统自带的 **远程登录 (SSH)** 即可（`系统设置 -> 共享 -> 勾选 远程登录`）。
- **发起同步的两种模式**：
  - **模式 A（推荐 · 零配置）**：直接在 Windows 端运行 DuetFlow 图形界面，输入 Mac 的 IP 与账号密码/密钥即可发起同步。Windows 无需开启任何 SSH 服务。
  - **模式 B（从 Mac 远程触发）**：若希望坐在 Mac 前直接发起同步，只需在 Windows 端开启内置的 OpenSSH Server 选配组件，即可在 Mac 终端通过 `ssh windows_ip "uv run python -m duetflow.cli"` 远程触发台式机执行同步。

### 🛡️ 建议与防范提醒

> [!WARNING]
> - **做好初始备份**：首次运行前，请先对关键工作区目录进行离线备份。
> - **审查冷启动合并**：首次运行（不存在 `baseline.json.gz`）时，引擎执行基于时间戳的并集模式，请在点击确认前仔细核对 Dry-run 操作列表。
> - **保护配置文件安全**：`config.json5` 和 `connections.json` 包含本地路径与主机连接参数，请确认已被 `.gitignore` 排除。

### ⚡ 核心功能
- **三路合并引擎**：精确区分“文件修改”与“文件删除”，彻底避免静默覆盖。
- **隔离区防护 (Quarantine)**：判删文件不执行硬删除，安全移入 `.sync_trash/YYYYMMDD/`（默认保留 30 天）。
- **熔断保护 (Circuit Breaker)**：待删除文件异常超标（>20% 或 >50 个）时立即熔断并中断任务。
- **换行符归一化**：自动处理文本文件的 CRLF/LF 差异，避免误判文件修改。
- **独占锁保护**：自动跳过 Office 等软件独占锁定的文件，不报错崩溃。

### 🚀 快速开始

```bash
# 1. 安装项目依赖
uv sync

# 2. 启动图形界面 (GUI)
uv run python -m duetflow.gui

# 3. 启动命令行界面 (CLI)
uv run python -m duetflow.cli

# 4. 运行单元测试
uv run pytest
```

首次运行会自动从 `config.example.json5` 生成 `config.json5`，亦可直接在 GUI 界面中选择和配置本地/远端同步路径。

---

## 🇯🇵 日本語

DuetFlow は **Windows (デスクトップ)** と **macOS (ノートPC)** の間で動作するファイル同期エンジンです。

### 🏗️ システム構成と事前準備

macOS 側に DuetFlow をインストールまたは実行する必要がありますか？  
**いいえ！macOS 側でアプリを実行またはインストールする必要は一切ありません。**

- **シングルコントローラー構成**: Windows 側が中央コントローラーとして GUI/CLI および 3 ウェイマージエンジンを実行します。
- **macOS 側の必要条件**: macOS の**リモートログイン (SSH)** を有効にするだけです（`システム設定 -> 共有 -> リモートログイン`）。
- **同期の実行モード**:
  - **モード A（推奨・Windows側設定不要）**: Windows 側の GUI アプリを起動し、Mac に接続して同期を実行します。
  - **モード B（Mac 側からのリモート実行）**: Windows 側で OpenSSH Server を有効にすると、Mac のターミナルから `ssh windows_ip "uv run python -m duetflow.cli"` を実行して遠隔同期できます。

### 🛡️ 推奨事項および安全対策

> [!WARNING]
> - **初回バックアップの実施**: 初回同期を実行する前に、重要なディレクトリのバックアップを作成してください。
> - **初回起動時マージの確認**: 初回実行時（`baseline.json.gz` が存在しない場合）、タイムスタンプに基づく統合マージが実行されます。事前に Dry-run プラン一覧を必ず確認してください。
> - **設定情報の保護**: `config.json5` および `connections.json` にはローカルパスや接続情報が含まれます。`.gitignore` により公開されないよう管理してください。

### ⚡ 主な機能
- **3 ウェイマージ**: 「修正」と「削除」を明確に区別し、誤消去を防止。
- **隔離フォルダ (Quarantine)**: 削除されたファイルは物理削除されず、`.sync_trash/YYYYMMDD/` に安全に移動（30 日間保存）。
- **サーキットブレーカー**: 削除ファイルが全体の 20% または 50 個を超えた場合、緊急停止。
- **改行コード正規化**: テキストファイルの CRLF/LF 差異を無視してハッシュ判定。
- **排他ロックの回避**: Office ファイルなどのロック中ファイルを自動スキップ。

### 🚀 使用方法

```bash
# 1. 依存関係のインストール
uv sync

# 2. GUI の起動
uv run python -m duetflow.gui

# 3. CLI の起動
uv run python -m duetflow.cli

# 4. テストの実行
uv run pytest
```

初回起動時に `config.example.json5` から `config.json5` が自動生成されます。GUI 上でパスを直接設定することも可能です。

---

## 📂 项目结构 / Structure

```text
DuetFlow/
├── duetflow/          # 核心源码包 / Core Python Package
│   ├── gui.py         # PySide6 GUI 界面
│   ├── cli.py         # CLI 命令行入口
│   ├── config.py      # 配置管理与网络扫描
│   ├── scanner.py     # 文件扫描与 xxhash 归一化
│   ├── merge.py       # 三路合并核心算法
│   ├── sftp.py        # SSH/SFTP 传输层
│   └── trash.py       # 隔离区与熔断防护
├── docs/              # 设计文档与流程图 / Architecture Docs
├── tests/             # Pytest 单元测试集 / Test Suite
├── scripts/           # 桌面快捷方式与图标生成脚本
├── assets/            # 图标与静态资源
├── pyproject.toml
└── README.md
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).

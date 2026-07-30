# DuetFlow

> **WARNING & DISCLAIMER / 免责声明 / 免責事項**  
> **English**: This project is a personal hobby tool created by an amateur developer. Please use it with extreme caution and thoroughly inspect the source code to verify its safety before running. The author is not responsible for any file deletion, data loss, system failure, or other issues caused by using this software.  
> **中文**: 本项目仅为个人兴趣开发的小工具，作者编程水平有限。请务必谨慎使用，并在运行前仔细检查源码安全性。若因使用本软件导致文件删除、数据丢失或系统故障等情况，作者不承担任何责任。  
> **日本語**: 本プロジェクトは個人が趣味で開発したツールであり、制作者の技術には限界があります。使用の際は十分注意し、実行前にソースコードを確認して安全性を検証してください。本ソフトウェアの使用によりファイル削除、データ損失、障害が発生した場合、作者は一切の責任を負いません。

---

## English

DuetFlow is a file synchronization tool for Windows and macOS.

It uses SSH/SFTP for file transfer and executes a three-way merge algorithm based on local, remote, and baseline snapshot states.

### Disclaimer & Warning
This project is a personal hobby tool developed by an amateur. Use it with caution and inspect the code to ensure safety. The author assumes no liability for file deletion, loss of data, or system errors.

### Security Recommendations & Precautions
- **Perform Initial Backups**: Create an offline backup of your critical synchronization directories before running the initial sync.
- **Review Cold-Start Merges**: On the first run (when `baseline.json.gz` does not exist), the system executes a union merge based on timestamps. Carefully review the Dry-run action list before confirming execution.
- **Protect Credentials**: `config.json5` and `connections.json` contain sensitive local paths and host credentials. Ensure they remain ignored by version control via `.gitignore`.

### Features
- Two-way file synchronization
- Quarantine folder for deleted files
- Normalization of CRLF/LF line endings for text files
- Automatic skip for locked or in-use files

### How It Works
1. Scans local and remote directories to generate file manifests.
2. Performs three-way merge using the baseline snapshot (`baseline.json.gz`).
3. Generates action plans (upload, download, quarantine).
4. Executes the action plan upon user confirmation.

Refer to [docs/DESIGN.md](docs/DESIGN.md) for detailed architecture and [docs/FLOWCHART.md](docs/FLOWCHART.md) for flowcharts.

### Getting Started

#### Installation & Launch

```bash
# Install dependencies
uv sync

# Launch GUI
uv run python -m duetflow.gui

# Launch CLI
uv run python -m duetflow.cli
```

On initial launch, `config.json5` is automatically generated from `config.example.json5`. Specify the synchronization roots in `config.json5`.
Connection credentials configured in the GUI are stored in `connections.json`.

#### Configuration Migration
When upgrading from older versions with `config.yaml`, the system automatically migrates data into:
- `config.json5`: Paths and exclusion rules
- `connections.json`: Connection history
- `state.json`: Runtime state data

### Dependencies
- Python >= 3.10
- paramiko
- xxhash
- pyjson5
- PySide6
- rich

---

## 中文

DuetFlow 是 Windows 与 macOS 之间的双端文件同步工具。

系统通过 SSH/SFTP 进行传输，基于 Windows 端、macOS 端及历史同步快照执行三路合并算法。系统可识别文件修改与删除状态。

### 警告与免责声明
本项目仅为个人兴趣开发的小工具，作者编程水平有限。请务必谨慎使用，并在运行前仔细检查源码安全性。若因使用本软件导致文件删除、数据丢失或系统故障等情况，作者不承担任何责任。

### 建议与防范提醒
- **做好初始备份**：首次运行前，请先对关键工作区目录进行离线备份。
- **审查冷启动合并**：首次运行（不存在 `baseline.json.gz`）时，引擎执行基于时间戳的并集模式，请在点击确认前仔细核对 Dry-run 操作列表。
- **保护配置文件安全**：`config.json5` 和 `connections.json` 包含本地路径与主机连接参数，请确认已被 `.gitignore` 排除，避免提交至公开代码库。

### 功能特性
- 双端文件同步
- 使用隔离区处理被删除文件
- 忽略文本文件的 CRLF/LF 换行符差异
- 自动跳过已被锁定占用的文件

### 工作原理
1. 扫描本地与远端目录，生成文件清单。
2. 以历史同步快照（Baseline）为基准执行三路合并。
3. 生成上传、下载、隔离等操作计划。
4. 用户确认后执行计划。

详细设计参考 [docs/DESIGN.md](docs/DESIGN.md)，流程图参考 [docs/FLOWCHART.md](docs/FLOWCHART.md)。

### 使用指南

#### 运行环境与启动

```bash
# 安装依赖
uv sync

# 启动图形界面
uv run python -m duetflow.gui

# 启动命令行界面
uv run python -m duetflow.cli
```

首次运行自动从 `config.example.json5` 生成 `config.json5`。同步路径需在 `config.json5` 中配置。
连接参数在图形界面中配置并自动保存至连接记录。

#### 配置文件迁移
存在旧版 `config.yaml` 时，系统自动迁移为以下文件：
- `config.json5`：同步路径与排除规则
- `connections.json`：连接历史记录
- `state.json`：运行时状态数据

### 项目依赖
- Python >= 3.10
- paramiko
- xxhash
- pyjson5
- PySide6
- rich

---

## 日本語

DuetFlow は Windows と macOS の間で動作するファイル同期ツールです。

SSH/SFTP を使用してファイルを転送し、ローカル、リモート、および履歴スナップショット（Baseline）に基づく 3 ウェイマージアルゴリズムを実行します。

### 警告および免責事項
本プロジェクトは個人が趣味で開発したツールであり、制作者の技術には限界があります。使用の際は十分注意し、実行前にソースコードを確認して安全性を検証してください。本ソフトウェアの使用によりファイル削除、データ損失、障害が発生した場合、作者は一切の責任を負いません。

### 推奨事項および安全対策
- **初回バックアップの実施**: 初回同期を実行する前に、重要な同期ディレクトリのオフラインバックアップを作成してください。
- **初回起動時マージの確認**: 初回実行時（`baseline.json.gz` が存在しない場合）、タイムスタンプに基づく統合マージが実行されます。実行前に Dry-run プラン一覧を必ず確認してください。
- **設定情報の保護**: `config.json5` および `connections.json` にはローカルパスや接続情報が含まれます。`.gitignore` によりリポジトリへ公開されないよう管理してください。

### 主な機能
- 双方向ファイル同期
- 隔離フォルダ（Quarantine）による削除ファイルの保護
- テキストファイルの改行コード（CRLF/LF）正規化
- 使用中・ロック中ファイルの自動スキップ

### 動作原理
1. ローカルおよびリモートディレクトリをスキャンし、ファイルマニフェストを生成します。
2. 履歴スナップショット（`baseline.json.gz`）を基準に 3 ウェイマージを実行します。
3. 同期プラン（アップロード、ダウンロード、隔離）を生成します。
4. ユーザーの確認後、同期を実行します。

詳細な設計は [docs/DESIGN.md](docs/DESIGN.md)、フローチャートは [docs/FLOWCHART.md](docs/FLOWCHART.md) を参照してください。

### 使用方法

#### 環境構築と起動

```bash
# 依存関係のインストール
uv sync

# GUI の起動
uv run python -m duetflow.gui

# CLI の起動
uv run python -m duetflow.cli
```

初回起動時に `config.example.json5` から `config.json5` が自動生成されます。同期ルートパスを `config.json5` に設定してください。
GUI で設定した接続情報は `connections.json` に保存されます。

#### 設定ファイルの移行
旧バージョンの `config.yaml` が存在する場合、自動的に以下のファイルへ移行されます：
- `config.json5`: パスおよび除外ルール
- `connections.json`: 接続履歴
- `state.json`: 実行時状態データ

### 依存関係
- Python >= 3.10
- paramiko
- xxhash
- pyjson5
- PySide6
- rich

---

## 项目结构 / Project Structure / プロジェクト構造

```
DuetFlow/
├── duetflow/          # 源码包 / Source package / ソースパッケージ
│   ├── gui.py         # 图形界面 / GUI / GUI
│   ├── cli.py         # 命令行界面 / CLI / CLI
│   ├── config.py      # 配置管理 / Configuration / 設定管理
│   ├── scanner.py     # 文件扫描 / File scanner / ファイルスキャン
│   ├── merge.py       # 三路合并引擎 / Merge engine / 3ウェイマージエンジン
│   ├── sftp.py        # SSH/SFTP 传输 / SFTP transport / SSH/SFTP転送
│   └── trash.py       # 隔离区管理 / Quarantine manager / 隔離管理
├── docs/              # 项目文档 / Documents / ドキュメント
│   ├── DESIGN.md      # 设计方案 / Design doc / 設計書
│   └── FLOWCHART*.md  # 流程图 / Flowcharts / フローチャート
├── scripts/           # 脚本工具 / Scripts / スクリプト
│   ├── create_shortcut.py
│   └── generate_icons.py
├── assets/            # 图标资源 / Assets / アセット
├── config.example.json5
├── pyproject.toml
└── README.md
```

## 许可证 / License / ライセンス

[MIT](LICENSE)

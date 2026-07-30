# DuetFlow

Windows 台式机 ↔ macOS 笔记本之间的文件同步工具。

基于 SSH/SFTP 传输，使用三路合并算法（Win 端、Mac 端、上一次同步快照），
能区分"文件被修改"和"文件被删除"两种状态，避免误删。

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 解决的问题

- 在 Win 和 Mac 之间同步工作文件，不依赖网盘
- 文件删除不会传播到另一端（用隔离区代替直接删除）
- 文本文件中的 CRLF/LF 换行符差异不影响哈希比对
- 被 Office 锁定的文件自动跳过，不会报错

## 工作原理

1. 分别扫描本地和远端目录，生成文件清单
2. 以上一次成功同步的快照（Baseline）为基准，做三路合并
3. 输出操作计划（哪些文件要上传/下载/隔离）
4. 用户确认后执行

详细设计见 [docs/DESIGN.md](docs/DESIGN.md)，流程图见 [docs/FLOWCHART.md](docs/FLOWCHART.md)。

## 快速开始

### 环境

```bash
# uv 管理依赖
uv sync

# 启动 GUI
uv run python -m duetflow.gui

# 或使用命令行（需先配好 config.json5）
uv run python -m duetflow.cli
```

首次运行会自动从 `config.example.json5` 生成 `config.json5`，编辑其中的同步路径即可。
连接参数（IP、端口、用户名、密钥）在 GUI 中输入，会自动保存为连接记录。

### 从旧版迁移

如果有旧版 `config.yaml`，首次运行新版时会自动迁移为：
- `config.json5` — 同步路径、排除规则等静态配置
- `connections.json` — 连接历史
- `state.json` — 运行时状态

## 目录结构

```
DuetFlow/
├── duetflow/          # 源码包
│   ├── gui.py         # PySide6 GUI
│   ├── cli.py         # 命令行入口
│   ├── config.py      # 配置加载
│   ├── scanner.py     # 文件扫描
│   ├── merge.py       # 三路合并引擎
│   ├── sftp.py        # SSH/SFTP 传输
│   └── trash.py       # 隔离区管理
├── docs/              # 文档
│   ├── DESIGN.md      # 设计方案
│   └── FLOWCHART*.md  # 流程图
├── scripts/           # 工具脚本
│   ├── create_shortcut.py
│   └── generate_icons.py
├── assets/            # 图标资源
├── config.example.json5  # 配置模板
├── pyproject.toml
└── README.md
```

## 依赖

- Python >= 3.10
- paramiko (SSH/SFTP)
- xxhash (文件哈希)
- pyjson5 (配置读取)
- PySide6 (GUI)
- rich (CLI 界面)

## License

[MIT](LICENSE)

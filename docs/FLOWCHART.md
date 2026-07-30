# DuetFlow 流程图文档索引

本文档包含启动、配置加载、扫描、三路合并、安全检查、确认执行及 Baseline 更新的流程图索引。

## 术语定义

| 缩写 | 含义 |
|------|------|
| Win / W | Windows 端（本地/主控） |
| Mac / M | macOS 端（远端/从节点） |
| Baseline / B | 上一次同步完成时保存的文件状态快照 (`baseline.json.gz`) |
| Manifest | 文件扫描清单（包含 size, mtime, hash） |
| Action Plan | 合并引擎计算得出的操作列表 |
| SFTP | 基于 SSH 的文件传输协议 |
| Dry-run | 预演模式（仅显示计划，不进行真实写操作） |
| QUARANTINE | 隔离操作（文件移入 `.sync_trash/` 目录） |

## 阶段索引

| 序号 | 文件 | 涵盖内容 |
|---|--------|----------|
| 01 | [FLOWCHART_01_STARTUP.md](FLOWCHART_01_STARTUP.md) | 系统启动、配置文件读取及 SSH 连接解析 |
| 02 | [FLOWCHART_02_SCAN.md](FLOWCHART_02_SCAN.md) | 本地扫描、远程扫描、Baseline 读取及冷启动状态判断 |
| 03 | [FLOWCHART_03_MERGE.md](FLOWCHART_03_MERGE.md) | 三路合并引擎计算流程 |
| 04 | [FLOWCHART_04_EXECUTION.md](FLOWCHART_04_EXECUTION.md) | 熔断校验、Dry-run 展示、用户确认及同步任务执行 |
| 05 | [FLOWCHART_05_REFERENCE.md](FLOWCHART_05_REFERENCE.md) | 数据结构与安全防护说明 |

## 流程顺序

```
[启动/配置加载] ──→ [GUI 展示] ──→ [扫描双端] ──→ [三路合并] ──→ [安全检查]
                                                         │
                                                         ↓
                                              [Dry-run 展示] ──→ [用户确认] ──→ [执行同步] ──→ [收尾]
```


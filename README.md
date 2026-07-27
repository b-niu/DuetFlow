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
- **⚡ 极速哈希比对引擎**：
  - 采用 **xxhash** 算法（GB/s 级比对速度）。
  - **文本归一化哈希**：自动吸收跨平台 `CRLF` / `LF` 换行符差异，代码比对无干扰。
  - **优雅避锁**：自动识别被 Word/Excel 锁定的文件并跳过，绝不崩溃。
- **🔌 原生跨平台传输**：纯 Python 栈（Paramiko SFTP），零外部软件依赖，开箱即用。

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

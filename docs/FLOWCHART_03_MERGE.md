# 03 — 三路合并引擎

三路合并计算函数 `three_way_merge()` 输入 Windows 端清单、macOS 端清单及 Baseline 状态，输出逐文件操作类型。

```mermaid
flowchart TD
    collect["汇总全量路径列表 all_paths\n遍历判决"]
    collect --> check_skip{文件是否\n锁定或包含非法字符?}
    check_skip -- 是 --> skip["SKIP: locked_or_illegal"]
    check_skip -- 否 --> has_baseline{Baseline 中\n存在该记录?}
    has_baseline -- 否（冷启动） --> cold_merge
    has_baseline -- 是（三路合并） --> normal_merge

    subgraph cold_merge["冷启动计算逻辑"]
        direction TB
        check_side{是否存在于\nWindows / macOS?}
        check_side -- "仅 Windows" --> w2m["WIN_TO_MAC"]
        check_side -- "仅 macOS" --> m2w["MAC_TO_WIN"]
        check_side -- "双端均存在" --> compare_hash{hash 一致?}
        compare_hash -- 是 --> skip_same["SKIP: same"]
        compare_hash -- 否 --> compare_mtime{Windows mtime\n>= macOS mtime?}
        compare_mtime -- 是 --> w2m2["WIN_TO_MAC"]
        compare_mtime -- 否 --> m2w2["MAC_TO_WIN"]
    end

    subgraph normal_merge["三路合并计算逻辑"]
        direction TB
        compute["计算状态变更:\n  win_changed = win.hash != base.hash\n  mac_changed = mac.hash != base.hash\n  win_deleted = win不存在 & base存在\n  mac_deleted = mac不存在 & base存在"]
        compute --> unchanged{均未变动?}
        unchanged -- 是 --> s1["① SKIP: unchanged"]
        unchanged -- 否 --> only_win{仅 Windows 修改?}
        only_win -- 是 --> s2["② WIN_TO_MAC"]
        only_win -- 否 --> only_mac{仅 macOS 修改?}
        only_mac -- 是 --> s3["③ MAC_TO_WIN"]
        only_mac -- 否 --> both_mod{双端均修改?}
        both_mod -- 是 --> s4["④ CONFLICT\nconflict_name = file_conflict_ts.ext"]
        both_mod -- 否 --> win_del_mac_ok{"Windows 删除 &\nmacOS 未变?"}
        win_del_mac_ok -- 是 --> s5["⑤ QUARANTINE_MAC\nmacOS 端移入隔离区"]
        win_del_mac_ok -- 否 --> mac_del_win_ok{"macOS 删除 &\nWindows 未变?"}
        mac_del_win_ok -- 是 --> s6["⑥ QUARANTINE_WIN\nWindows 端移入隔离区"]
        mac_del_win_ok -- 否 --> s7["⑦ CONFLICT: modified_vs_deleted\n保留修改版本"]
    end
```

## 判定结果一览

| 编号 | 判定状态 | 条件说明 | 执行动作 |
|---|------|------|---------|
| ① | `SKIP: unchanged` | 双端文件与 Baseline 一致 | 不处理 |
| ② | `WIN_TO_MAC` | 仅 Windows 端修改 | 上传 Windows 文件至 macOS |
| ③ | `MAC_TO_WIN` | 仅 macOS 端修改 | 从 macOS 下载文件至 Windows |
| ④ | `CONFLICT` | 双端均修改该文件 | 双端各备份冲突文件，跳过覆盖 |
| ⑤ | `QUARANTINE_MAC` | Windows 端删除，macOS 端未变 | macOS 端文件移入隔离区 |
| ⑥ | `QUARANTINE_WIN` | macOS 端删除，Windows 端未变 | Windows 端文件移入隔离区 |
| ⑦ | `CONFLICT: modified_vs_deleted` | 单端删除，另端修改 | 保留修改版文件，不执行删除 |

## 模式比对

| 维度 | 冷启动模式（无 Baseline） | 正常模式（有 Baseline） |
|---|-------------------|---------------------|
| 触发条件 | Baseline 文件不存在 | Baseline 文件正常加载 |
| 判定策略 | 取双端并集，以修改时间确定传输方向 | 基于 Baseline 进行三路比对 |
| 依据 | 文件修改时间 (mtime) | 文件哈希 (hash) |

[返回索引](FLOWCHART.md)


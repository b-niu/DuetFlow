# 04 — 安全检查、Dry-run、执行与收尾

## 4.1 熔断检查

计算完成操作计划后，系统进行熔断校验。

```mermaid
flowchart LR
    count_quarantine["统计待隔离项数量\nQUARANTINE_WIN + QUARANTINE_MAC"]
    count_quarantine --> circuit_breaker{"待隔离数 > 总文件数×20%\n且 待隔离数 > 5\n或 待隔离数 > 50?"}
    circuit_breaker -- 触发熔断 --> abort(["终止任务\n不执行操作"])
    circuit_breaker -- 未触发 --> proceed["通过发送 plan_ready 信号传递结果"]
```

**熔断触发条件**：
- 待隔离文件数超过总文件数 20% 且超过 5 个。
- 待隔离文件数超过 50 个。

---

## 4.2 Dry-run 展示与确认

校验通过后，图形界面展示计划列表。

```mermaid
flowchart TD
    fill_table["填充表格控件\n显示动作、路径与备注"]
    fill_table --> show_summary["计算并显示各动作文件数量汇总"]
    show_summary --> has_changes{包含有效变动?}
    has_changes -- 无变动 --> already_synced(["显示双端已同步"])
    has_changes -- 有变动 --> wait_confirm([等待用户触发确认执行])
```

---

## 4.3 执行阶段

确认后，`SyncWorker.execute_plan()` 顺序执行各类计划项。

```mermaid
flowchart TD
    iterate["遍历操作计划，跳过 SKIP 项"]
    iterate --> dispatch{操作类型}
    dispatch -- WIN_TO_MAC --> upload["sftp.upload()\n上传文件至远端"]
    dispatch -- MAC_TO_WIN --> download["sftp.download()\n从远端下载文件"]
    dispatch -- QUARANTINE_WIN --> quarantine_local["trash.quarantine_local()\n文件移入本地 .sync_trash/ 目录"]
    dispatch -- QUARANTINE_MAC --> quarantine_remote["sftp.remote_quarantine()\n文件移入远端 .sync_trash/ 目录"]
    dispatch -- CONFLICT --> check_reason{"判定冲突原因"}
    check_reason -- 改删冲突 --> log_skip["记录日志，跳过处理"]
    check_reason -- 双端修改 --> backup_both["保存本地冲突副本\n下载远端冲突副本"]
```

---

## 4.4 收尾流程

```mermaid
flowchart TD
    save["save_baseline()\n合并最新清单并原子写入 baseline.json.gz"]
    save --> cleanup["trash.purge_expired()\n删除 .sync_trash/ 中超过 30 天的目录"]
    cleanup --> done(["更新状态栏为同步完成"])
```

1. **保存 Baseline**：合并双端最新清单，写入临时文件后执行替换。
2. **清理过期文件**：清除历史隔离区中保存时间超过指定天数的目录。

[返回索引](FLOWCHART.md)


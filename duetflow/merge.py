"""三路合并引擎。对比 win_manifest、mac_manifest、baseline，产出 action_plan。

action_plan 是一个 list，每个元素是 dict:
    {"action": str, "path": str, ...}

action 取值:
    WIN_TO_MAC    - 将 Windows 文件推送到 Mac
    MAC_TO_WIN    - 将 Mac 文件拉取到 Windows
    QUARANTINE_WIN - 将 Windows 本地文件移入隔离区
    QUARANTINE_MAC - 将 Mac 远端文件移入隔离区（通过 SFTP）
    CONFLICT      - 双端均修改或改删冲突，两边保留并重命名
    SKIP          - 无需操作
"""

from datetime import datetime


def _changed(entry, baseline_entry):
    """判断文件相对基线是否发生变化（hash 不同即变）"""
    if baseline_entry is None:
        return True  # 新文件
    return entry.get("hash") != baseline_entry.get("hash")


def _is_skipped(entry):
    return entry.get("status") in ("SKIPPED_LOCKED", "SKIPPED_ILLEGAL_CHAR")


def three_way_merge(win_manifest, mac_manifest, baseline):
    """
    三路合并。baseline 为上次同步快照的 files dict（可以为 {}，即冷启动 init 模式）。
    返回 action_plan list。
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_paths = set(win_manifest) | set(mac_manifest) | set(baseline)
    plan = []

    for path in sorted(all_paths):
        win = win_manifest.get(path)
        mac = mac_manifest.get(path)
        base = baseline.get(path)

        # 跳过锁文件/非法字符文件
        if (win and _is_skipped(win)) or (mac and _is_skipped(mac)):
            plan.append({"action": "SKIP", "path": path, "reason": "locked_or_illegal"})
            continue

        win_exists = win is not None
        mac_exists = mac is not None
        base_exists = base is not None

        # 冷启动模式：baseline 为空时，做双向并集
        if not base_exists:
            if win_exists and not mac_exists:
                plan.append({"action": "WIN_TO_MAC", "path": path})
            elif mac_exists and not win_exists:
                plan.append({"action": "MAC_TO_WIN", "path": path})
            elif win_exists and mac_exists:
                # 两端都有，取 mtime 较新的
                if win["mtime"] >= mac["mtime"]:
                    if win.get("hash") != mac.get("hash"):
                        plan.append({"action": "WIN_TO_MAC", "path": path})
                    else:
                        plan.append({"action": "SKIP", "path": path, "reason": "same"})
                else:
                    plan.append({"action": "MAC_TO_WIN", "path": path})
            continue

        # 正常三路合并
        win_changed = win_exists and _changed(win, base)
        mac_changed = mac_exists and _changed(mac, base)
        win_deleted = not win_exists and base_exists
        mac_deleted = not mac_exists and base_exists

        # Case 1: 均未变
        if not win_changed and not mac_changed and not win_deleted and not mac_deleted:
            plan.append({"action": "SKIP", "path": path, "reason": "unchanged"})

        # Case 2: Win 修改，Mac 未变
        elif win_changed and not mac_changed and not mac_deleted:
            plan.append({"action": "WIN_TO_MAC", "path": path})

        # Case 3: Mac 修改，Win 未变
        elif mac_changed and not win_changed and not win_deleted:
            plan.append({"action": "MAC_TO_WIN", "path": path})

        # Case 4: 两端均修改 -> 冲突
        elif win_changed and mac_changed:
            stem = path.rsplit(".", 1)
            if len(stem) == 2:
                conflict_path = f"{stem[0]}_conflict_{ts}.{stem[1]}"
            else:
                conflict_path = f"{path}_conflict_{ts}"
            plan.append(
                {"action": "CONFLICT", "path": path, "conflict_name": conflict_path}
            )

        # Case 5: Win 删除，Mac 未变
        elif win_deleted and not mac_changed:
            plan.append({"action": "QUARANTINE_MAC", "path": path})

        # Case 6: Mac 删除，Win 未变
        elif mac_deleted and not win_changed:
            plan.append({"action": "QUARANTINE_WIN", "path": path})

        # Case 7: Win 修改 + Mac 删除 (或反向) -> 保留修改版，报告冲突
        elif win_changed and mac_deleted:
            plan.append(
                {
                    "action": "CONFLICT",
                    "path": path,
                    "reason": "modified_vs_deleted",
                    "conflict_name": path,
                }
            )
        elif mac_changed and win_deleted:
            plan.append(
                {
                    "action": "CONFLICT",
                    "path": path,
                    "reason": "modified_vs_deleted",
                    "conflict_name": path,
                }
            )

    return plan

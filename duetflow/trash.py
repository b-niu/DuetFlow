"""隔离区管理：本地隔离、熔断检查、过期清理。"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def quarantine_local(file_path, win_root):
    """将 Windows 端文件移入本地隔离区 .sync_trash/<YYYYMMDD>/"""
    root = Path(win_root)
    trash_root = root.parent / ".sync_trash"
    date_dir = trash_root / datetime.now().strftime("%Y%m%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    src = root / file_path
    dest = date_dir / Path(file_path).name
    # 目标路径冲突时追加时间戳
    if dest.exists():
        dest = date_dir / f"{Path(file_path).stem}_{datetime.now().strftime('%H%M%S')}{Path(file_path).suffix}"
    if src.exists():
        shutil.move(str(src), str(dest))


def circuit_breaker_check(action_plan, total_files, max_ratio=0.20, max_count=50):
    """检查熔断条件，触发则返回 True（调用方应中止执行）"""
    quarantine_count = sum(
        1 for a in action_plan if a["action"] in ("QUARANTINE_WIN", "QUARANTINE_MAC")
    )
    if total_files == 0:
        return False, 0, 0.0
    ratio = quarantine_count / total_files
    if (ratio > max_ratio and quarantine_count > 5) or quarantine_count > max_count:
        return True, quarantine_count, ratio
    return False, quarantine_count, ratio


def purge_expired(win_root, quarantine_days=30):
    """清理隔离区中超过 quarantine_days 天的文件（物理删除）"""
    trash_root = Path(win_root).parent / ".sync_trash"
    if not trash_root.exists():
        return
    cutoff = datetime.now() - timedelta(days=quarantine_days)
    for date_dir in trash_root.iterdir():
        if not date_dir.is_dir():
            continue
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
        except ValueError:
            continue
        if dir_date < cutoff:
            shutil.rmtree(str(date_dir), ignore_errors=True)

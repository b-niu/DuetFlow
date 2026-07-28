"""DuetFlow 主控 CLI 入口。在 Windows 端运行，统揽三路合并与 SFTP 传输。

用法:
    uv run python -m duetflow.cli          # 正常同步（需已有 baseline）
    uv run python -m duetflow.cli --init   # 首次冷启动初始化
"""

import gzip
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from duetflow import config, merge, scanner, sftp, trash

console = Console()

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "baseline.json.gz"


# ─── Baseline 读写 ──────────────────────────────────────────────────────────


def load_baseline():
    if not BASELINE_PATH.exists():
        return {}
    with gzip.open(BASELINE_PATH, "rt", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("files", {})


def save_baseline(win_manifest, mac_manifest):
    """合并双端清单为新基线（以同步成功后的状态为准）"""
    merged = {}
    for path, entry in win_manifest.items():
        if not entry.get("status"):
            merged[path] = entry
    for path, entry in mac_manifest.items():
        if not entry.get("status") and path not in merged:
            merged[path] = entry

    data = {
        "version": "2.0",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "files": merged,
    }
    tmp = BASELINE_PATH.with_suffix(".json.gz.tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp.replace(BASELINE_PATH)


# ─── Rich 打印工具 ──────────────────────────────────────────────────────────

ACTION_STYLE = {
    "WIN_TO_MAC": ("[bold cyan]▲ WIN→MAC[/]", "cyan"),
    "MAC_TO_WIN": ("[bold green]▼ MAC→WIN[/]", "green"),
    "QUARANTINE_WIN": ("[bold yellow]🗑 隔离(Win)[/]", "yellow"),
    "QUARANTINE_MAC": ("[bold yellow]🗑 隔离(Mac)[/]", "yellow"),
    "CONFLICT": ("[bold red]⚡ 冲突[/]", "red"),
    "SKIP": ("[dim]— 跳过[/]", "dim"),
}


def print_dry_run(plan, win_manifest, mac_manifest):
    counts = {}
    for item in plan:
        counts[item["action"]] = counts.get(item["action"], 0) + 1

    table = Table(title="[bold]DuetFlow · Dry-Run 预检报告[/]", border_style="blue", show_lines=False)
    table.add_column("动作", style="bold", min_width=14)
    table.add_column("文件路径", overflow="fold")
    table.add_column("备注", style="dim")

    for item in plan:
        if item["action"] == "SKIP":
            continue
        label, _ = ACTION_STYLE.get(item["action"], (item["action"], "white"))
        remark = item.get("reason", "") or item.get("conflict_name", "")
        table.add_row(label, item["path"], remark)

    console.print()
    console.print(table)

    summary_parts = []
    for action, label_color in [
        ("WIN_TO_MAC", "[cyan]▲ Win→Mac[/]"),
        ("MAC_TO_WIN", "[green]▼ Mac→Win[/]"),
        ("QUARANTINE_WIN", "[yellow]🗑 隔离Win[/]"),
        ("QUARANTINE_MAC", "[yellow]🗑 隔离Mac[/]"),
        ("CONFLICT", "[red]⚡ 冲突[/]"),
        ("SKIP", "[dim]— 跳过[/]"),
    ]:
        n = counts.get(action, 0)
        if n:
            summary_parts.append(f"{label_color} {n} 个")

    console.print(Panel(
        "  ".join(summary_parts) or "无变动",
        title="[bold blue]同步摘要[/]",
        border_style="blue",
    ))


# ─── 执行阶段 ───────────────────────────────────────────────────────────────


def execute(plan, cfg, ssh, sftp_client, win_root, mac_root):
    quarantine_days = cfg.get("safety", {}).get("quarantine_days", 30)

    for item in plan:
        action = item["action"]
        path = item["path"]
        local_full = Path(win_root) / path
        remote_full = str(PurePosixPath(mac_root) / path)

        if action == "WIN_TO_MAC":
            console.print(f"  [cyan]▲[/] {path}")
            sftp.upload(sftp_client, local_full, remote_full)

        elif action == "MAC_TO_WIN":
            console.print(f"  [green]▼[/] {path}")
            sftp.download(sftp_client, remote_full, local_full)

        elif action == "QUARANTINE_WIN":
            console.print(f"  [yellow]🗑 Win[/] {path}")
            trash.quarantine_local(path, win_root, quarantine_days)

        elif action == "QUARANTINE_MAC":
            console.print(f"  [yellow]🗑 Mac[/] {path}")
            mac_trash = str(PurePosixPath(mac_root).parent / ".sync_trash")
            sftp.remote_quarantine(ssh, remote_full, mac_trash)

        elif action == "CONFLICT":
            reason = item.get("reason", "")
            if reason == "modified_vs_deleted":
                # 修改 vs 删除：两端文件已经一端不存在，只报告不动
                console.print(f"  [red]⚡[/] 冲突(改/删) {path} — 跳过，请手动处理")
            else:
                # 双端均修改：Win 改名追加 _conflict_ts，Mac 端也做同样命名
                conflict_name = item["conflict_name"]
                local_conflict = local_full.parent / Path(conflict_name).name
                remote_conflict = str(PurePosixPath(remote_full).parent / Path(conflict_name).name)
                console.print(f"  [red]⚡[/] 冲突 {path} → 双端保留 {conflict_name}")
                # Win 端重命名
                if local_full.exists():
                    shutil.copy2(str(local_full), str(local_conflict))
                # 将 Mac 端冲突版本拉到 Win 端
                sftp.download(sftp_client, remote_full, local_conflict.parent / f"_mac_{Path(conflict_name).name}")

        # SKIP: do nothing


# ─── 主流程 ─────────────────────────────────────────────────────────────────


def main():
    init_mode = "--init" in sys.argv

    console.print(Panel(
        "[bold]🎶 DuetFlow[/]  双端文件同步引擎\n[dim]Windows (主控) ↔ macOS (从节点)[/]",
        border_style="blue",
        padding=(0, 2),
    ))

    cfg = config.load()
    resolved = cfg["_resolved"]
    win_root = cfg["sync_paths"]["windows_root"]
    mac_root = cfg["sync_paths"]["mac_root"]
    exclude = cfg.get("exclude", [])
    text_ext = cfg.get("text_extensions", [])
    safety = cfg.get("safety", {})
    cb = safety.get("circuit_breaker", {})
    cb_ratio = cb.get("max_ratio", 0.20)
    cb_count = cb.get("max_count", 50)

    # 1. 扫描本地
    console.print("\n[bold blue]● 扫描本地文件...[/]")
    win_manifest = scanner.scan(win_root, exclude, text_ext)
    console.print(f"  Win 端: {len(win_manifest)} 个文件")

    # 2. 连接 Mac 并扫描远端
    console.print(f"\n[bold blue]● 连接 {resolved['host']}...[/]")
    try:
        ssh, sftp_client = sftp.connect(resolved)
    except Exception as e:
        console.print(f"[red]连接失败: {e}[/]")
        sys.exit(1)
    console.print("  连接成功")

    console.print("\n[bold blue]● 扫描 Mac 端文件...[/]")
    mac_manifest = sftp.remote_scan(ssh, mac_root, exclude, text_ext)
    console.print(f"  Mac 端: {len(mac_manifest)} 个文件")

    # 3. 加载 baseline
    baseline = load_baseline()
    if not baseline and not init_mode:
        console.print(Panel(
            "[yellow]未找到 baseline.json.gz，检测到首次运行。\n自动切换到初始化模式 (--init)。[/]",
            border_style="yellow",
        ))
        init_mode = True

    if init_mode:
        baseline = {}  # 冷启动：以空 baseline 触发并集合并

    # 4. 三路合并
    console.print("\n[bold blue]● 三路合并计算...[/]")
    plan = merge.three_way_merge(win_manifest, mac_manifest, baseline)

    # 5. 熔断检查
    triggered, q_count, ratio = trash.circuit_breaker_check(plan, len(win_manifest) + len(mac_manifest), cb_ratio, cb_count)
    if triggered:
        console.print(Panel(
            f"[bold red]⚠ 熔断触发！待隔离 {q_count} 个文件（{ratio:.1%}），超出安全阈值。\n本次同步已中止，请检查后手动确认。[/]",
            border_style="red",
        ))
        ssh.close()
        sys.exit(1)

    # 6. Dry-run 打印
    print_dry_run(plan, win_manifest, mac_manifest)

    active = [a for a in plan if a["action"] != "SKIP"]
    if not active:
        console.print("\n[green]✓ 双端已是最新状态，无需同步。[/]")
        ssh.close()
        return

    # 7. 用户确认
    console.print("\n[bold]回车确认执行，输入 q 取消：[/] ", end="")
    try:
        ans = input()
    except (KeyboardInterrupt, EOFError):
        ans = "q"

    if ans.strip().lower() == "q":
        console.print("[yellow]已取消。[/]")
        ssh.close()
        return

    # 8. 执行
    console.print("\n[bold blue]● 执行中...[/]")
    execute(plan, cfg, ssh, sftp_client, win_root, mac_root)

    # 9. 保存 baseline
    save_baseline(win_manifest, mac_manifest)
    console.print(f"\n[green bold]✓ 同步完成！Baseline 已更新。[/]")

    # 10. 清理过期隔离文件
    trash.purge_expired(win_root, safety.get("quarantine_days", 30))

    ssh.close()


if __name__ == "__main__":
    main()

"""DuetFlow GUI 主界面 —— 现代 macOS 浅色风格 PySide6 实现。

运行方式:
    uv run python -m duetflow.gui
"""

import socket
import sys
import time
import traceback
from pathlib import Path, PurePosixPath

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from duetflow import config, merge, scanner, sftp, trash

ROOT = Path(__file__).resolve().parent.parent

# ─── 现代优雅调色板 ───────────────────────────────────────────────────────────

LIGHT_BG = "#f8fafc"          # 全局清爽背景 (Slate 50)
CARD_BG = "#ffffff"           # 卡片背景 (纯白)
BORDER_COLOR = "#e2e8f0"      # 微边框 (Slate 200)
TEXT_PRIMARY = "#0f172a"      # 主文字 (Slate 900)
TEXT_SECONDARY = "#64748b"    # 次要文字 (Slate 500)
ACCENT_BLUE = "#2563eb"       # 品牌海蓝 (Blue 600)
SUCCESS_GREEN = "#16a34a"     # 成功绿 (Green 600)
WARNING_YELLOW = "#d97706"    # 警告橙 (Amber 600)
DANGER_RED = "#dc2626"        # 危险红 (Red 600)
TABLE_ALT_BG = "#f8fafc"      # 表格交替行

CONSOLE_BG = "#0f172a"        # 暗黑控制台背景 (Slate 900)
CONSOLE_TEXT = "#38bdf8"      # 暗黑控制台青蓝文本 (Sky 400)

MAX_CONNECTIONS = 5

QSS = f"""
QWidget {{
    background-color: {LIGHT_BG};
    color: {TEXT_PRIMARY};
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}}

QFrame#card {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
}}

QProgressBar {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    background-color: #f1f5f9;
    text-align: center;
    font-size: 12px;
    color: {TEXT_PRIMARY};
}}
QProgressBar::chunk {{
    background-color: {ACCENT_BLUE};
    border-radius: 3px;
}}

QComboBox, QLineEdit {{
    background-color: #f8fafc;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}
QComboBox:hover, QLineEdit:hover {{
    border-color: #cbd5e1;
    background-color: {CARD_BG};
}}
QComboBox:focus, QLineEdit:focus {{
    border-color: {ACCENT_BLUE};
    background-color: {CARD_BG};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QPushButton {{
    background-color: {ACCENT_BLUE};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #1d4ed8;
}}
QPushButton:pressed {{
    background-color: #1e40af;
}}
QPushButton:disabled {{
    background-color: #e2e8f0;
    border-color: #cbd5e1;
    color: #94a3b8;
}}

QPushButton#danger {{
    background-color: {DANGER_RED};
}}
QPushButton#danger:hover {{
    background-color: #b91c1c;
}}

QPushButton#success {{
    background-color: {SUCCESS_GREEN};
}}
QPushButton#success:hover {{
    background-color: #15803d;
}}

QPushButton#flat {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    font-weight: 500;
    font-size: 13px;
    padding: 6px 12px;
    border-radius: 6px;
}}
QPushButton#flat:hover {{
    background-color: #f1f5f9;
    border-color: #cbd5e1;
}}

QPushButton#add_tab {{
    background-color: {CARD_BG};
    color: {ACCENT_BLUE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    font-size: 15px;
    font-weight: bold;
    padding: 2px 10px;
    min-height: 24px;
}}
QPushButton#add_tab:hover {{
    background-color: #eff6ff;
    border-color: {ACCENT_BLUE};
}}

QPushButton#browse_key {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    font-weight: normal;
    font-size: 13px;
    padding: 5px 12px;
}}
QPushButton#browse_key:hover {{
    background-color: #f1f5f9;
}}

QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background-color: {CARD_BG};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 10px 6px 14px;
    margin-right: 6px;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: #eff6ff;
    border: 1px solid {ACCENT_BLUE};
    color: {ACCENT_BLUE};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background-color: #f1f5f9;
    color: {TEXT_PRIMARY};
}}

QTableWidget {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #dbeafe;
    selection-color: {TEXT_PRIMARY};
    alternate-background-color: {TABLE_ALT_BG};
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border: none;
}}
QHeaderView::section {{
    background-color: #f1f5f9;
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {BORDER_COLOR};
}}

QTextEdit {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 10px;
    font-family: Consolas, "Fira Code", monospace;
    font-size: 12px;
    color: #334155;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QSplitter::handle {{
    background: {BORDER_COLOR};
    width: 1px;
}}

QLabel#title {{
    font-size: 18px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QLabel#subtitle {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}
QLabel#section {{
    font-size: 13px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}
"""

ACTION_META = {
    "WIN_TO_MAC":    ("▲ Win → Mac",  ACCENT_BLUE),
    "MAC_TO_WIN":    ("▼ Mac → Win",  SUCCESS_GREEN),
    "QUARANTINE_WIN": ("🗑 隔离 Win",   WARNING_YELLOW),
    "QUARANTINE_MAC": ("🗑 隔离 Mac",   WARNING_YELLOW),
    "CONFLICT":      ("⚡ 冲突",        DANGER_RED),
    "SKIP":          ("— 跳过",        TEXT_SECONDARY),
}


def get_local_ip():
    """获取本机的 LAN IP 地址。"""
    try:
        from duetflow.config import scan_local_ips
        scanned = scan_local_ips()
        if scanned:
            return scanned[0]["ip"]
        return "127.0.0.1"
    except Exception:
        return "127.0.0.1"


# ─── 后台工作线程 ─────────────────────────────────────────────────────────────

class ConnectionTester(QObject):
    """测试 SSH 通断检测线程。"""

    result = Signal(bool, str, float)  # ok, msg, rtt_ms

    def __init__(self, resolved_cfg):
        super().__init__()
        self.r = resolved_cfg

    def test_connection(self):
        start = time.time()
        try:
            ssh, sftp_client = sftp.connect(self.r)
            rtt = (time.time() - start) * 1000
            ssh.close()
            self.result.emit(True, "连接正常", rtt)
        except Exception as e:
            err_msg = str(e)
            if "Error reading SSH protocol banner" in err_msg or "EOFError" in err_msg:
                err_msg = "SSH 协议握手超时/失败 (请检查目标机器 SSH 服务或 IP 端口)"
            elif "Connection refused" in err_msg or "10061" in err_msg:
                err_msg = "连接被拒绝 (目标主机未开启 SSH 服务)"
            elif "timed out" in err_msg or "10060" in err_msg:
                err_msg = "连接超时 (目标 IP 不可达或网络防火墙阻挡)"
            self.result.emit(False, err_msg, 0.0)


class SyncWorker(QObject):
    """在 QThread 中执行扫描 / 合并 / 传输，通过信号回调主线程。"""

    log = Signal(str)                   # 普通日志行
    progress = Signal(int, int, str)    # 进度 (current, total, status_msg)
    plan_ready = Signal(list)           # dry-run plan 完成
    done = Signal(bool, str)            # 完成 (success, message)

    def __init__(self, cfg, do_execute=False, approved_plan=None,
                 win_manifest=None, mac_manifest=None, ssh=None, sftp_client=None):
        super().__init__()
        self.cfg = cfg
        self.do_execute = do_execute
        self.approved_plan = approved_plan
        self._ssh = ssh
        self._sftp = sftp_client
        self._win_manifest = win_manifest
        self._mac_manifest = mac_manifest
        self._cancelled = False

    def stop(self):
        """发送终止请求"""
        self._cancelled = True

    def _is_cancelled(self):
        return self._cancelled

    def scan_and_plan(self):
        try:
            cfg = self.cfg
            r = cfg["_resolved"]
            local_root = r["local_root"]
            remote_root = r["remote_root"]
            exclude = cfg.get("exclude", [])
            text_ext = cfg.get("text_extensions", [])

            # 提前加载 baseline，用作本地扫描的 mtime/size 缓存（典型提速 80%+）
            from duetflow.cli import load_baseline
            self.progress.emit(0, 0, "正在加载历史快照...")
            baseline_for_cache = load_baseline()
            if baseline_for_cache:
                self.log.emit(f"已加载 baseline 快照（{len(baseline_for_cache)} 条记录），将用于 mtime 缓存加速")
            else:
                self.log.emit("未找到历史 baseline 快照，进入冷启动并集模式")

            self.log.emit(f"开始扫描本地: {local_root}")
            self.progress.emit(0, 0, "正在扫描本地目录...")

            def scan_progress(count, path):
                if count % 200 == 0 or count == 1:
                    self.progress.emit(0, 0, f"正在扫描本地... 已发现 {count} 个文件")

            local_mf = scanner.scan(
                local_root, exclude, text_ext,
                progress_callback=scan_progress,
                cancel_check=self._is_cancelled,
                prev_manifest=baseline_for_cache,   # ← mtime 缓存加速
            )

            if self._is_cancelled():
                self.done.emit(False, "任务已被用户取消。")
                return

            # 统计缓存命中率（有 hash 且 size/mtime 与 baseline 一致的文件）
            cached = sum(
                1 for rel, e in local_mf.items()
                if not e.get("status") and baseline_for_cache.get(rel, {}).get("mtime") == e.get("mtime")
            )
            self.log.emit(
                f"✓ 本地扫描完毕，共 {len(local_mf)} 个文件"
                + (f"（{cached} 个命中 mtime 缓存，跳过 I/O）" if cached else "")
            )

            self.log.emit(f"正在连接 SSH 主机 {r['host']}:{r['port']} ...")
            self.progress.emit(0, 0, "连接 SSH 主机...")
            try:
                self._ssh, self._sftp = sftp.connect(r)
            except Exception as conn_err:
                err_msg = str(conn_err)
                if "timed out" in err_msg or "10060" in err_msg:
                    hint = f"❌ 连接超时: 无法连接到 {r['host']}:{r['port']}\n请检查:\n 1. Mac 端 IP 是否已变动\n 2. Mac 端是否已开启'远程登录'(SSH)\n 3. 两端是否处于同一局域网"
                elif "Connection refused" in err_msg or "10061" in err_msg:
                    hint = f"❌ 连接被拒绝: {r['host']}:{r['port']}\n目标主机未开启 SSH 服务。"
                else:
                    hint = f"❌ 连接失败: {err_msg}"
                self.log.emit(hint)
                self.done.emit(False, hint)
                return

            self.log.emit("✓ SSH 连接成功")

            if self._is_cancelled():
                self.done.emit(False, "任务已被用户取消。")
                return

            self.log.emit(f"开始扫描远端: {remote_root}")
            self.progress.emit(0, 0, "正在扫描远端目录...")
            mac_app_dir = r.get("mac_app_dir", "/Users/bing/MyGithub/DuetFlow")
            remote_mf = sftp.remote_scan(
                self._ssh, remote_root, exclude, text_ext,
                prev_manifest=baseline_for_cache,
                mac_app_dir=mac_app_dir,
            )

            if self._is_cancelled():
                self.done.emit(False, "任务已被用户取消。")
                return

            mac_cached = sum(
                1 for rel, e in remote_mf.items()
                if not e.get("status") and baseline_for_cache.get(rel, {}).get("mtime") == e.get("mtime")
            )
            self.log.emit(
                f"✓ 远端扫描完毕，共 {len(remote_mf)} 个文件"
                + (f"（{mac_cached} 个命中 mtime 缓存，跳过 I/O）" if mac_cached else "")
            )
            if len(remote_mf) == 0:
                self.log.emit("⚠ 远端目录无任何文件！可能原因：远端目录不存在、路径含 ~ 未展开、或扫描脚本出错")

            baseline = baseline_for_cache  # 直接复用已加载的快照
            if not baseline:
                self.log.emit("未找到历史 baseline 快照，进入冷启动并集模式")
                baseline = {}

            self.log.emit("正在进行三路合并计算...")
            if r["is_win"]:
                win_mf, mac_mf = local_mf, remote_mf
            else:
                win_mf, mac_mf = remote_mf, local_mf

            plan = merge.three_way_merge(win_mf, mac_mf, baseline)

            # 诊断报告：操作类型统计 + 典型案例
            action_counts = {}
            sample_by_type = {}
            for a in plan:
                act = a["action"]
                action_counts[act] = action_counts.get(act, 0) + 1
                if act not in sample_by_type and act != "SKIP":
                    sample_by_type[act] = a["path"]

            self.log.emit("合并计算结果：")
            for act, cnt in sorted(action_counts.items(), key=lambda x: -x[1]):
                self.log.emit(f"  {act}: {cnt} 次")
            for act, path in sorted(sample_by_type.items()):
                self.log.emit(f"  典型案例 — {act}: {path}")
            self.log.emit(f"  本地 {len(local_mf)} 个文件  ×  远端 {len(remote_mf)} 个文件  ×  Baseline {len(baseline)} 条记录")

            # 熔断检查
            cb = cfg.get("safety", {}).get("circuit_breaker", {})
            triggered, q_count, ratio = trash.circuit_breaker_check(
                plan,
                len(local_mf) + len(remote_mf),
                cb.get("max_ratio", 0.20),
                cb.get("max_count", 50),
            )
            if triggered:
                self.done.emit(False, f"熔断！待隔离 {q_count} 个文件 ({ratio:.1%})，超出安全阈值。")
                return

            self._win_manifest = win_mf
            self._mac_manifest = mac_mf
            self.plan_ready.emit(plan)

        except Exception:
            self.done.emit(False, traceback.format_exc())
        finally:
            # 扫描完成后立即释放 SSH 连接，避免连接泄漏；执行阶段会重新建立连接。
            if self._ssh:
                try:
                    self._ssh.close()
                except Exception:
                    pass
                self._ssh = None
                self._sftp = None

    def execute_plan(self):
        try:
            cfg = self.cfg
            r = cfg["_resolved"]
            local_root = r["local_root"]
            remote_root = r["remote_root"]
            is_win = r["is_win"]
            plan = self.approved_plan
            total = len(plan)

            import shutil as _shutil

            # 执行阶段自行建立 SSH 连接（不复用扫描线程的连接，避免跨线程使用
            # paramiko 导致崩溃）。扫描阶段只在需要时才建立连接。
            if not self._ssh or not self._sftp:
                self.log.emit(f"正在连接 SSH 主机 {r['host']}:{r['port']} ...")
                self._ssh, self._sftp = sftp.connect(r)
                self.log.emit("✓ SSH 连接成功")

            for idx, item in enumerate(plan):
                if self._is_cancelled():
                    self.done.emit(False, "同步任务已被用户中途取消。")
                    return

                action = item["action"]
                path = item["path"]
                if action == "SKIP":
                    continue
                step_num = idx + 1
                msg = f"({step_num}/{total}) {action} -> {path}"
                self.log.emit(f"[{step_num}/{total}] {action}: {path}")
                self.progress.emit(step_num, total, msg)

                # 转换方向
                if is_win:
                    to_remote_action = "WIN_TO_MAC"
                    to_local_action = "MAC_TO_WIN"
                    quarantine_local_action = "QUARANTINE_WIN"
                    quarantine_remote_action = "QUARANTINE_MAC"
                else:
                    to_remote_action = "MAC_TO_WIN"
                    to_local_action = "WIN_TO_MAC"
                    quarantine_local_action = "QUARANTINE_MAC"
                    quarantine_remote_action = "QUARANTINE_WIN"

                local_full = Path(local_root) / path
                remote_full = str(PurePosixPath(remote_root) / path)

                if action == to_remote_action:
                    sftp.upload(self._sftp, local_full, remote_full)
                elif action == to_local_action:
                    sftp.download(self._sftp, remote_full, local_full)
                elif action == quarantine_local_action:
                    trash.quarantine_local(path, local_root)
                elif action == quarantine_remote_action:
                    remote_trash = str(PurePosixPath(remote_root).parent / ".sync_trash")
                    sftp.remote_quarantine(self._ssh, remote_full, remote_trash)
                elif action == "CONFLICT":
                    reason = item.get("reason", "")
                    if reason != "modified_vs_deleted":
                        conflict_name = item["conflict_name"]
                        local_conflict = local_full.parent / Path(conflict_name).name
                        if local_full.exists():
                            _shutil.copy2(str(local_full), str(local_conflict))
                        sftp.download(
                            self._sftp, remote_full,
                            local_conflict.parent / f"_remote_{Path(conflict_name).name}"
                        )

            # 优先保存 baseline（单独 try，避免被后续清理步骤异常连累而丢失历史记录）
            try:
                from duetflow.cli import save_baseline
                save_baseline(self._win_manifest, self._mac_manifest, self.approved_plan)
            except Exception as e:
                self.log.emit(f"⚠ 保存 baseline 快照失败: {e}")
            try:
                trash.purge_expired(local_root, cfg.get("safety", {}).get("quarantine_days", 30))
            except Exception as e:
                self.log.emit(f"⚠ 清理过期隔离文件失败: {e}")

            self.progress.emit(total, total, "同步完成")
            self.done.emit(True, "同步完成，Baseline 快照已成功更新。")

        except Exception:
            self.done.emit(False, traceback.format_exc())
        finally:
            if self._ssh:
                try:
                    self._ssh.close()
                except Exception:
                    pass


# ─── 删除与误删人工审核对话框 ───────────────────────────────────────────────

class DeletionReviewDialog(QDialog):
    """删除与误删人工审核对话框。"""

    def __init__(self, quarantine_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🗑 文件删除审核 — 人工确认")
        self.resize(1000, 560)
        self._quarantine_items = quarantine_items
        self._combos = []  # list of (item_dict, QComboBox)
        self.resolved_plan_updates = {}  # {path: updated_item_dict}

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 头部提示
        tip_lbl = QLabel(
            "<b>检测到以下文件在对端已不存在：</b><br>"
            "<font color='#64748b'>这可能是对端主动删除了文件，也可能是程序或人工误删。请逐项确认处置方式：</font>"
        )
        tip_lbl.setWordWrap(True)
        layout.addWidget(tip_lbl)

        # 批量快捷控制按钮行
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        all_quarantine_btn = QPushButton("一键全部隔离/删除")
        all_quarantine_btn.setObjectName("flat")
        all_quarantine_btn.clicked.connect(lambda: self._set_all_combo_index(0))
        btn_bar.addWidget(all_quarantine_btn)

        all_restore_btn = QPushButton("一键全部误删恢复")
        all_restore_btn.setObjectName("flat")
        all_restore_btn.clicked.connect(lambda: self._set_all_combo_index(1))
        btn_bar.addWidget(all_restore_btn)

        all_skip_btn = QPushButton("一键全部暂不处理")
        all_skip_btn.setObjectName("flat")
        all_skip_btn.clicked.connect(lambda: self._set_all_combo_index(2))
        btn_bar.addWidget(all_skip_btn)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # 表格
        self._table = QTableWidget(len(self._quarantine_items), 3)
        self._table.setHorizontalHeaderLabels(["相对文件路径", "状态来源", "处理动作"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._table.setColumnWidth(2, 200)  # 处理动作下拉框列宽足够显示
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        # 删除审核事关文件安全，路径必须完整可读：允许单元格换行并随内容撑高，
        # 悬停时显示完整路径。
        self._table.setWordWrap(True)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        for row, item in enumerate(self._quarantine_items):
            path = item["path"]
            action = item["action"]

            path_item = QTableWidgetItem(path)
            path_item.setToolTip(path)
            path_item.setData(Qt.UserRole, path)
            self._table.setItem(row, 0, path_item)

            if action == "QUARANTINE_WIN":
                src_text = "Mac 端已删除"
            else:
                src_text = "Windows 端已删除"
            src_item = QTableWidgetItem(src_text)
            src_item.setForeground(QColor(WARNING_YELLOW))
            self._table.setItem(row, 1, src_item)

            cb = QComboBox()
            cb.addItem("🗑 同步隔离 (确认删除)", "QUARANTINE")
            cb.addItem("🔄 误删恢复 (补回对端)", "RESTORE")
            cb.addItem("⏸ 暂不处理 (跳过)", "SKIP")
            cb.setCurrentIndex(0)  # 默认隔离
            # 处理动作下拉框必须清晰可读：给足宽度并单独设置样式，
            # 避免被表格单元格样式/列宽压成"进度条"。
            cb.setMinimumWidth(180)
            cb.setStyleSheet(
                "QComboBox { background-color: #f8fafc; border: 1px solid #e2e8f0;"
                " border-radius: 6px; padding: 5px 8px; font-size: 12px; color: #0f172a; }"
                "QComboBox::drop-down { border: none; width: 22px; }"
            )

            self._combos.append((item, cb))
            self._table.setCellWidget(row, 2, cb)

        layout.addWidget(self._table, 1)

        # 底部确定/取消按钮
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        cancel_btn = QPushButton("取消同步")
        cancel_btn.setObjectName("flat")
        cancel_btn.clicked.connect(self.reject)
        bottom_bar.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认并开始执行")
        confirm_btn.setObjectName("success")
        confirm_btn.clicked.connect(self._on_confirm)
        bottom_bar.addWidget(confirm_btn)

        layout.addLayout(bottom_bar)

    def _set_all_combo_index(self, index):
        for _, cb in self._combos:
            cb.setCurrentIndex(index)

    def _on_confirm(self):
        self.resolved_plan_updates = {}
        for item, cb in self._combos:
            opt = cb.currentData()
            orig_action = item["action"]
            path = item["path"]

            if opt == "QUARANTINE":
                self.resolved_plan_updates[path] = dict(item)
            elif opt == "RESTORE":
                if orig_action == "QUARANTINE_WIN":
                    new_action = "WIN_TO_MAC"
                else:
                    new_action = "MAC_TO_WIN"
                new_item = dict(item)
                new_item["action"] = new_action
                self.resolved_plan_updates[path] = new_item
            elif opt == "SKIP":
                new_item = dict(item)
                new_item["action"] = "SKIP"
                new_item["reason"] = "user_skipped_quarantine"
                self.resolved_plan_updates[path] = new_item

        self.accept()


# ─── 主窗口 ──────────────────────────────────────────────────────────────────

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DuetFlow 双端文件同步")
        self.resize(960, 680)
        self._cfg = None
        self._plan = None
        self._thread = None
        self._worker_obj = None

        # 连接选项卡数据
        self._connections = []          # list[dict]: {host, port, user, key_path}
        self._current_idx = -1          # 当前选中的选项卡索引
        self._tab_updating = False      # 防止信号递归

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("DuetFlow")
        title.setObjectName("title")

        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        self._status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._status_label)
        root.addLayout(header)

        # ── 连接选项卡栏 ─────────────────────────────────────────────────────
        self._build_connection_bar(root)

        # ── 连接设置卡片 ─────────────────────────────────────────────────────
        self._build_connection_card(root)

        # ── 本机 + 远端路径信息 ──────────────────────────────────────────────
        self._build_path_info(root)

        # ── Splitter: table left, log right ─────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        root.addWidget(splitter, 1)

        # Left: plan table
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(6)

        sec_label = QLabel("同步变更计划")
        sec_label.setObjectName("section")
        lv.addWidget(sec_label)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["动作", "相对文件路径", "冲突 / 备注"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        lv.addWidget(self._table)

        # Summary bar
        self._summary_label = QLabel("暂无预览计划")
        self._summary_label.setObjectName("subtitle")
        lv.addWidget(self._summary_label)

        splitter.addWidget(left)

        # Right: log
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(6)

        log_header = QHBoxLayout()
        log_label = QLabel("运行控制台日志")
        log_label.setObjectName("section")
        log_header.addWidget(log_label)
        log_header.addStretch()

        self._clear_log_btn = QPushButton("清空")
        self._clear_log_btn.setObjectName("flat")
        self._clear_log_btn.setFixedHeight(24)
        self._clear_log_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self._clear_log_btn.clicked.connect(lambda: self._log.clear())
        log_header.addWidget(self._clear_log_btn)

        rv.addLayout(log_header)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        rv.addWidget(self._log)

        splitter.addWidget(right)
        splitter.setSizes([600, 320])

        # ── Bottom Action Buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(24)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        btn_row.addWidget(self._progress_bar, 1)

        self._stop_btn = QPushButton("停止")
        self._stop_btn.setObjectName("danger")
        self._stop_btn.setFixedHeight(32)
        self._stop_btn.hide()
        self._stop_btn.clicked.connect(self._stop_task)
        btn_row.addWidget(self._stop_btn)

        self._scan_btn = QPushButton("扫描并预览变动")
        self._scan_btn.setFixedHeight(32)
        self._scan_btn.clicked.connect(self._start_scan)
        btn_row.addWidget(self._scan_btn)

        self._exec_btn = QPushButton("确认同步执行")
        self._exec_btn.setObjectName("success")
        self._exec_btn.setFixedHeight(32)
        self._exec_btn.setEnabled(False)
        self._exec_btn.clicked.connect(self._start_execute)
        btn_row.addWidget(self._exec_btn)

        root.addLayout(btn_row)

    def _build_connection_bar(self, parent_layout):
        """构建选项卡栏：QTabBar + "+" 新增按钮。"""
        bar_row = QHBoxLayout()
        bar_row.setSpacing(4)
        bar_row.setContentsMargins(0, 0, 0, 0)

        bar_label = QLabel("连接配置:")
        bar_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT_SECONDARY}; margin-right: 6px;")
        bar_row.addWidget(bar_label)

        self._conn_combo = QComboBox()
        self._conn_combo.setMinimumWidth(200)
        self._conn_combo.currentIndexChanged.connect(self._on_tab_changed)
        bar_row.addWidget(self._conn_combo)

        self._add_tab_btn = QPushButton("+ 新增")
        self._add_tab_btn.setObjectName("flat")
        self._add_tab_btn.setFixedHeight(30)
        self._add_tab_btn.clicked.connect(self._add_new_tab)
        bar_row.addWidget(self._add_tab_btn)

        self._save_tab_btn = QPushButton("保存连接")
        self._save_tab_btn.setObjectName("flat")
        self._save_tab_btn.setFixedHeight(30)
        self._save_tab_btn.clicked.connect(self._save_current_conn)
        bar_row.addWidget(self._save_tab_btn)

        self._del_tab_btn = QPushButton("删除当前连接")
        self._del_tab_btn.setObjectName("flat")
        self._del_tab_btn.setFixedHeight(30)
        self._del_tab_btn.clicked.connect(self._delete_current_tab)
        bar_row.addWidget(self._del_tab_btn)

        bar_row.addStretch()
        parent_layout.addLayout(bar_row)

    def _build_connection_card(self, parent_layout):
        """构建连接设置输入卡片。"""
        self._conn_card = QFrame()
        self._conn_card.setObjectName("card")
        card_layout = QVBoxLayout(self._conn_card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(8)

        # ── Row 1: Host + Port + User ──────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        row1.addWidget(QLabel("Host:"))
        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("e.g. 192.168.1.101")
        self._host_edit.setMinimumWidth(180)
        self._host_edit.textChanged.connect(self._on_field_changed)
        row1.addWidget(self._host_edit)

        row1.addSpacing(6)
        row1.addWidget(QLabel("Port:"))
        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText("22")
        self._port_edit.setFixedWidth(60)
        self._port_edit.setText("22")
        self._port_edit.textChanged.connect(self._on_field_changed)
        row1.addWidget(self._port_edit)

        row1.addSpacing(6)
        row1.addWidget(QLabel("User:"))
        self._user_edit = QLineEdit()
        self._user_edit.setPlaceholderText("username")
        self._user_edit.setMinimumWidth(120)
        self._user_edit.textChanged.connect(self._on_field_changed)
        row1.addWidget(self._user_edit)

        row1.addStretch()
        card_layout.addLayout(row1)

        # ── Row 2: Key path + Browse ───────────────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        row2.addWidget(QLabel("Key:"))
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("~/.ssh/id_rsa（留空自动探测）")
        self._key_edit.textChanged.connect(self._on_field_changed)
        row2.addWidget(self._key_edit, 1)

        self._browse_key_btn = QPushButton("浏览...")
        self._browse_key_btn.setObjectName("browse_key")
        self._browse_key_btn.setFixedHeight(30)
        self._browse_key_btn.clicked.connect(self._select_key_file)
        row2.addWidget(self._browse_key_btn)

        card_layout.addLayout(row2)

        # ── Row 3: Test button + status ────────────────────────────────────
        row3 = QHBoxLayout()
        row3.setSpacing(12)

        self._test_conn_btn = QPushButton("测试连接")
        self._test_conn_btn.setObjectName("flat")
        self._test_conn_btn.setFixedHeight(32)
        self._test_conn_btn.clicked.connect(self._test_connection)
        row3.addWidget(self._test_conn_btn)

        self._conn_status_lbl = QLabel("未检测")
        status_font = self._conn_status_lbl.font()
        status_font.setPointSize(12)
        status_font.setBold(True)
        self._conn_status_lbl.setFont(status_font)
        self._conn_status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        row3.addWidget(self._conn_status_lbl)

        self._conn_err_detail_lbl = QLabel("")
        self._conn_err_detail_lbl.setStyleSheet(f"color: {DANGER_RED}; font-size: 12px; font-weight: 500;")
        self._conn_err_detail_lbl.setWordWrap(True)
        self._conn_err_detail_lbl.setVisible(False)
        row3.addWidget(self._conn_err_detail_lbl, 1)

        row3.addStretch()

        # 本机 IP 选择（内嵌在行尾）
        row3.addWidget(QLabel("本机 IP:"))
        self._local_ip_combo = QComboBox()
        self._local_ip_combo.setMinimumWidth(140)
        self._local_ip_combo.currentIndexChanged.connect(self._on_local_ip_selected)
        row3.addWidget(self._local_ip_combo)

        card_layout.addLayout(row3)

        parent_layout.addWidget(self._conn_card)

    def _build_path_info(self, parent_layout):
        """构建同步路径设置卡片。"""
        self._path_card = QFrame()
        self._path_card.setObjectName("card")
        path_layout = QHBoxLayout(self._path_card)
        path_layout.setContentsMargins(16, 10, 16, 10)
        path_layout.setSpacing(12)

        # 本地路径
        path_layout.addWidget(QLabel("本地目录:"))
        self._local_path_edit = QLineEdit()
        self._local_path_edit.setPlaceholderText("选择或输入本地同步根目录 (e.g. D:/Work)")
        self._local_path_edit.editingFinished.connect(self._on_sync_path_changed)
        path_layout.addWidget(self._local_path_edit, 1)

        self._browse_local_btn = QPushButton("选择目录...")
        self._browse_local_btn.setObjectName("flat")
        self._browse_local_btn.setFixedHeight(30)
        self._browse_local_btn.clicked.connect(self._select_local_folder)
        path_layout.addWidget(self._browse_local_btn)

        path_layout.addSpacing(16)

        # 远端路径
        path_layout.addWidget(QLabel("远端目录:"))
        self._remote_path_edit = QLineEdit()
        self._remote_path_edit.setPlaceholderText("输入远端同步根目录 (e.g. /Users/name/WorkSpace)")
        self._remote_path_edit.editingFinished.connect(self._on_sync_path_changed)
        path_layout.addWidget(self._remote_path_edit, 1)

        parent_layout.addWidget(self._path_card)

    # ── 连接选项卡管理 ──────────────────────────────────────────────────────

    def _on_tab_changed(self, index):
        """切换选项卡 → 将对应连接的参数填入输入框。"""
        if self._tab_updating:
            return
        if index < 0 or index >= len(self._connections):
            return

        self._current_idx = index
        conn = self._connections[index]
        self._fill_fields_from_conn(conn)
        self._update_resolved_from_fields()

    def _fill_fields_from_conn(self, conn):
        """将连接数据填入输入框（不触发保存回写）。"""
        self._tab_updating = True
        self._host_edit.setText(conn.get("host", ""))
        self._port_edit.setText(str(conn.get("port", 22)))
        self._user_edit.setText(conn.get("user", ""))
        self._key_edit.setText(conn.get("key_path", ""))
        # 重置连接状态
        self._conn_status_lbl.setText("未检测")
        self._conn_status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._conn_err_detail_lbl.setVisible(False)
        self._tab_updating = False

    def _on_field_changed(self):
        """输入字段变更时，实时同步到当前连接数据与下拉列表。"""
        if self._tab_updating:
            return
        if self._current_idx < 0 or self._current_idx >= len(self._connections):
            return
        conn = self._connections[self._current_idx]
        conn["host"] = self._host_edit.text().strip()
        conn["port"] = self._port_number()
        conn["user"] = self._user_edit.text().strip()
        conn["key_path"] = self._key_edit.text().strip()
        # 更新下拉框文本
        label = conn["host"] or "新连接"
        self._conn_combo.setItemText(self._current_idx, label)
        # 重置连接状态
        self._conn_status_lbl.setText("未检测")
        self._conn_status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._conn_err_detail_lbl.setVisible(False)

    def _add_new_tab(self):
        """新增一个空白连接配置。"""
        if len(self._connections) >= MAX_CONNECTIONS:
            QMessageBox.information(self, "提示", f"最多保留 {MAX_CONNECTIONS} 个连接记录")
            return

        new_conn = {"host": "", "port": 22, "user": "", "key_path": ""}
        self._connections.append(new_conn)

        self._tab_updating = True
        self._conn_combo.addItem("新连接")
        self._tab_updating = False

        idx = self._conn_combo.count() - 1
        self._conn_combo.setCurrentIndex(idx)
        self._current_idx = idx
        self._fill_fields_from_conn(new_conn)

        # 聚焦到 Host 输入框
        self._host_edit.setFocus()
        self._host_edit.selectAll()

        # 新增的空连接不立即落盘，等用户填写后点"保存连接"再持久化，
        # 避免空的脏连接被保存下来并被误选。

    def _save_current_conn(self):
        """将当前输入卡片的内容保存到当前连接记录并持久化。"""
        if self._current_idx < 0 or self._current_idx >= len(self._connections):
            QMessageBox.information(self, "提示", "请先新增一个连接")
            return
        host = self._host_edit.text().strip()
        if not host:
            QMessageBox.warning(self, "提示", "请先填写 Host 地址再保存")
            return
        conn = self._connections[self._current_idx]
        conn["host"] = host
        conn["port"] = self._port_number()
        conn["user"] = self._user_edit.text().strip()
        conn["key_path"] = self._key_edit.text().strip()
        # 同步更新下拉框显示名
        self._tab_updating = True
        self._conn_combo.setItemText(self._current_idx, host)
        self._tab_updating = False
        self._save_connections_to_disk()
        self._update_resolved_from_fields()
        self._append_log(f"连接配置已保存: {host}")

    def _delete_current_tab(self):
        """删除当前选中的连接配置。"""
        if len(self._connections) <= 1:
            QMessageBox.information(self, "提示", "至少保留一个连接记录")
            return
        index = self._conn_combo.currentIndex()
        if index < 0 or index >= len(self._connections):
            return

        # 移除数据
        self._connections.pop(index)
        self._tab_updating = True
        self._conn_combo.removeItem(index)
        self._tab_updating = False

        # 切换选中
        new_count = self._conn_combo.count()
        if new_count > 0:
            new_idx = min(index, new_count - 1)
            self._conn_combo.setCurrentIndex(new_idx)
        else:
            self._current_idx = -1

        self._save_connections_to_disk()

    def _select_key_file(self):
        """浏览选择密钥文件。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 SSH 私钥", str(Path.home() / ".ssh"),
            "所有文件 (*);;私钥文件 (*.pem;*.key)"
        )
        if path:
            self._key_edit.setText(path)

    def _save_connections_to_disk(self):
        """将当前连接列表持久化到 connections.json。"""
        from duetflow.config import save_connections
        save_connections(self._connections, self._conn_combo.currentIndex())

    # ── 构建运行时配置 ──────────────────────────────────────────────────────

    def _port_number(self):
        """从端口输入框解析整数，非法或空时回退到 22。"""
        text = self._port_edit.text().strip()
        try:
            port = int(text)
            if 1 <= port <= 65535:
                return port
        except ValueError:
            pass
        return 22

    def _select_local_folder(self):
        """选择本地根同步目录。"""
        current = self._local_path_edit.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "选择本地同步根目录", current)
        if folder:
            self._local_path_edit.setText(folder)
            self._on_sync_path_changed()

    def _on_sync_path_changed(self):
        """同步根路径变更回调：写回 config.json5 并更新内存配置。"""
        if not self._cfg:
            return
        local_path = self._local_path_edit.text().strip()
        remote_path = self._remote_path_edit.text().strip()
        is_win = sys.platform == "win32"
        win_root = local_path if is_win else remote_path
        mac_root = remote_path if is_win else local_path

        self._cfg["sync_paths"]["windows_root"] = win_root
        self._cfg["sync_paths"]["mac_root"] = mac_root
        self._update_resolved_from_fields()

        from duetflow import config as cfg_mod
        cfg_mod.save_sync_paths(win_root, mac_root)

    def _update_resolved_from_fields(self):
        """从当前输入字段 + self._cfg 的静态配置，构建 _resolved。"""
        if not self._cfg:
            return

        host = self._host_edit.text().strip()
        port = self._port_number()
        user = self._user_edit.text().strip()
        key_path = self._key_edit.text().strip()

        local_path = self._local_path_edit.text().strip()
        remote_path = self._remote_path_edit.text().strip()

        # 如果密钥为空，自动探测
        if not key_path:
            for name in ("id_rsa", "id_ed25519", "id_ecdsa"):
                p = Path.home() / ".ssh" / name
                if p.exists():
                    key_path = str(p)
                    break

        r = self._cfg["_resolved"]
        r["host"] = host
        r["port"] = port
        r["user"] = user
        r["key_path"] = key_path
        r["local_root"] = local_path
        r["remote_root"] = remote_path

        local_ip = self._local_ip_combo.itemData(self._local_ip_combo.currentIndex()) or ""
        r["local_ip"] = local_ip

    # ── Config ───────────────────────────────────────────────────────────────

    def _load_config(self):
        from duetflow import config as cfg_mod

        # config.load() 内部自动处理：从 example 复制 / 从旧 config.yaml 迁移
        try:
            self._cfg = cfg_mod.load()
        except SystemExit:
            self._set_status("配置文件已生成，请编辑 config.json5 后重启", DANGER_RED)
            self._append_log("首次运行：config.json5 已自动生成，请编辑后重新启动程序")
            self._scan_btn.setEnabled(False)
            return

        try:
            r = self._cfg["_resolved"]

            # 设置本机 IP 下拉
            scanned_ips = r.get("scanned_ips", [])
            selected_ip = r.get("local_ip", "")
            self._local_ip_combo.blockSignals(True)
            self._local_ip_combo.clear()
            sel_idx = 0
            for idx, item in enumerate(scanned_ips):
                label = item.get("label", item.get("ip"))
                ip_val = item.get("ip")
                self._local_ip_combo.addItem(label, ip_val)
                if ip_val == selected_ip:
                    sel_idx = idx
            if self._local_ip_combo.count() > 0:
                self._local_ip_combo.setCurrentIndex(sel_idx)
            self._local_ip_combo.blockSignals(False)

            # 更新路径信息
            win_root = self._cfg["sync_paths"].get("windows_root", "")
            mac_root = self._cfg["sync_paths"].get("mac_root", "")
            is_win = sys.platform == "win32"
            local_path = win_root if is_win else mac_root
            remote_path = mac_root if is_win else win_root
            self._local_path_edit.setText(local_path)
            self._remote_path_edit.setText(remote_path)

            # 加载连接历史
            connections, last_idx = cfg_mod.load_connections()

            # 过滤掉"空壳连接"（host 为空，未真正填写的记录），避免误选到空连接
            # 而用空 host 去连接（导致 WinError 10013）。
            if connections:
                filtered = [c for c in connections if (c.get("host") or "").strip()]
                if len(filtered) != len(connections):
                    connections = filtered
                    if last_idx >= len(connections):
                        last_idx = max(0, len(connections) - 1)
                    if connections:
                        cfg_mod.save_connections(connections, last_idx)

            # 如果没有历史连接，从旧配置创建一个
            if not connections:
                old_host = self._cfg.get("ssh", {}).get("host", "")
                old_user = self._cfg.get("ssh", {}).get("user", "")
                old_port = self._cfg.get("ssh", {}).get("port", 22)
                old_key = r.get("key_path", "")
                if old_host:
                    connections = [{"host": old_host, "port": old_port, "user": old_user, "key_path": old_key}]
                    cfg_mod.save_connections(connections, 0)

            self._connections = connections

            # 填充下拉列表
            self._tab_updating = True
            self._conn_combo.clear()
            for conn in connections:
                label = conn.get("host", "") or "新连接"
                self._conn_combo.addItem(label)
            self._tab_updating = False

            # 选中上次使用的连接
            if connections:
                safe_idx = max(0, min(last_idx, len(connections) - 1))
                self._conn_combo.setCurrentIndex(safe_idx)
                self._current_idx = safe_idx
                self._fill_fields_from_conn(connections[safe_idx])

            self._update_resolved_from_fields()
            self._append_log(f"配置文件加载成功，当前本机 IP: {r['local_ip']}")
            self._append_log(f"已加载 {len(connections)} 个连接记录")
        except Exception as e:
            self._set_status(f"配置加载失败: {e}", DANGER_RED)
            self._append_log(f"配置加载错误: {e}")
            self._scan_btn.setEnabled(False)

    def _on_local_ip_selected(self, index):
        if index < 0 or not self._cfg:
            return
        new_ip = self._local_ip_combo.itemData(index)
        current_ip = self._cfg.get("_resolved", {}).get("local_ip")
        if new_ip and new_ip != current_ip:
            self._cfg["_resolved"]["local_ip"] = new_ip
            from duetflow import config as cfg_mod
            cfg_mod.save_local_ip(new_ip)
            self._append_log(f"已选择并保存本机 IP 为: {new_ip}")

    # ── Connection Test ──────────────────────────────────────────────────────

    def _test_connection(self):
        if not self._cfg:
            return
        self._update_resolved_from_fields()
        r = self._cfg["_resolved"]

        if not r.get("host"):
            QMessageBox.warning(self, "提示", "请先输入目标主机地址")
            return
        if not r.get("user"):
            QMessageBox.warning(self, "提示", "请先输入用户名")
            return

        self._conn_status_lbl.setText("检测中...")
        self._conn_status_lbl.setStyleSheet(f"color: {WARNING_YELLOW}; font-weight: bold;")
        self._test_conn_btn.setEnabled(False)
        self._conn_err_detail_lbl.setVisible(False)

        self._conn_tester = ConnectionTester(r)
        self._conn_thread = QThread()
        self._conn_tester.moveToThread(self._conn_thread)
        self._conn_thread.started.connect(self._conn_tester.test_connection)
        self._conn_tester.result.connect(self._on_conn_test_result)
        self._conn_thread.start()

    def _on_conn_test_result(self, ok, msg, rtt):
        if hasattr(self, "_conn_thread") and self._conn_thread:
            self._conn_thread.quit()
            self._conn_thread.wait()
            self._conn_thread = None
        self._conn_tester = None

        self._test_conn_btn.setEnabled(True)
        if ok:
            self._conn_status_lbl.setText(f"在线 ({int(rtt)}ms)")
            self._conn_status_lbl.setStyleSheet(f"color: {SUCCESS_GREEN}; font-weight: bold;")
            self._conn_err_detail_lbl.setVisible(False)
            self._append_log(f"网络探针: 成功连接至远端主机 ({int(rtt)}ms)")

            # 连接成功 → 确保当前连接的参数已保存到选项卡
            if self._current_idx >= 0 and self._current_idx < len(self._connections):
                conn = self._connections[self._current_idx]
                host = self._host_edit.text().strip()
                # 如果是空白连接（新建的），自动填入
                if not conn.get("host"):
                    conn["host"] = host
                    conn["port"] = self._port_number()
                    conn["user"] = self._user_edit.text().strip()
                    conn["key_path"] = self._key_edit.text().strip()
                    self._conn_combo.setItemText(self._current_idx, host or "新连接")
                self._save_connections_to_disk()
        else:
            self._conn_status_lbl.setText("无法连接")
            self._conn_status_lbl.setStyleSheet(f"color: {DANGER_RED}; font-weight: bold;")
            self._conn_err_detail_lbl.setText(f"{msg}")
            self._conn_err_detail_lbl.setToolTip(msg)
            self._conn_err_detail_lbl.setVisible(True)
            self._append_log(f"网络探针: 连接异常 - {msg}")

    # ── Scan ─────────────────────────────────────────────────────────────────

    def _start_scan(self):
        if not self._cfg:
            return
        self._update_resolved_from_fields()
        r = self._cfg["_resolved"]

        # 扫描前校验连接参数，避免用空 host 去连 SSH（会触发 WinError 10013）
        if not r.get("host"):
            QMessageBox.warning(self, "提示", "请先填写远端主机 Host 地址（或选择一个已保存的连接）")
            return
        if not r.get("user"):
            QMessageBox.warning(self, "提示", "请先填写远端 SSH 用户名")
            return

        self._set_busy(True)
        self._table.setRowCount(0)
        self._plan = None
        self._exec_btn.setEnabled(False)
        self._append_log("─" * 45)
        self._append_log("开始扫描本地与远端文件...")

        worker_obj = SyncWorker(self._cfg)
        self._worker_obj = worker_obj
        thread = QThread()
        worker_obj.moveToThread(thread)
        thread.started.connect(worker_obj.scan_and_plan)
        worker_obj.log.connect(self._append_log)
        worker_obj.progress.connect(self._on_progress_update)
        worker_obj.plan_ready.connect(self._on_plan_ready)
        worker_obj.done.connect(lambda ok, msg: self._on_done(ok, msg, thread))
        thread.start()
        self._thread = thread

    def _on_plan_ready(self, plan):
        self._plan = plan
        active = [a for a in plan if a["action"] != "SKIP"]
        self._fill_table(active)

        counts = {}
        for item in plan:
            counts[item["action"]] = counts.get(item["action"], 0) + 1
        parts = []
        for key, (label, _) in ACTION_META.items():
            n = counts.get(key, 0)
            if n:
                parts.append(f"{label}: {n}")
        self._summary_label.setText("  |  ".join(parts) if parts else "双端一致，无需要执行的操作")

        if active:
            self._exec_btn.setEnabled(True)
            self._set_status("预览计算完成，等待确认执行", WARNING_YELLOW)
        else:
            self._set_status("双端文件完全一致", SUCCESS_GREEN)
        self._set_busy(False)

    def _fill_table(self, plan):
        self._table.setRowCount(len(plan))
        for row, item in enumerate(plan):
            action = item["action"]
            label, color = ACTION_META.get(action, (action, TEXT_PRIMARY))
            remark = item.get("conflict_name", item.get("reason", ""))

            action_item = QTableWidgetItem(label)
            action_item.setForeground(QColor(color))
            item_font = action_item.font()
            item_font.setPointSize(13)
            item_font.setBold(True)
            action_item.setFont(item_font)

            self._table.setItem(row, 0, action_item)
            self._table.setItem(row, 1, QTableWidgetItem(item["path"]))
            self._table.setItem(row, 2, QTableWidgetItem(remark or ""))

    # ── Execute ──────────────────────────────────────────────────────────────

    def _start_execute(self):
        try:
            self._start_execute_inner()
        except Exception:
            import traceback as _tb
            msg = _tb.format_exc()
            self._append_log(f"[未预期错误]\n{msg}")
            self._set_status("发生未预期错误", DANGER_RED)
            self._set_busy(False)
            QMessageBox.critical(self, "执行错误", msg)

    def _start_execute_inner(self):
        if not self._plan:
            return
        active = [a for a in self._plan if a["action"] != "SKIP"]
        if not active:
            return

        # 检查是否存在待隔离/删除条目，如存在则先弹出人工审核窗口
        quarantine_items = [a for a in active if a["action"] in ("QUARANTINE_WIN", "QUARANTINE_MAC")]
        if quarantine_items:
            dialog = DeletionReviewDialog(quarantine_items, parent=self)
            if dialog.exec() == QDialog.Accepted:
                updates = dialog.resolved_plan_updates
                updated_active = []
                for item in active:
                    p = item["path"]
                    if p in updates:
                        updated_active.append(updates[p])
                    else:
                        updated_active.append(item)
                active = updated_active
            else:
                self._append_log("用户取消了文件删除审核，同步中断。")
                return

        # 过滤可能全部变为了 SKIP 的情况
        active_to_run = [a for a in active if a["action"] != "SKIP"]
        if not active_to_run:
            self._append_log("所有隔离/删除操作已被选择跳过，无其他待执行变动。")
            self._set_status("变动已全被跳过", WARNING_YELLOW)
            skipped_quarantines = [a for a in active if a.get("reason") == "user_skipped_quarantine"]
            if skipped_quarantines:
                scan_worker = getattr(self, "_worker_obj", None)
                win_manifest = scan_worker._win_manifest if scan_worker else None
                mac_manifest = scan_worker._mac_manifest if scan_worker else None
                try:
                    from duetflow.cli import save_baseline
                    save_baseline(win_manifest, mac_manifest, active)
                    self._append_log("✓ Baseline 已更新（从基线中清除了已选择跳过的删除条目）")
                except Exception as e:
                    self._append_log(f"⚠ 保存 baseline 失败: {e}")
            return

        self._set_busy(True)
        self._exec_btn.setEnabled(False)
        self._append_log("─" * 45)
        self._append_log("确认无误，开始执行同步文件传输与隔离...")

        # 复用扫描阶段得到的清单（纯数据），但 SSH/SFTP 连接不跨线程复用——
        # paramiko 的 SFTP 连接非线程安全，跨线程使用可能导致进程崩溃退出。
        # 执行阶段会自行建立新连接。
        scan_worker = getattr(self, "_worker_obj", None)
        win_manifest = scan_worker._win_manifest if scan_worker else None
        mac_manifest = scan_worker._mac_manifest if scan_worker else None
        worker = SyncWorker(
            self._cfg, do_execute=True, approved_plan=active,
            win_manifest=win_manifest, mac_manifest=mac_manifest,
        )
        self._worker_obj = worker
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.execute_plan)
        worker.log.connect(self._append_log)
        worker.progress.connect(self._on_progress_update)
        worker.done.connect(lambda ok, msg: self._on_done(ok, msg, thread))
        thread.start()
        self._thread = thread

    def _stop_task(self):
        if self._worker_obj:
            self._append_log("正在发送中途取消指令，等待当前异步步骤安全退出...")
            self._stop_btn.setEnabled(False)
            self._stop_btn.setText("正在取消...")
            self._worker_obj.stop()

    def _on_progress_update(self, current, total, msg):
        self._set_status(msg, ACCENT_BLUE)
        if total == 0:
            self._progress_bar.setRange(0, 0)  # Busy 走马灯模式
        else:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)

    def _on_done(self, ok, msg, thread):
        thread.quit()
        thread.wait()
        self._set_busy(False)
        if ok:
            self._set_status("同步完成", SUCCESS_GREEN)
            self._exec_btn.setEnabled(False)
        else:
            if "取消" in msg:
                self._set_status("任务已取消", WARNING_YELLOW)
            else:
                self._set_status("发生错误", DANGER_RED)
                self._append_log(f"[错误提示]\n{msg}")
        self._append_log(msg)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _append_log(self, text):
        self._log.append(text)
        self._log.verticalScrollBar().setValue(self._log.verticalScrollBar().maximum())

    def _set_status(self, text, color=TEXT_PRIMARY):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _set_busy(self, busy):
        self._scan_btn.setEnabled(not busy)
        self._scan_btn.setText("正在计算中..." if busy else "扫描并预览变动")
        if busy:
            self._progress_bar.show()
            self._progress_bar.setRange(0, 0)
            self._stop_btn.show()
            self._stop_btn.setEnabled(True)
            self._stop_btn.setText("停止")
        else:
            self._progress_bar.hide()
            self._stop_btn.hide()


# ─── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    # ── 全局异常钩子：把崩溃信息写到 crash.log 并弹框 ──────────────────────
    import traceback as _tb

    _crash_log = ROOT / "crash.log"

    def _excepthook(exc_type, exc_value, exc_tb):
        text = "".join(_tb.format_exception(exc_type, exc_value, exc_tb))
        try:
            with open(_crash_log, "a", encoding="utf-8") as f:
                from datetime import datetime as _dt
                f.write(f"\n{'='*60}\n{_dt.now().isoformat()}\n{text}\n")
        except Exception:
            pass
        # 如果 QApplication 还活着，弹框
        try:
            QMessageBox.critical(None, "DuetFlow 未捕获异常", text)
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    app.setApplicationName("DuetFlow")

    # 全局浅色调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(LIGHT_BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Base, QColor(CARD_BG))
    palette.setColor(QPalette.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Button, QColor(CARD_BG))
    palette.setColor(QPalette.ButtonText, QColor(TEXT_PRIMARY))
    app.setPalette(palette)
    app.setStyleSheet(QSS)

    icon_path = ROOT / "assets" / "icon.ico"
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

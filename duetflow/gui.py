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
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from duetflow import config, merge, scanner, sftp, trash

ROOT = Path(__file__).resolve().parent.parent

# ─── macOS Light 风格调色板 ───────────────────────────────────────────────────

LIGHT_BG = "#f5f5f7"          # 系统全局浅灰背景
CARD_BG = "#ffffff"           # 卡片纯白背景
BORDER_COLOR = "#e5e5ea"      # 浅灰边框
TEXT_PRIMARY = "#1d1d1f"      # 核心文字深灰/近黑
TEXT_SECONDARY = "#86868b"    # 次要说明文字
ACCENT_BLUE = "#0066cc"       # 苹果蓝
SUCCESS_GREEN = "#28cd41"     # 活力绿
WARNING_YELLOW = "#ff9500"    # 警告橙
DANGER_RED = "#ff3b30"        # 危险红
TABLE_ALT_BG = "#fafafa"      # 表格交替行颜色

QSS = f"""
QWidget {{
    background-color: {LIGHT_BG};
    color: {TEXT_PRIMARY};
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 14px;
}}

QFrame#card {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
}}

QComboBox {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: 500;
}}
QComboBox:hover {{
    border-color: {ACCENT_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QPushButton {{
    background-color: {ACCENT_BLUE};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 14px;
}}
QPushButton:hover {{
    background-color: #0055b3;
}}
QPushButton:pressed {{
    background-color: #004499;
}}
QPushButton:disabled {{
    background-color: {BORDER_COLOR};
    color: {TEXT_SECONDARY};
}}

QPushButton#danger {{
    background-color: {DANGER_RED};
}}
QPushButton#danger:hover {{
    background-color: #e03228;
}}

QPushButton#success {{
    background-color: {SUCCESS_GREEN};
}}
QPushButton#success:hover {{
    background-color: #22b83a;
}}

QPushButton#flat {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    font-weight: 500;
    font-size: 13px;
    padding: 6px 12px;
}}
QPushButton#flat:hover {{
    background-color: #f0f0f2;
    border-color: #d1d1d6;
}}

QPushButton#del_host_btn {{
    background-color: transparent;
    color: #888888;
    border: none;
    font-size: 13px;
    font-weight: bold;
    padding: 0px;
    margin: 0px;
}}
QPushButton#del_host_btn:hover {{
    color: #e53935;
    background-color: rgba(229, 57, 53, 0.15);
    border-radius: 4px;
}}

QSpinBox {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 2px 4px;
    font-size: 13px;
    font-weight: 500;
}}
QSpinBox:hover {{
    border-color: {ACCENT_BLUE};
}}

QTableWidget {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    gridline-color: #f0f0f5;
    selection-background-color: #0066cc1a;
    selection-color: {TEXT_PRIMARY};
    alternate-background-color: {TABLE_ALT_BG};
    font-size: 14px;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border: none;
}}
QHeaderView::section {{
    background-color: #ebebeb;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 700;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {BORDER_COLOR};
}}

QTextEdit {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 10px;
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    color: {TEXT_PRIMARY};
    line-height: 1.4;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #d1d1d6;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #a1a1a6;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QSplitter::handle {{
    background: {BORDER_COLOR};
    width: 1px;
}}

QLabel#title {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}
QLabel#subtitle {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}
QLabel#section {{
    font-size: 13px;
    font-weight: 700;
    color: {TEXT_SECONDARY};
    letter-spacing: 0.5px;
}}
"""

ACTION_META = {
    "WIN_TO_MAC":    ("▲ Win → Mac",   ACCENT_BLUE),
    "MAC_TO_WIN":    ("▼ Mac → Win",   SUCCESS_GREEN),
    "QUARANTINE_WIN": ("🗑 隔离 Win",   WARNING_YELLOW),
    "QUARANTINE_MAC": ("🗑 隔离 Mac",   WARNING_YELLOW),
    "CONFLICT":      ("⚡ 冲突",        DANGER_RED),
    "SKIP":          ("— 跳过",         TEXT_SECONDARY),
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

    log = Signal(str)           # 普通日志行
    plan_ready = Signal(list)   # dry-run plan 完成
    done = Signal(bool, str)    # 完成(success, message)

    def __init__(self, cfg, do_execute=False, approved_plan=None):
        super().__init__()
        self.cfg = cfg
        self.do_execute = do_execute
        self.approved_plan = approved_plan
        self._ssh = None
        self._sftp = None
        self._win_manifest = None
        self._mac_manifest = None

    def scan_and_plan(self):
        try:
            cfg = self.cfg
            r = cfg["_resolved"]
            local_root = r["local_root"]
            remote_root = r["remote_root"]
            exclude = cfg.get("exclude", [])
            text_ext = cfg.get("text_extensions", [])

            self.log.emit(f"扫描本地: {local_root}")
            local_mf = scanner.scan(local_root, exclude, text_ext)
            self.log.emit(f"  → {len(local_mf)} 个文件")

            self.log.emit(f"连接 {r['host']}:{r['port']} ...")
            self._ssh, self._sftp = sftp.connect(r)
            self.log.emit("  → 连接成功")

            self.log.emit(f"扫描远端: {remote_root}")
            remote_mf = sftp.remote_scan(self._ssh, remote_root, exclude, text_ext)
            self.log.emit(f"  → {len(remote_mf)} 个文件")

            from duetflow.cli import load_baseline
            baseline = load_baseline()
            if not baseline:
                self.log.emit("未找到 baseline，进入冷启动（并集）模式")
                baseline = {}

            self.log.emit("计算三路合并...")
            # 将本地作为 win_manifest，远端作为 mac_manifest (统一命名处理)
            if r["is_win"]:
                win_mf, mac_mf = local_mf, remote_mf
            else:
                win_mf, mac_mf = remote_mf, local_mf

            plan = merge.three_way_merge(win_mf, mac_mf, baseline)

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

    def execute_plan(self):
        try:
            cfg = self.cfg
            r = cfg["_resolved"]
            local_root = r["local_root"]
            remote_root = r["remote_root"]
            is_win = r["is_win"]
            plan = self.approved_plan

            import shutil as _shutil

            for item in plan:
                action = item["action"]
                path = item["path"]
                
                # 转换方向为 [本地 -> 远端] 或 [远端 -> 本地]
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
                    self.log.emit(f"▲ {path}")
                    sftp.upload(self._sftp, local_full, remote_full)
                elif action == to_local_action:
                    self.log.emit(f"▼ {path}")
                    sftp.download(self._sftp, remote_full, local_full)
                elif action == quarantine_local_action:
                    self.log.emit(f"🗑 隔离本地: {path}")
                    trash.quarantine_local(path, local_root)
                elif action == quarantine_remote_action:
                    self.log.emit(f"🗑 隔离远端: {path}")
                    remote_trash = str(PurePosixPath(remote_root).parent / ".sync_trash")
                    sftp.remote_quarantine(self._ssh, remote_full, remote_trash)
                elif action == "CONFLICT":
                    reason = item.get("reason", "")
                    if reason == "modified_vs_deleted":
                        self.log.emit(f"⚡ 冲突(改/删) 跳过: {path}")
                    else:
                        conflict_name = item["conflict_name"]
                        local_conflict = local_full.parent / Path(conflict_name).name
                        if local_full.exists():
                            _shutil.copy2(str(local_full), str(local_conflict))
                        sftp.download(
                            self._sftp, remote_full,
                            local_conflict.parent / f"_remote_{Path(conflict_name).name}"
                        )
                        self.log.emit(f"⚡ 冲突保留: {conflict_name}")

            from duetflow.cli import save_baseline
            save_baseline(self._win_manifest, self._mac_manifest)
            trash.purge_expired(local_root, cfg.get("safety", {}).get("quarantine_days", 30))

            self.done.emit(True, "同步完成，Baseline 已更新。")

        except Exception:
            self.done.emit(False, traceback.format_exc())
        finally:
            if self._ssh:
                self._ssh.close()


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

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("🎶 DuetFlow")
        title.setObjectName("title")
        sub = QLabel("双端镜像级文件同步引擎")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignVCenter)

        self._open_cfg_btn = QPushButton("📝 编辑配置")
        self._open_cfg_btn.setObjectName("flat")
        self._open_cfg_btn.clicked.connect(self._open_config)

        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        self._status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header.addWidget(title)
        header.addSpacing(12)
        header.addWidget(sub)
        header.addStretch()
        header.addWidget(self._open_cfg_btn)
        header.addSpacing(16)
        header.addWidget(self._status_label)
        root.addLayout(header)

        # ── Device Cards (本机与对方设备信息) ─────────────────────────────────
        devices_layout = QHBoxLayout()
        devices_layout.setSpacing(16)

        # 1. 本机设备卡片
        self._local_card = QFrame()
        self._local_card.setObjectName("card")
        lc_layout = QVBoxLayout(self._local_card)
        lc_layout.setContentsMargins(14, 12, 14, 12)
        lc_layout.setSpacing(6)

        sys_name = "Windows" if sys.platform == "win32" else ("macOS" if sys.platform == "darwin" else "Linux")

        lc_title = QLabel(f"💻 本机 ({sys_name})")
        font_13_bold = lc_title.font()
        font_13_bold.setPointSize(13)
        font_13_bold.setBold(True)
        lc_title.setFont(font_13_bold)
        lc_title.setStyleSheet(f"color: {TEXT_PRIMARY};")

        lc_ip_layout = QHBoxLayout()
        lc_ip_lbl = QLabel("IP:")
        lc_ip_lbl.setObjectName("subtitle")

        self._local_ip_combo = QComboBox()
        self._local_ip_combo.setMinimumWidth(160)
        self._local_ip_combo.currentIndexChanged.connect(self._on_local_ip_selected)

        lc_ip_layout.addWidget(lc_ip_lbl)
        lc_ip_layout.addWidget(self._local_ip_combo)
        lc_ip_layout.addStretch()

        self._local_path_lbl = QLabel("本地根路径: 未配置")
        self._local_path_lbl.setObjectName("subtitle")
        self._local_path_lbl.setWordWrap(True)

        lc_layout.addWidget(lc_title)
        lc_layout.addLayout(lc_ip_layout)
        lc_layout.addWidget(self._local_path_lbl)
        lc_layout.addStretch()

        # 2. 对方设备卡片
        self._remote_card = QFrame()
        self._remote_card.setObjectName("card")
        rc_layout = QVBoxLayout(self._remote_card)
        rc_layout.setContentsMargins(14, 12, 14, 12)
        rc_layout.setSpacing(6)

        rc_top = QHBoxLayout()
        rc_title = QLabel("🖥️ 目标设备")
        rc_title.setFont(font_13_bold)
        rc_title.setStyleSheet(f"color: {TEXT_PRIMARY};")

        # 下拉与手动输入组合框
        self._host_combo = QComboBox()
        self._host_combo.setEditable(True)
        self._host_combo.setMinimumWidth(130)
        self._host_combo.activated.connect(self._on_host_selected_from_combo)
        if self._host_combo.lineEdit():
            self._host_combo.lineEdit().editingFinished.connect(self._on_host_editing_finished)

        # 删除当前 Host 按钮
        self._del_host_btn = QPushButton("✕")
        self._del_host_btn.setObjectName("del_host_btn")
        self._del_host_btn.setFixedSize(22, 22)
        self._del_host_btn.setToolTip("删除当前选中的 Host 记录")
        self._del_host_btn.clicked.connect(self._delete_current_host)

        host_layout = QHBoxLayout()
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(2)
        host_layout.addWidget(self._host_combo)
        host_layout.addWidget(self._del_host_btn)

        # 端口设置控件
        port_lbl = QLabel("端口:")
        port_lbl.setObjectName("subtitle")
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(22)
        self._port_spin.setFixedWidth(60)
        self._port_spin.editingFinished.connect(self._on_port_editing_finished)

        port_layout = QHBoxLayout()
        port_layout.setContentsMargins(0, 0, 0, 0)
        port_layout.setSpacing(4)
        port_layout.addWidget(port_lbl)
        port_layout.addWidget(self._port_spin)

        # 连通状态指示灯
        self._conn_status_lbl = QLabel("⚪ 未检测")
        font_12_bold = self._conn_status_lbl.font()
        font_12_bold.setPointSize(12)
        font_12_bold.setBold(True)
        self._conn_status_lbl.setFont(font_12_bold)
        self._conn_status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")

        self._test_conn_btn = QPushButton("测试连接")
        self._test_conn_btn.setObjectName("flat")
        self._test_conn_btn.setFixedHeight(26)
        self._test_conn_btn.clicked.connect(self._test_connection)

        rc_top.addWidget(rc_title)
        rc_top.addSpacing(4)
        rc_top.addLayout(host_layout)
        rc_top.addSpacing(6)
        rc_top.addLayout(port_layout)
        rc_top.addStretch()
        rc_top.addWidget(self._conn_status_lbl)
        rc_top.addSpacing(6)
        rc_top.addWidget(self._test_conn_btn)

        self._remote_info_lbl = QLabel("SSH: 未加载")
        self._remote_info_lbl.setObjectName("subtitle")

        self._remote_path_lbl = QLabel("远端根路径: 未配置")
        self._remote_path_lbl.setObjectName("subtitle")
        self._remote_path_lbl.setWordWrap(True)

        self._conn_err_detail_lbl = QLabel("")
        self._conn_err_detail_lbl.setStyleSheet(f"color: {DANGER_RED}; font-size: 12px; font-weight: 500;")
        self._conn_err_detail_lbl.setWordWrap(True)
        self._conn_err_detail_lbl.setVisible(False)

        rc_layout.addLayout(rc_top)
        rc_layout.addWidget(self._remote_info_lbl)
        rc_layout.addWidget(self._remote_path_lbl)
        rc_layout.addWidget(self._conn_err_detail_lbl)
        rc_layout.addStretch()

        devices_layout.addWidget(self._local_card, 1)
        devices_layout.addWidget(self._remote_card, 1)
        root.addLayout(devices_layout)

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

        log_label = QLabel("运行控制台日志")
        log_label.setObjectName("section")
        rv.addWidget(log_label)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        rv.addWidget(self._log)

        splitter.addWidget(right)
        splitter.setSizes([600, 320])

        # ── Bottom Action Buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("🔍  扫描并预览变动")
        self._scan_btn.setFixedHeight(40)
        self._scan_btn.clicked.connect(self._start_scan)

        self._exec_btn = QPushButton("✅  确认同步执行")
        self._exec_btn.setObjectName("success")
        self._exec_btn.setFixedHeight(40)
        self._exec_btn.setEnabled(False)
        self._exec_btn.clicked.connect(self._start_execute)

        btn_row.addStretch()
        btn_row.addWidget(self._scan_btn)
        btn_row.addSpacing(12)
        btn_row.addWidget(self._exec_btn)
        root.addLayout(btn_row)

    # ── Config ───────────────────────────────────────────────────────────────

    def _load_config(self):
        from duetflow import config as cfg_mod
        from duetflow.cli import ROOT as cli_root
        config_path = cli_root / "config.yaml"
        example_path = cli_root / "config.example.yaml"

        if not config_path.exists():
            if example_path.exists():
                import shutil
                shutil.copy(example_path, config_path)
            self._set_status(f"配置文件已生成: {config_path.name}", DANGER_RED)
            self._append_log(f"配置文件已自动生成，请编辑后重新运行: {config_path}")
            self._scan_btn.setEnabled(False)
            return

        try:
            self._cfg = cfg_mod.load()
            r = self._cfg["_resolved"]
            host = self._cfg["ssh"]["host"]

            # 设置 本机 IP 下拉选项（自动扫描并同步被选选定的 IP）
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

            # 设置 Host 下拉选项与端口 SpinBox
            hosts_list = r.get("hosts_list", [host])
            self._host_combo.blockSignals(True)
            self._host_combo.clear()
            for h in hosts_list:
                if h:
                    self._host_combo.addItem(h)
            self._host_combo.setEditText(host)
            self._host_combo.blockSignals(False)

            self._port_spin.blockSignals(True)
            self._port_spin.setValue(r.get("port", 22))
            self._port_spin.blockSignals(False)

            # 更新双端卡片 UI
            win_root = self._cfg["sync_paths"]["windows_root"]
            mac_root = self._cfg["sync_paths"]["mac_root"]
            is_win = sys.platform == "win32"
            local_path = win_root if is_win else mac_root
            remote_path = mac_root if is_win else win_root

            self._local_path_lbl.setText(f"本地根路径: {local_path}")
            self._remote_info_lbl.setText(f"SSH: {r['user']}@{r['host']}:{r['port']}")
            self._remote_path_lbl.setText(f"远端根路径: {remote_path}")

            self._append_log(f"配置文件加载成功，当前本机 IP: {r['local_ip']}")
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

    def _on_host_selected_from_combo(self, index):
        if index < 0 or not self._cfg:
            return
        host_text = self._host_combo.itemText(index).strip()
        self._apply_host_change(host_text)

    def _on_host_editing_finished(self):
        if not self._cfg:
            return
        host_text = self._host_combo.currentText().strip()
        self._apply_host_change(host_text)

    def _apply_host_change(self, host_text):
        if not host_text or not self._cfg:
            return
        curr = self._cfg.get("ssh", {}).get("host")
        if host_text != curr:
            self._cfg["ssh"]["host"] = host_text
            self._cfg["_resolved"]["host"] = host_text
            from duetflow import config as cfg_mod
            cfg_mod.save_host(host_text)
            self._remote_info_lbl.setText(f"SSH: {self._cfg['_resolved']['user']}@{host_text}:{self._cfg['_resolved']['port']}")
            self._append_log(f"已更新并保存目标 Host 为: {host_text}")

    def _on_port_editing_finished(self):
        if not self._cfg:
            return
        new_port = self._port_spin.value()
        curr_port = self._cfg.get("ssh", {}).get("port")
        if new_port != curr_port:
            self._cfg["ssh"]["port"] = new_port
            self._cfg["_resolved"]["port"] = new_port
            from duetflow import config as cfg_mod
            cfg_mod.save_port(new_port)
            host_text = self._cfg.get("_resolved", {}).get("host", "")
            self._remote_info_lbl.setText(f"SSH: {self._cfg['_resolved']['user']}@{host_text}:{new_port}")
            self._append_log(f"已更新并保存 SSH 端口号为: {new_port}")

    def _delete_current_host(self):
        if not self._cfg:
            return
        curr_text = self._host_combo.currentText().strip()
        idx = self._host_combo.currentIndex()
        if curr_text:
            from duetflow import config as cfg_mod
            cfg_mod.save_host(curr_text, remove=True)
            if idx >= 0:
                self._host_combo.removeItem(idx)
            self._append_log(f"已删除目标 Host 记录: {curr_text}")
            new_text = self._host_combo.currentText().strip()
            if new_text:
                self._apply_host_change(new_text)

    def _open_config(self):
        from duetflow.cli import ROOT as cli_root
        import os, subprocess
        config_path = str(cli_root / "config.yaml")
        if sys.platform == "win32":
            os.startfile(config_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", config_path])
        else:
            subprocess.run(["xdg-open", config_path])

    # ── Connection Test ──────────────────────────────────────────────────────

    def _test_connection(self):
        if not self._cfg:
            return
        self._conn_status_lbl.setText("🟡 检测中...")
        self._conn_status_lbl.setStyleSheet(f"color: {WARNING_YELLOW}; font-weight: bold;")
        self._test_conn_btn.setEnabled(False)

        r = self._cfg["_resolved"]
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
            self._conn_status_lbl.setText(f"🟢 在线 ({int(rtt)}ms)")
            self._conn_status_lbl.setStyleSheet(f"color: {SUCCESS_GREEN}; font-weight: bold;")
            self._conn_err_detail_lbl.setVisible(False)
            self._append_log(f"网络探针: 成功连接至远端主机 ({int(rtt)}ms)")
        else:
            self._conn_status_lbl.setText("🔴 无法连接")
            self._conn_status_lbl.setStyleSheet(f"color: {DANGER_RED}; font-weight: bold;")
            self._conn_err_detail_lbl.setText(f"⚠️ {msg}")
            self._conn_err_detail_lbl.setToolTip(msg)
            self._conn_err_detail_lbl.setVisible(True)
            self._append_log(f"网络探针: 连接异常 - {msg}")

    # ── Scan ─────────────────────────────────────────────────────────────────

    def _start_scan(self):
        if not self._cfg:
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
        if not self._plan or not self._worker_obj:
            return
        active = [a for a in self._plan if a["action"] != "SKIP"]
        if not active:
            return

        self._set_busy(True)
        self._exec_btn.setEnabled(False)
        self._append_log("─" * 45)
        self._append_log("确认无误，开始执行同步文件传输与隔离...")

        worker = self._worker_obj
        worker.approved_plan = active
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.execute_plan)
        worker.log.connect(self._append_log)
        worker.done.connect(lambda ok, msg: self._on_done(ok, msg, thread))
        thread.start()
        self._thread = thread

    def _on_done(self, ok, msg, thread):
        thread.quit()
        thread.wait()
        self._set_busy(False)
        if ok:
            self._set_status("同步完成", SUCCESS_GREEN)
            self._exec_btn.setEnabled(False)
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
        self._scan_btn.setText("正在扫描计算中..." if busy else "🔍  扫描并预览变动")


# ─── 入口 ─────────────────────────────────────────────────────────────────────

def main():
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

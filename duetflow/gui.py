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
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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

# ─── 中性浅色调色板 ───────────────────────────────────────────────────────────

LIGHT_BG = "#f3f3f3"          # 全局背景
CARD_BG = "#ffffff"           # 卡片背景
BORDER_COLOR = "#d0d0d0"      # 边框
TEXT_PRIMARY = "#222222"      # 主文字
TEXT_SECONDARY = "#666666"    # 次要文字
ACCENT_BLUE = "#005a9e"       # 强调蓝
SUCCESS_GREEN = "#217346"     # 成功绿
WARNING_YELLOW = "#c78000"    # 警告橙
DANGER_RED = "#c42b1c"        # 危险红
TABLE_ALT_BG = "#f7f7f7"      # 表格交替行

MAX_CONNECTIONS = 5

QSS = f"""
QWidget {{
    background-color: {LIGHT_BG};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}}

QFrame#card {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
}}

QComboBox, QLineEdit {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    padding: 5px 8px;
    font-size: 13px;
}}
QComboBox:hover, QLineEdit:hover {{
    border-color: {ACCENT_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}

QPushButton {{
    background-color: {ACCENT_BLUE};
    color: white;
    border: 1px solid {ACCENT_BLUE};
    border-radius: 3px;
    padding: 6px 14px;
    font-weight: normal;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #004a85;
    border-color: #004a85;
}}
QPushButton:pressed {{
    background-color: #003a6a;
}}
QPushButton:disabled {{
    background-color: #e0e0e0;
    border-color: #d0d0d0;
    color: {TEXT_SECONDARY};
}}

QPushButton#danger {{
    background-color: {DANGER_RED};
    border-color: {DANGER_RED};
}}
QPushButton#danger:hover {{
    background-color: #a32012;
}}

QPushButton#success {{
    background-color: {SUCCESS_GREEN};
    border-color: {SUCCESS_GREEN};
}}
QPushButton#success:hover {{
    background-color: #1a5f39;
}}

QPushButton#flat {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    font-weight: normal;
    font-size: 13px;
    padding: 5px 10px;
}}
QPushButton#flat:hover {{
    background-color: #f0f0f0;
    border-color: #b0b0b0;
}}

QPushButton#add_tab {{
    background-color: transparent;
    color: {ACCENT_BLUE};
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    font-size: 14px;
    font-weight: normal;
    padding: 2px 10px;
    min-height: 22px;
}}
QPushButton#add_tab:hover {{
    background-color: #f0f0f0;
    border-color: {ACCENT_BLUE};
}}

QPushButton#browse_key {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 3px;
    font-weight: normal;
    font-size: 13px;
    padding: 5px 10px;
}}
QPushButton#browse_key:hover {{
    background-color: #f0f0f0;
}}

QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 12px;
    margin-right: 2px;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background-color: {CARD_BG};
    border-bottom: 2px solid {ACCENT_BLUE};
    color: {ACCENT_BLUE};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background-color: #f0f0f0;
}}
QTabBar::close-button {{
    image: none;
    subcontrol-position: right;
    padding: 2px;
}}
QTabBar::close-button:hover {{
    background: rgba(196, 43, 28, 0.12);
    border-radius: 3px;
}}

QTableWidget {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    gridline-color: #eeeeee;
    selection-background-color: #d6e8f7;
    selection-color: {TEXT_PRIMARY};
    alternate-background-color: {TABLE_ALT_BG};
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
}}
QHeaderView::section {{
    background-color: #e8e8e8;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-weight: bold;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {BORDER_COLOR};
}}

QTextEdit {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    padding: 8px;
    font-family: Consolas, monospace;
    font-size: 12px;
    color: {TEXT_PRIMARY};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #c0c0c0;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #909090;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QSplitter::handle {{
    background: {BORDER_COLOR};
    width: 1px;
}}

QLabel#title {{
    font-size: 16px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QLabel#subtitle {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}
QLabel#section {{
    font-size: 12px;
    font-weight: bold;
    color: {TEXT_SECONDARY};
}}
"""

ACTION_META = {
    "WIN_TO_MAC":    ("Win -> Mac",   ACCENT_BLUE),
    "MAC_TO_WIN":    ("Mac -> Win",   SUCCESS_GREEN),
    "QUARANTINE_WIN": ("隔离 Win",    WARNING_YELLOW),
    "QUARANTINE_MAC": ("隔离 Mac",    WARNING_YELLOW),
    "CONFLICT":      ("冲突",         DANGER_RED),
    "SKIP":          ("跳过",         TEXT_SECONDARY),
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
                    self.log.emit(f"上传 {path}")
                    sftp.upload(self._sftp, local_full, remote_full)
                elif action == to_local_action:
                    self.log.emit(f"下载 {path}")
                    sftp.download(self._sftp, remote_full, local_full)
                elif action == quarantine_local_action:
                    self.log.emit(f"隔离本地: {path}")
                    trash.quarantine_local(path, local_root)
                elif action == quarantine_remote_action:
                    self.log.emit(f"隔离远端: {path}")
                    remote_trash = str(PurePosixPath(remote_root).parent / ".sync_trash")
                    sftp.remote_quarantine(self._ssh, remote_full, remote_trash)
                elif action == "CONFLICT":
                    reason = item.get("reason", "")
                    if reason == "modified_vs_deleted":
                        self.log.emit(f"冲突(改/删) 跳过: {path}")
                    else:
                        conflict_name = item["conflict_name"]
                        local_conflict = local_full.parent / Path(conflict_name).name
                        if local_full.exists():
                            _shutil.copy2(str(local_full), str(local_conflict))
                        sftp.download(
                            self._sftp, remote_full,
                            local_conflict.parent / f"_remote_{Path(conflict_name).name}"
                        )
                        self.log.emit(f"冲突保留: {conflict_name}")

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
        self._scan_btn = QPushButton("扫描并预览变动")
        self._scan_btn.setFixedHeight(32)
        self._scan_btn.clicked.connect(self._start_scan)

        self._exec_btn = QPushButton("确认同步执行")
        self._exec_btn.setObjectName("success")
        self._exec_btn.setFixedHeight(32)
        self._exec_btn.setEnabled(False)
        self._exec_btn.clicked.connect(self._start_execute)

        btn_row.addStretch()
        btn_row.addWidget(self._scan_btn)
        btn_row.addSpacing(12)
        btn_row.addWidget(self._exec_btn)
        root.addLayout(btn_row)

    def _build_connection_bar(self, parent_layout):
        """构建选项卡栏：QTabBar + "+" 新增按钮。"""
        bar_row = QHBoxLayout()
        bar_row.setSpacing(4)
        bar_row.setContentsMargins(0, 0, 0, 0)

        bar_label = QLabel("连接")
        bar_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT_SECONDARY}; margin-right: 6px;")
        bar_row.addWidget(bar_label)

        self._tab_bar = QTabBar()
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._tab_bar.tabCloseRequested.connect(self._close_tab)
        # 自定义关闭按钮文本
        for i in range(self._tab_bar.count()):
            tab_btn = self._tab_bar.tabButton(i, QTabBar.RightSide)
            if tab_btn:
                tab_btn.setText("✕")
        bar_row.addWidget(self._tab_bar, 1)

        self._add_tab_btn = QPushButton("+")
        self._add_tab_btn.setObjectName("add_tab")
        self._add_tab_btn.setFixedSize(32, 28)
        self._add_tab_btn.setToolTip("新增连接")
        self._add_tab_btn.clicked.connect(self._add_new_tab)
        bar_row.addWidget(self._add_tab_btn)

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
        """构建路径信息行。"""
        path_row = QHBoxLayout()
        path_row.setSpacing(24)

        self._local_path_lbl = QLabel("本地根路径: 未配置")
        self._local_path_lbl.setObjectName("subtitle")
        path_row.addWidget(self._local_path_lbl)

        self._remote_path_lbl = QLabel("远端根路径: 未配置")
        self._remote_path_lbl.setObjectName("subtitle")
        path_row.addWidget(self._remote_path_lbl)

        path_row.addStretch()
        parent_layout.addLayout(path_row)

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
        """输入字段变更时，实时同步到当前选项卡数据。"""
        if self._tab_updating:
            return
        if self._current_idx < 0 or self._current_idx >= len(self._connections):
            return
        conn = self._connections[self._current_idx]
        conn["host"] = self._host_edit.text().strip()
        conn["port"] = self._port_number()
        conn["user"] = self._user_edit.text().strip()
        conn["key_path"] = self._key_edit.text().strip()
        # 更新选项卡标签
        label = conn["host"] or "新连接"
        self._tab_bar.setTabText(self._current_idx, label)
        # 重置连接状态
        self._conn_status_lbl.setText("未检测")
        self._conn_status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._conn_err_detail_lbl.setVisible(False)

    def _add_new_tab(self):
        """新增一个空白连接选项卡。"""
        if len(self._connections) >= MAX_CONNECTIONS:
            QMessageBox.information(self, "提示", f"最多保留 {MAX_CONNECTIONS} 个连接记录")
            return

        new_conn = {"host": "", "port": 22, "user": "", "key_path": ""}
        self._connections.append(new_conn)

        self._tab_updating = True
        idx = self._tab_bar.addTab("新连接")
        self._tab_updating = False

        self._tab_bar.setCurrentIndex(idx)
        self._current_idx = idx
        self._fill_fields_from_conn(new_conn)

        # 聚焦到 Host 输入框
        self._host_edit.setFocus()
        self._host_edit.selectAll()

        self._save_connections_to_disk()

    def _close_tab(self, index):
        """关闭指定选项卡。"""
        if len(self._connections) <= 1:
            QMessageBox.information(self, "提示", "至少保留一个连接")
            return
        if index < 0 or index >= len(self._connections):
            return

        # 移除数据
        self._connections.pop(index)
        self._tab_updating = True
        self._tab_bar.removeTab(index)
        self._tab_updating = False

        # 切换选中
        new_count = self._tab_bar.count()
        if new_count > 0:
            new_idx = min(index, new_count - 1)
            self._tab_bar.setCurrentIndex(new_idx)
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
        save_connections(self._connections, self._tab_bar.currentIndex())

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

    def _update_resolved_from_fields(self):
        """从当前输入字段 + self._cfg 的静态配置，构建 _resolved。"""
        if not self._cfg:
            return

        host = self._host_edit.text().strip()
        port = self._port_number()
        user = self._user_edit.text().strip()
        key_path = self._key_edit.text().strip()

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
            win_root = self._cfg["sync_paths"]["windows_root"]
            mac_root = self._cfg["sync_paths"]["mac_root"]
            is_win = sys.platform == "win32"
            local_path = win_root if is_win else mac_root
            remote_path = mac_root if is_win else win_root
            self._local_path_lbl.setText(f"本地根路径: {local_path}")
            self._remote_path_lbl.setText(f"远端根路径: {remote_path}")

            # 加载连接历史
            connections, last_idx = cfg_mod.load_connections()

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

            # 填充选项卡
            self._tab_updating = True
            self._tab_bar.clear()
            for conn in connections:
                label = conn.get("host", "") or "新连接"
                self._tab_bar.addTab(label)
            self._tab_updating = False

            # 选中上次使用的选项卡
            if connections:
                safe_idx = max(0, min(last_idx, len(connections) - 1))
                self._tab_bar.setCurrentIndex(safe_idx)
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
                    self._tab_bar.setTabText(self._current_idx, host or "新连接")
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
        self._scan_btn.setText("正在扫描计算中..." if busy else "扫描并预览变动")


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

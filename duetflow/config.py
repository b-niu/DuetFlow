"""读取 config.json5，缺失则自动迁移旧 config.yaml 或从 config.example.json5 复制。

配置体系（文件分工）:
  - config.json5      — 人类编辑的配置（JSON5 格式，支持注释）
  - connections.json  — 连接历史（程序自动保存，纯 JSON）
  - state.json        — 运行时状态（如本机 IP，纯 JSON）
  - baseline.json.gz  — 同步基线快照（gzip 压缩 JSON，详见 cli.py）
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json5"
EXAMPLE_PATH = ROOT / "config.example.json5"
OLD_YAML_PATH = ROOT / "config.yaml"
STATE_PATH = ROOT / "state.json"
CONNECTIONS_PATH = ROOT / "connections.json"


# ─── 本机 IP 扫描 ─────────────────────────────────────────────────────────────


def scan_local_ips():
    """自动扫描本机的网络接口与 IPv4 地址。
    返回: list[dict] -> [{"name": "以太网", "ip": "192.168.1.100", "label": "以太网 (192.168.1.100)"}, ...]
    """
    import socket
    interfaces = []
    seen_ips = set()

    # 1. 尝试通过 PySide6 QNetworkInterface 获取带有网卡名称的 IP 列表
    try:
        from PySide6.QtNetwork import QNetworkInterface, QAbstractSocket

        for iface in QNetworkInterface.allInterfaces():
            flags = iface.flags()
            if not (flags & QNetworkInterface.IsUp) or (flags & QNetworkInterface.IsLoopBack):
                continue
            name = iface.humanReadableName()
            for entry in iface.addressEntries():
                ip = entry.ip()
                if ip.protocol() == QAbstractSocket.IPv4Protocol:
                    ip_str = ip.toString()
                    if not ip_str.startswith("127.") and ip_str not in seen_ips:
                        seen_ips.add(ip_str)
                        interfaces.append({
                            "name": name,
                            "ip": ip_str,
                            "label": f"{name} ({ip_str})" if name else ip_str,
                        })
    except ImportError:
        pass

    # 2. 标准库 socket 兜底
    try:
        hostname = socket.gethostname()
        for ip_str in socket.gethostbyname_ex(hostname)[2]:
            if not ip_str.startswith("127.") and ip_str not in seen_ips:
                seen_ips.add(ip_str)
                interfaces.append({
                    "name": "网络适配器",
                    "ip": ip_str,
                    "label": f"网络适配器 ({ip_str})",
                })
    except Exception:
        pass

    # 3. 通过连接探测出口主 IP
    primary_ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    if primary_ip and not primary_ip.startswith("127."):
        if primary_ip not in seen_ips:
            seen_ips.add(primary_ip)
            interfaces.append({
                "name": "默认网卡",
                "ip": primary_ip,
                "label": f"默认网卡 ({primary_ip})",
            })

    # 排序：主出口 IP 排第 1，普通局域网 IP 排第 2，APIPA (169.254.x.x) 排第 3
    def sort_key(item):
        ip = item["ip"]
        if ip == primary_ip:
            return 0
        if ip.startswith("169.254."):
            return 2
        return 1

    interfaces.sort(key=sort_key)

    if not interfaces:
        interfaces = [{
            "name": "Loopback",
            "ip": "127.0.0.1",
            "label": "回环地址 (127.0.0.1)",
        }]

    return interfaces


# ─── 运行时状态 (state.json) ──────────────────────────────────────────────────


def _read_state():
    """读取 state.json，不存在返回空 dict。"""
    if not STATE_PATH.exists():
        return {}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_state(data: dict):
    """写入 state.json。"""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_local_ip(ip_address: str):
    """保存选定的本机 IP 到 state.json。"""
    state = _read_state()
    state["local_ip"] = ip_address
    _write_state(state)


# ─── 连接历史 (connections.json) ──────────────────────────────────────────────


def load_connections():
    """读取连接历史。
    返回: (connections: list[dict], last_index: int)
    """
    if not CONNECTIONS_PATH.exists():
        return [], 0
    try:
        with open(CONNECTIONS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        connections = data.get("connections", [])
        if not isinstance(connections, list):
            connections = []
        last_index = data.get("last_index", 0)
        return connections, last_index
    except Exception:
        return [], 0


def save_connections(connections: list, last_index: int = 0):
    """保存连接历史到 connections.json。"""
    CONNECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONNECTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"connections": connections, "last_index": last_index},
                f, indent=2, ensure_ascii=False,
            )
    except Exception as e:
        print(f"[DuetFlow] 保存 connections 失败: {e}")


# ─── 主配置加载 ───────────────────────────────────────────────────────────────


def _migrate_from_yaml():
    """将旧 config.yaml 迁移为 config.json5 + connections.json + state.json。"""
    import yaml

    with open(OLD_YAML_PATH, encoding="utf-8") as f:
        old = yaml.safe_load(f)

    # 提取 SSH 连接 → connections.json
    ssh = old.get("ssh", {})
    host = ssh.get("host", "")
    port = ssh.get("port", 22)
    user = ssh.get("user", "")
    key_path = ssh.get("key_path", "")

    connections = []
    if host:
        connections.append({
            "host": host,
            "port": port,
            "user": user,
            "key_path": key_path,
        })
    # 旧 host_history 也转为连接
    for h in old.get("host_history", []):
        if h and h != host and not any(c["host"] == h for c in connections):
            connections.append({"host": h, "port": port, "user": user, "key_path": key_path})

    if connections:
        save_connections(connections, 0)

    # 写入 config.json5（标准 JSON 即是合法 JSON5，且 json.dump 支持缩进）
    import json
    new_cfg = {
        "sync_paths": old.get("sync_paths", {}),
        "exclude": old.get("exclude", []),
        "text_extensions": old.get("text_extensions", []),
        "safety": old.get("safety", {}),
        "baseline": old.get("baseline", {}),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(new_cfg, f, indent=2)

    # 写入 local_ip → state.json
    local_ip = old.get("local_ip", "")
    if local_ip:
        save_local_ip(local_ip)

    print(f"[DuetFlow] 已从 {OLD_YAML_PATH.name} 迁移到 {CONFIG_PATH.name} + connections.json + state.json")

    # 重命名旧 yaml 以防混淆
    OLD_YAML_PATH.rename(OLD_YAML_PATH.with_suffix(".yaml.bak"))


def load():
    """加载配置。

    优先级:
      1. config.json5 (JSON5 格式，支持注释)
      2. 如不存在，尝试从 config.yaml 迁移
      3. 如 yaml 也不存在，从 config.example.json5 复制

    返回: dict，含 _resolved 计算字段
    """
    if not CONFIG_PATH.exists():
        if OLD_YAML_PATH.exists():
            # 一步迁移旧的 yaml 配置
            _migrate_from_yaml()
        elif EXAMPLE_PATH.exists():
            shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
            print(f"[DuetFlow] 配置文件已生成: {CONFIG_PATH}")
            print("[DuetFlow] 请编辑 config.json5 后重新运行。")
            raise SystemExit(0)
        else:
            print(f"[DuetFlow] 缺少配置，请创建 {CONFIG_PATH}")
            raise SystemExit(1)

    import pyjson5

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = pyjson5.load(f)

    # 自动扫描本机网卡与 IP
    scanned_ips = scan_local_ips()
    state = _read_state()
    saved_ip = state.get("local_ip")
    scanned_ip_list = [item["ip"] for item in scanned_ips]

    if saved_ip and saved_ip in scanned_ip_list:
        active_local_ip = saved_ip
    else:
        active_local_ip = scanned_ips[0]["ip"]
        if saved_ip != active_local_ip:
            save_local_ip(active_local_ip)

    # 自动识别 local_root 和 remote_root
    import sys
    is_win = sys.platform == "win32"
    win_root = cfg["sync_paths"]["windows_root"]
    mac_root = cfg["sync_paths"]["mac_root"]

    local_root = win_root if is_win else mac_root
    remote_root = mac_root if is_win else win_root

    cfg["_resolved"] = {
        "local_root": local_root,
        "remote_root": remote_root,
        "is_win": is_win,
        "local_ip": active_local_ip,
        "scanned_ips": scanned_ips,
    }
    return cfg

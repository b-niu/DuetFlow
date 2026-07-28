"""读取 config.yaml，缺失则自动从 config.example.yaml 复制并提示。支持 ~/.ssh/config 别名解析。"""

import os
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
EXAMPLE_PATH = ROOT / "config.example.yaml"


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
                            "label": f"{name} ({ip_str})" if name else ip_str
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
                    "label": f"网络适配器 ({ip_str})"
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
                "label": f"默认网卡 ({primary_ip})"
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
            "label": "回环地址 (127.0.0.1)"
        }]

    return interfaces


def save_local_ip(ip_address: str):
    """将选定的本机 IP 保存到 config.yaml。"""
    if not CONFIG_PATH.exists():
        return
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        cfg["local_ip"] = ip_address
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"[DuetFlow] 保存 local_ip 失败: {e}")


def save_host(host_str: str, remove: bool = False):
    """保存或从历史中删除目标 SSH Host 到 config.yaml。"""
    if not CONFIG_PATH.exists():
        return
    host_str = host_str.strip()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        if "ssh" not in cfg:
            cfg["ssh"] = {}

        history = cfg.get("host_history", [])
        if not isinstance(history, list):
            history = []

        if not remove and host_str:
            if host_str not in history:
                history.append(host_str)
            cfg["ssh"]["host"] = host_str
        elif remove and host_str:
            if host_str in history:
                history.remove(host_str)
            if cfg["ssh"].get("host") == host_str:
                cfg["ssh"]["host"] = history[0] if history else ""

        cfg["host_history"] = history
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"[DuetFlow] 保存 host 失败: {e}")


def save_port(port_val: int):
    """保存 SSH 端口号到 config.yaml。"""
    if not CONFIG_PATH.exists():
        return
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        if "ssh" not in cfg:
            cfg["ssh"] = {}
        cfg["ssh"]["port"] = int(port_val)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"[DuetFlow] 保存 port 失败: {e}")


def load():
    if not CONFIG_PATH.exists():
        if EXAMPLE_PATH.exists():
            shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
        print(f"[DuetFlow] 配置文件已生成: {CONFIG_PATH}")
        print("[DuetFlow] 请编辑 config.yaml 后重新运行。")
        raise SystemExit(0)

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 自动扫描本机网卡与 IP
    scanned_ips = scan_local_ips()
    saved_ip = cfg.get("local_ip")
    scanned_ip_list = [item["ip"] for item in scanned_ips]

    if saved_ip and saved_ip in scanned_ip_list:
        active_local_ip = saved_ip
    else:
        active_local_ip = scanned_ips[0]["ip"]
        if saved_ip != active_local_ip:
            save_local_ip(active_local_ip)

    # 解析 ~/.ssh/config 别名及 Host 列表
    host_str = cfg["ssh"]["host"]
    ssh_cfg_path = Path.home() / ".ssh" / "config"
    resolved_host = host_str
    resolved_port = cfg["ssh"].get("port", 22)
    resolved_user = cfg["ssh"].get("user", "")
    resolved_key = cfg["ssh"].get("key_path", None)

    hosts_list = []
    if host_str:
        hosts_list.append(host_str)

    for h in cfg.get("host_history", []):
        if h and h not in hosts_list:
            hosts_list.append(h)

    if ssh_cfg_path.exists():
        try:
            import paramiko

            ssh_config = paramiko.SSHConfig()
            with open(ssh_cfg_path) as scf:
                ssh_config.parse(scf)

            for host_name in ssh_config.get_hostnames():
                if host_name and "*" not in host_name and host_name not in hosts_list:
                    hosts_list.append(host_name)

            lookup = ssh_config.lookup(host_str)
            resolved_host = lookup.get("hostname", host_str)
            resolved_port = int(lookup.get("port", resolved_port))
            resolved_user = lookup.get("user", resolved_user)
            id_files = lookup.get("identityfile", [])
            if id_files and not resolved_key:
                resolved_key = id_files[0]
        except Exception:
            pass

    # 默认密钥
    if not resolved_key:
        for name in ("id_rsa", "id_ed25519", "id_ecdsa"):
            p = Path.home() / ".ssh" / name
            if p.exists():
                resolved_key = str(p)
                break

    # 自动识别 local_root 和 remote_root
    import sys
    is_win = sys.platform == "win32"
    win_root = cfg["sync_paths"]["windows_root"]
    mac_root = cfg["sync_paths"]["mac_root"]

    local_root = win_root if is_win else mac_root
    remote_root = mac_root if is_win else win_root

    cfg["_resolved"] = {
        "host": resolved_host,
        "port": resolved_port,
        "user": resolved_user,
        "key_path": resolved_key,
        "local_root": local_root,
        "remote_root": remote_root,
        "is_win": is_win,
        "local_ip": active_local_ip,
        "scanned_ips": scanned_ips,
        "hosts_list": hosts_list,
    }
    return cfg


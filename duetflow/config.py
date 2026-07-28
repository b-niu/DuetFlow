"""读取 config.yaml，缺失则自动从 config.example.yaml 复制并提示。支持 ~/.ssh/config 别名解析。"""

import os
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
EXAMPLE_PATH = ROOT / "config.example.yaml"


def load():
    if not CONFIG_PATH.exists():
        if EXAMPLE_PATH.exists():
            shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
        print(f"[DuetFlow] 配置文件已生成: {CONFIG_PATH}")
        print("[DuetFlow] 请编辑 config.yaml 后重新运行。")
        raise SystemExit(0)

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 解析 ~/.ssh/config 别名
    host_str = cfg["ssh"]["host"]
    ssh_cfg_path = Path.home() / ".ssh" / "config"
    resolved_host = host_str
    resolved_port = cfg["ssh"].get("port", 22)
    resolved_user = cfg["ssh"].get("user", "")
    resolved_key = cfg["ssh"].get("key_path", None)

    if ssh_cfg_path.exists():
        try:
            import paramiko

            ssh_config = paramiko.SSHConfig()
            with open(ssh_cfg_path) as scf:
                ssh_config.parse(scf)
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
    }
    return cfg

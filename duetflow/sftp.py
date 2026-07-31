"""SFTP 传输层。封装 paramiko 的连接、上传、下载、远端隔离、远端扫描。"""

import io
import json
import os
import textwrap
from pathlib import Path, PurePosixPath

import paramiko


def connect(resolved):
    """建立 SSH 连接，返回 (ssh_client, sftp_client)"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": resolved["host"],
        "port": resolved["port"],
        "username": resolved["user"],
        "timeout": 8,           # TCP 连接超时
        "banner_timeout": 8,    # SSH banner 协商超时
        "auth_timeout": 8,      # 认证超时
    }
    if resolved.get("key_path"):
        connect_kwargs["key_filename"] = str(Path(resolved["key_path"]).expanduser())
    ssh.connect(**connect_kwargs)
    sftp = ssh.open_sftp()
    return ssh, sftp


def remote_scan(ssh, mac_root, exclude_patterns, text_extensions):
    """在 Mac 端执行 scanner.py 并返回 manifest dict。
    通过 SSH 把 scanner 脚本内容 heredoc 进去执行，避免依赖远端安装。
    """
    # 生成内联脚本
    script_path = Path(__file__).parent / "scanner.py"
    scanner_src = script_path.read_text(encoding="utf-8")

    call_code = f"""
import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')
exclude = {json.dumps(exclude_patterns)}
text_ext = {json.dumps(text_extensions)}
mac_root = os.path.expanduser({json.dumps(mac_root)})
result = scan(mac_root, exclude, text_ext)
print(json.dumps(result))
"""
    full_script = scanner_src + "\n" + textwrap.dedent(call_code)

    # 兼容 macOS：优先 python3，找不到则回退 python
    which_line = "PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null); "
    stdin, stdout, stderr = ssh.exec_command(which_line + "$PYBIN -c " + _quote(full_script))
    out = stdout.read().decode("utf-8").strip()
    err = stderr.read().decode("utf-8").strip()
    if err:
        print(f"[remote_scan stderr] {err}")
    if not out:
        return {}
    return json.loads(out)


def _quote(s):
    """对 shell 命令参数做简单 single-quote 转义"""
    return "'" + s.replace("'", "'\\''") + "'"


def upload(sftp, local_path, remote_path):
    """上传本地文件到 Mac"""
    _sftp_makedirs(sftp, str(PurePosixPath(remote_path).parent))
    sftp.put(str(local_path), remote_path)


def download(sftp, remote_path, local_path):
    """从 Mac 下载文件到本地"""
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    sftp.get(remote_path, str(local_path))


def remote_quarantine(ssh, remote_path, remote_trash_root):
    """将 Mac 端文件移入远端隔离区"""
    from datetime import datetime

    date_dir = datetime.now().strftime("%Y%m%d")
    dest = f"{remote_trash_root}/{date_dir}/{PurePosixPath(remote_path).name}"
    ssh.exec_command(f"mkdir -p {_quote(f'{remote_trash_root}/{date_dir}')} && mv {_quote(remote_path)} {_quote(dest)}")


def _sftp_makedirs(sftp, remote_dir):
    """递归创建远端目录"""
    parts = PurePosixPath(remote_dir).parts
    cur = ""
    for part in parts:
        cur = str(PurePosixPath(cur) / part) if cur else part
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            try:
                sftp.mkdir(cur)
            except Exception:
                pass

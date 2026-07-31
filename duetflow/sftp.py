"""SFTP 传输层。封装 paramiko 的连接、上传、下载、远端隔离、远端扫描。"""

import base64
import gzip
import json
import stat as _stat
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


def remote_scan(ssh, mac_root, exclude_patterns, text_extensions, prev_manifest=None, mac_app_dir="/Users/bing/MyGithub/DuetFlow"):
    """在 Mac 端直接运行其部署的 DuetFlow 扫描模块并返回 manifest dict。

    通过 SSH 在 mac_app_dir 目录下直接执行：
      uv run python -m duetflow.cli_scan
    并通过 stdin 传入控制 JSON。
    """
    prev_b64 = ""
    if prev_manifest:
        gz_bytes = gzip.compress(
            json.dumps(prev_manifest, ensure_ascii=False).encode("utf-8"),
            compresslevel=6,
        )
        prev_b64 = base64.b64encode(gz_bytes).decode("ascii")

    req_payload = {
        "root": mac_root,
        "exclude": exclude_patterns,
        "text_extensions": text_extensions,
        "prev_manifest_b64": prev_b64,
    }

    # 优先检测 uv 路径并在 mac_app_dir 下运行 cli_scan
    cmd = (
        "sh -c '"
        f"cd {_quote(mac_app_dir)} && "
        "UVBIN=$(command -v ~/.local/bin/uv 2>/dev/null || command -v ~/.cargo/bin/uv 2>/dev/null || command -v uv 2>/dev/null); "
        "if [ -z \"$UVBIN\" ]; then "
        "  echo \"ERROR: 未在 Mac 上找到 uv！请在 Mac 上安装 uv。\" >&2; exit 1; "
        "fi; "
        "$UVBIN run python -m duetflow.cli_scan'"
    )

    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.settimeout(300)

    stdin.write(json.dumps(req_payload, ensure_ascii=False).encode("utf-8"))
    stdin.flush()
    stdin.channel.shutdown_write()

    out = stdout.read().decode("utf-8").strip()
    err = stderr.read().decode("utf-8").strip()
    if err:
        print(f"[remote_scan stderr]\n{err}")
    if not out:
        return {}
    return json.loads(out)


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
    cmd = f"mkdir -p {_quote(f'{remote_trash_root}/{date_dir}')} && mv {_quote(remote_path)} {_quote(dest)}"
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode("utf-8").strip()
        raise OSError(f"remote_quarantine 失败 (exit {exit_status}): {err}")


def _quote(s):
    """对 shell 命令参数做 single-quote 转义"""
    return "'" + s.replace("'", "'\\''") + "'"


def _sftp_makedirs(sftp, remote_dir):
    """递归创建远端目录"""
    parts = PurePosixPath(remote_dir).parts
    cur = ""
    for part in parts:
        cur = str(PurePosixPath(cur) / part) if cur else part
        try:
            sftp.mkdir(cur)
        except OSError:
            try:
                st = sftp.stat(cur)
                if not _stat.S_ISDIR(st.st_mode):
                    raise OSError(f"远端路径已存在但不是目录: {cur}")
            except FileNotFoundError:
                raise OSError(f"无法创建远端目录: {cur}")

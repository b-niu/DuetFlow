"""SFTP 传输层。封装 paramiko 的连接、上传、下载、远端隔离、远端扫描。"""

import base64
import gzip
import json
import os
import stat as _stat
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


def remote_scan(ssh, mac_root, exclude_patterns, text_extensions, prev_manifest=None):
    """在 Mac 端执行 scanner.py 并返回 manifest dict。

    改进点（相比原版）：
      1. 通过 SSH stdin pipe 传输脚本，彻底规避 shell ARG_MAX 长度限制和
         特殊字符转义风险（原版用 python -c '...' 参数，有 ~2MB 上限）。
      2. 支持 prev_manifest：将 baseline 压缩后嵌入脚本变量，让 Mac 端
         扫描也能享受 mtime 缓存加速（同 Windows 端策略，典型提速 80%+）。
      3. 设置 5 分钟超时，避免远端进程异常时永久阻塞。
    """
    script_path = Path(__file__).parent / "scanner.py"
    scanner_src = script_path.read_text(encoding="utf-8")

    # 将 prev_manifest 压缩+Base64 编码后嵌入脚本（绕开命令行长度限制）
    if prev_manifest:
        gz_bytes = gzip.compress(
            json.dumps(prev_manifest, ensure_ascii=False).encode("utf-8"),
            compresslevel=6,
        )
        prev_b64 = base64.b64encode(gz_bytes).decode("ascii")
    else:
        prev_b64 = ""

    call_code = f"""
import json, sys, os, gzip, base64
sys.stdout.reconfigure(encoding='utf-8')
exclude   = {json.dumps(exclude_patterns)}
text_ext  = {json.dumps(text_extensions)}
mac_root  = os.path.expanduser({json.dumps(mac_root)})
_prev_b64 = {json.dumps(prev_b64)}
prev_manifest = (
    json.loads(gzip.decompress(base64.b64decode(_prev_b64)))
    if _prev_b64 else None
)
result = scan(mac_root, exclude, text_ext, prev_manifest=prev_manifest)
print(json.dumps(result, ensure_ascii=False))
"""
    full_script = scanner_src + "\n" + textwrap.dedent(call_code)

    # 通过 stdin pipe 发送脚本（无大小限制，无需 shell 转义）
    # 兼容 macOS：优先 python3，回退 python
    cmd = "sh -c 'PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null) && $PYBIN -'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.settimeout(300)  # 最长等待 5 分钟

    stdin.write(full_script.encode("utf-8"))
    stdin.flush()
    stdin.channel.shutdown_write()  # 发送 EOF，让远端 python - 开始执行

    out = stdout.read().decode("utf-8").strip()
    err = stderr.read().decode("utf-8").strip()
    if err:
        print(f"[remote_scan stderr] {err}")
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
    """将 Mac 端文件移入远端隔离区，并检查执行结果。"""
    from datetime import datetime

    date_dir = datetime.now().strftime("%Y%m%d")
    dest = f"{remote_trash_root}/{date_dir}/{PurePosixPath(remote_path).name}"
    cmd = (
        f"mkdir -p {_quote(f'{remote_trash_root}/{date_dir}')}"
        f" && mv {_quote(remote_path)} {_quote(dest)}"
    )
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode("utf-8").strip()
        raise OSError(f"remote_quarantine 失败 (exit {exit_status}): {err}")


def _quote(s):
    """对 shell 命令参数做 single-quote 转义（POSIX 标准）"""
    return "'" + s.replace("'", "'\\''") + "'"


def _sftp_makedirs(sftp, remote_dir):
    """递归创建远端目录。

    采用 mkdir-first 策略（EAFP）：直接尝试创建，失败后再用 stat 确认是否
    "已存在"。相比原先的 stat-then-mkdir，减少约一半的网络往返次数。
    """
    parts = PurePosixPath(remote_dir).parts
    cur = ""
    for part in parts:
        cur = str(PurePosixPath(cur) / part) if cur else part
        try:
            sftp.mkdir(cur)
        except OSError:
            # 可能是"已存在"也可能是真实错误，用 stat 确认
            try:
                st = sftp.stat(cur)
                if not _stat.S_ISDIR(st.st_mode):
                    raise OSError(f"远端路径已存在但不是目录: {cur}")
                # 目录确实存在，继续下一级
            except FileNotFoundError:
                raise OSError(f"无法创建远端目录: {cur}")

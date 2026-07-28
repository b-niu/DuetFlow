"""本地目录扫描器。生成文件清单 {相对路径: {size, mtime, hash, is_text}}。"""

import fnmatch
import os
from pathlib import Path

import xxhash

WIN_ILLEGAL = set('\\:*?"<>|')


def _is_excluded(rel_path, exclude_patterns):
    # 统一用 posix 风格比对
    p = rel_path.replace("\\", "/")
    for pattern in exclude_patterns:
        pat = pattern.lstrip("**/").replace("**/", "")
        # 逐段匹配
        parts = p.split("/")
        # 全路径匹配
        if fnmatch.fnmatch(p, pattern.lstrip("**/")):
            return True
        # 任意段匹配
        for part in parts:
            if fnmatch.fnmatch(part, pat):
                return True
    return False


def _file_hash(filepath, is_text):
    h = xxhash.xxh64()
    with open(filepath, "rb") as f:
        data = f.read()
    if is_text:
        data = data.replace(b"\r\n", b"\n")
    h.update(data)
    return h.hexdigest()


def scan(root, exclude_patterns, text_extensions):
    """扫描 root 目录，返回文件清单 dict。遇到锁文件则标记 LOCKED 跳过。"""
    root = Path(root)
    manifest = {}
    text_ext_set = set(ext.lower() for ext in text_extensions)

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)

        # 剪枝：将被排除的子目录从递归中移除
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_excluded(
                os.path.join(rel_dir, d).replace("\\", "/"), exclude_patterns
            )
        ]

        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root).replace("\\", "/")

            if _is_excluded(rel, exclude_patterns):
                continue

            # Windows 文件名非法字符检查（针对 Mac 端传来的路径）
            if any(c in fname for c in WIN_ILLEGAL):
                manifest[rel] = {"status": "SKIPPED_ILLEGAL_CHAR"}
                continue

            stat = None
            try:
                stat = os.stat(full)
            except (PermissionError, OSError):
                manifest[rel] = {"status": "SKIPPED_LOCKED"}
                continue

            is_text = Path(fname).suffix.lower() in text_ext_set

            try:
                file_hash = _file_hash(full, is_text)
            except (PermissionError, OSError):
                manifest[rel] = {"status": "SKIPPED_LOCKED"}
                continue

            manifest[rel] = {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "hash": file_hash,
                "is_text": is_text,
            }

    return manifest

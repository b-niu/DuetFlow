"""测试 duetflow.scanner 模块的文件扫描与换行符归一化功能"""

import time

from duetflow import scanner


def test_is_excluded():
    """测试文件排除规则匹配。

    full_match() 使用标准 glob 语义：
      - "**/.git"     只匹配路径末尾是 .git 的条目（目录本身）
      - "**/.git/**"  匹配 .git 目录内的任意深度文件
      - "**/node_modules/**" 匹配 node_modules 目录内的文件

    注意：在实际扫描中，node_modules 等目录已在 dirnames[:] 过滤阶段被剪枝，
    其内部文件永远不会到达 _is_excluded 的文件判断逻辑。
    """
    exclude_dirs = ["**/.git", "**/.git/**", "**/node_modules", "**/.DS_Store"]
    # 目录自身的匹配
    assert scanner._is_excluded(".git", exclude_dirs)
    assert scanner._is_excluded("sub/node_modules", exclude_dirs)

    # .git 内部文件需要 "**/.git/**" 模式
    assert scanner._is_excluded("sub/.git/config", exclude_dirs)

    # node_modules 内部文件：实际扫描不会到这里（目录被剪枝），
    # 若需直接匹配，pattern 应写 "**/node_modules/**"
    exclude_with_glob = ["**/.git", "**/.git/**", "**/node_modules/**", "**/.DS_Store"]
    assert scanner._is_excluded("node_modules/express/index.js", exclude_with_glob)

    assert scanner._is_excluded("dir/.DS_Store", exclude_dirs)

    assert not scanner._is_excluded("src/main.py", exclude_dirs)
    assert not scanner._is_excluded("README.md", exclude_dirs)


def test_hidden_entries_are_skipped(tmp_path):
    """以 '.' 开头的目录/文件应被忽略，不进入清单"""
    root = tmp_path / "ws"
    root.mkdir()
    (root / "keep.txt").write_text("ok")
    (root / ".gitignore").write_text("ignored")
    dotdir = root / ".workbuddy"
    dotdir.mkdir()
    (dotdir / "memory.md").write_text("ignored")
    nested = root / "sub" / ".Rproj.user"
    nested.mkdir(parents=True)
    (nested / "a").write_text("ignored")

    manifest = scanner.scan(str(root), [], [])
    assert "keep.txt" in manifest
    assert ".gitignore" not in manifest
    assert ".workbuddy/memory.md" not in manifest
    assert "sub/.Rproj.user/a" not in manifest


def test_hidden_entry_helper():
    assert scanner._is_hidden_entry(".git")
    assert scanner._is_hidden_entry(".DS_Store")
    assert not scanner._is_hidden_entry("src")
    assert not scanner._is_hidden_entry(".")
    assert not scanner._is_hidden_entry("..")


def test_file_hash_crlf_normalization(tmp_path):
    """测试文本文件 CRLF 与 LF 归一化后得到的哈希值一致"""
    file_crlf = tmp_path / "crlf.txt"
    file_lf = tmp_path / "lf.txt"

    file_crlf.write_bytes(b"hello\r\nworld\r\n")
    file_lf.write_bytes(b"hello\nworld\n")

    hash_crlf = scanner._file_hash(file_crlf, is_text=True, size=len(b"hello\r\nworld\r\n"))
    hash_lf = scanner._file_hash(file_lf, is_text=True, size=len(b"hello\nworld\n"))

    assert hash_crlf == hash_lf, "CRLF 与 LF 文本文件的 hash 应一致（跨平台一致性）"

    # 二进制前缀哈希：相同内容前缀 + 相同大小 → 哈希一致（双端可比）
    big_a = tmp_path / "big_a.bin"
    big_b = tmp_path / "big_b.bin"
    big_a.write_bytes(b"A" * (1024 * 1024))
    big_b.write_bytes(b"A" * (1024 * 1024))
    assert scanner._file_hash(big_a, is_text=False, size=big_a.stat().st_size) == \
           scanner._file_hash(big_b, is_text=False, size=big_b.stat().st_size)

    # 内容前缀不同 → 哈希不同
    big_c = tmp_path / "big_c.bin"
    big_c.write_bytes(b"B" * (1024 * 1024))
    assert scanner._file_hash(big_a, is_text=False, size=big_a.stat().st_size) != \
           scanner._file_hash(big_c, is_text=False, size=big_c.stat().st_size)


def test_mtime_cache_skips_hash(tmp_path):
    """mtime + size 未变时，应直接复用 prev_manifest 中的 hash，不重新计算 I/O"""
    root = tmp_path / "ws"
    root.mkdir()
    f = root / "data.py"
    f.write_text("print('hello')")

    # 首次扫描
    mf1 = scanner.scan(str(root), [], [".py"])
    assert "data.py" in mf1
    original_hash = mf1["data.py"]["hash"]

    # 篡改 prev_manifest 中的 hash（模拟缓存命中）
    fake_prev = {
        "data.py": {
            "size": mf1["data.py"]["size"],
            "mtime": mf1["data.py"]["mtime"],
            "hash": "CACHED_HASH_VALUE",
            "is_text": True,
        }
    }

    # 第二次扫描传入 prev_manifest：mtime + size 一致 → 应直接返回 CACHED_HASH_VALUE
    mf2 = scanner.scan(str(root), [], [".py"], prev_manifest=fake_prev)
    assert mf2["data.py"]["hash"] == "CACHED_HASH_VALUE", \
        "mtime+size 未变时应命中缓存，返回 prev_manifest 中的 hash"


def test_mtime_cache_recomputes_on_change(tmp_path):
    """文件修改后（mtime 变化），应重新计算 hash"""
    root = tmp_path / "ws"
    root.mkdir()
    f = root / "data.py"
    f.write_text("version = 1")

    mf1 = scanner.scan(str(root), [], [".py"])

    # 修改文件内容（mtime 会更新）
    time.sleep(0.01)  # 确保 mtime 不同
    f.write_text("version = 2")

    # prev_manifest 中保存旧的 mtime（已过期）
    old_mtime = mf1["data.py"]["mtime"]
    fake_prev = {
        "data.py": {
            "size": mf1["data.py"]["size"],
            "mtime": old_mtime,
            "hash": "OLD_HASH",
            "is_text": True,
        }
    }

    mf2 = scanner.scan(str(root), [], [".py"], prev_manifest=fake_prev)
    # mtime 已变，应重新计算 hash，不等于 "OLD_HASH"
    assert mf2["data.py"]["hash"] != "OLD_HASH", \
        "文件修改后应重新计算 hash，不应使用缓存"


def test_concurrent_scan_produces_correct_results(tmp_path):
    """并发扫描（ThreadPoolExecutor）应正确返回所有文件的 hash"""
    root = tmp_path / "ws"
    root.mkdir()

    # 创建多个文件，确保并发路径被充分测试
    files = {}
    for i in range(20):
        f = root / f"file_{i:02d}.txt"
        content = f"content of file {i}"
        f.write_text(content)
        files[f"file_{i:02d}.txt"] = content

    manifest = scanner.scan(str(root), [], [".txt"])

    # 所有文件都应被扫描到
    for fname in files:
        assert fname in manifest, f"{fname} 应在扫描结果中"
        assert "hash" in manifest[fname], f"{fname} 应有 hash 字段"
        assert not manifest[fname].get("status"), f"{fname} 不应有错误状态"


def test_exclude_nested_dot_dirs(tmp_path):
    """嵌套路径中的 .xxx 目录应被正确剪枝，不进入清单"""
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("# main")
    # 嵌套 .cache 目录
    cache = root / "src" / ".cache"
    cache.mkdir()
    (cache / "cached_file.bin").write_bytes(b"\x00" * 100)

    manifest = scanner.scan(str(root), [], [".py"])
    assert "src/main.py" in manifest
    assert "src/.cache/cached_file.bin" not in manifest, \
        "嵌套 .cache 目录中的文件不应被扫描"

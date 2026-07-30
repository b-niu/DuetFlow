"""测试 duetflow.scanner 模块的文件扫描与换行符归一化功能"""

from duetflow import scanner


def test_is_excluded():
    """测试文件排除规则匹配"""
    exclude = ["**/.git", "**/.git/**", "**/node_modules", "**/.DS_Store"]

    assert scanner._is_excluded(".git", exclude)
    assert scanner._is_excluded("sub/.git/config", exclude)
    assert scanner._is_excluded("node_modules/express/index.js", exclude)
    assert scanner._is_excluded("dir/.DS_Store", exclude)

    assert not scanner._is_excluded("src/main.py", exclude)
    assert not scanner._is_excluded("README.md", exclude)


def test_file_hash_crlf_normalization(tmp_path):
    """测试文本文件 CRLF 与 LF 归一化后得到的哈希值一致"""
    file_crlf = tmp_path / "crlf.txt"
    file_lf = tmp_path / "lf.txt"

    file_crlf.write_bytes(b"hello\r\nworld\r\n")
    file_lf.write_bytes(b"hello\nworld\n")

    hash_crlf = scanner._file_hash(file_crlf, is_text=True)
    hash_lf = scanner._file_hash(file_lf, is_text=True)

    assert hash_crlf == hash_lf

"""远端轻量扫描 CLI 入口。

由 Windows 端通过 SSH 执行：
  cd /Users/bing/MyGithub/DuetFlow && uv run python -m duetflow.cli_scan
从 stdin 读入 JSON 参数，调 scanner.scan()，输出 JSON 到 stdout。
"""

import gzip
import json
import sys

from duetflow.scanner import scan


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

    raw = sys.stdin.read().strip()
    if not raw:
        print("{}")
        return

    req = json.loads(raw)
    root = req["root"]
    exclude = req.get("exclude", [])
    text_extensions = req.get("text_extensions", [])

    prev_b64 = req.get("prev_manifest_b64")
    prev_manifest = None
    if prev_b64:
        import base64
        gz_bytes = base64.b64decode(prev_b64)
        prev_manifest = json.loads(gzip.decompress(gz_bytes).decode("utf-8"))

    result = scan(root, exclude, text_extensions, prev_manifest=prev_manifest)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

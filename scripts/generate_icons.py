#!/usr/bin/env python3
"""
DuetFlow 图标生成脚本
利用源图片自动生成 Windows 专用 (.ico) 和 macOS 专用 (.icns / .png) 图标。
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"

def generate_icons(source_image_path: Path):
    """根据源图片生成 Windows (.ico) 和 macOS (.icns) 图标"""
    if not Image:
        print("[Error] 未安装 Pillow 库，请先执行 `pip install Pillow`。")
        sys.exit(1)

    if not source_image_path.exists():
        print(f"[Error] 找不到源图片文件 {source_image_path}")
        sys.exit(1)

    print(f"[Info] 正在从 {source_image_path.name} 生成双端图标...")

    img = Image.open(source_image_path)

    # 1. 生成 Windows .ico 图标
    ico_path = ASSETS_DIR / "icon.ico"
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"[Success] 已生成 Windows 图标: {ico_path}")

    # 2. 生成 macOS .icns 图标
    icns_path = ASSETS_DIR / "icon.icns"
    try:
        img.save(icns_path, format="ICNS")
        print(f"[Success] 已生成 macOS 图标: {icns_path}")
    except Exception:
        mac_png_path = ASSETS_DIR / "icon_mac.png"
        img.save(mac_png_path, format="PNG")
        print(f"[Warning] 当前环境未导出 ICNS，已导出 macOS 高清 PNG 图标: {mac_png_path}")

if __name__ == "__main__":
    source = ASSETS_DIR / "windows_master.png"
    generate_icons(source)

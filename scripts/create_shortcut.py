#!/usr/bin/env python3
"""
DuetFlow 桌面快捷方式一键生成脚本
根据当前运行平台 (Windows / macOS)，自动在桌面创建关联专用 Icon 图标的快捷方式。
"""

import sys
import os
import platform
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"

def get_desktop_path() -> Path:
    """获取当前系统桌面目录"""
    home = Path.home()
    desktop = home / "Desktop"
    if not desktop.exists():
        desktop = home / "桌面"
    return desktop

def create_windows_shortcut(desktop_dir: Path):
    """Windows 平台：通过 PowerShell / WScript.Shell 生成带有 .ico 的 .lnk 快捷方式"""
    shortcut_path = desktop_dir / "DuetFlow.lnk"
    ico_path = ASSETS_DIR / "icon.ico"

    ps_script = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = 'python.exe'
    $Shortcut.Arguments = '-m duetflow.gui'
    $Shortcut.WorkingDirectory = '{ROOT_DIR}'
    if (Test-Path '{ico_path}') {{
        $Shortcut.IconLocation = '{ico_path}'
    }}
    $Shortcut.Save()
    """

    try:
        subprocess.run(["powershell", "-Command", ps_script], check=True)
        print(f"[Success] 成功在 Windows 桌面创建快捷方式: {shortcut_path}")
    except Exception as e:
        print(f"[Error] 创建 Windows 快捷方式失败: {e}")

def create_mac_shortcut(desktop_dir: Path):
    """macOS 平台：生成双击可运行的 .command 终端脚本"""
    shortcut_path = desktop_dir / "DuetFlow.command"
    
    script_content = f"""#!/bin/bash
# DuetFlow macOS 启动快捷方式
cd "{ROOT_DIR}"
python3 -m duetflow.gui
"""

    try:
        shortcut_path.write_text(script_content, encoding="utf-8")
        os.chmod(shortcut_path, 0o755)
        print(f"[Success] 成功在 macOS 桌面创建快捷方式: {shortcut_path}")
    except Exception as e:
        print(f"[Error] 创建 macOS 快捷方式失败: {e}")

def main():
    desktop = get_desktop_path()
    current_os = platform.system()

    print(f"[Info] 开始为 {current_os} 生成桌面快捷方式...")
    if current_os == "Windows":
        create_windows_shortcut(desktop)
    elif current_os == "Darwin":
        create_mac_shortcut(desktop)
    else:
        print(f"[Info] 当前操作系统 {current_os} 暂未专门适配桌面快捷方式生成。")

if __name__ == "__main__":
    main()

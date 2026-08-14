#!/usr/bin/env python3
"""Securely configure credentials for read-only portfolio connectors."""

from __future__ import annotations

import argparse
import getpass
import platform
import subprocess
import sys
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))


def _secret_terminal(label: str) -> str:
    while True:
        value = getpass.getpass(f"{label}（输入不可见）: ").strip()
        if value:
            print(f"{label} 已接收。")
            return value
        print("不能为空，请重新输入。")


def _secret_dialog(label: str) -> str:
    script = f'''
        display dialog "请粘贴 {label}" default answer "" with hidden answer \
            buttons {{"取消", "确定"}} default button "确定" cancel button "取消" \
            with title "Vibe-Trading 安全配置"
        return text returned of result
    '''
    while True:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise KeyboardInterrupt from exc
        value = result.stdout.strip()
        if value:
            print(f"{label} 已接收。")
            return value
        print(f"{label} 不能为空，请在弹窗中重新输入。")


def _secret(label: str, *, gui: bool) -> str:
    return _secret_dialog(label) if gui else _secret_terminal(label)


def configure_longbridge(*, gui: bool) -> Path:
    from src.trading.connectors.longbridge.sdk import LongbridgeConfig, save_config

    print("配置长桥只读持仓连接。请从长桥开发者中心复制以下三项。")
    config = LongbridgeConfig.from_mapping(
        {
            "app_key": _secret("App Key", gui=gui),
            "app_secret": _secret("App Secret", gui=gui),
            "access_token": _secret("Access Token", gui=gui),
            "profile": "live-readonly",
            "region": "global",
            "readonly": True,
        }
    )
    return save_config(config)


def configure_binance(*, gui: bool) -> Path:
    from src.trading.connectors.binance.sdk import BinanceConfig, save_config

    print("配置币安现货只读持仓连接。API 必须关闭现货交易和提现权限。")
    config = BinanceConfig.from_mapping(
        {
            "api_key": _secret("API Key", gui=gui),
            "api_secret": _secret("Secret Key", gui=gui),
            "profile": "live-readonly",
            "readonly": True,
        }
    )
    return save_config(config)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("connector", choices=("longbridge", "binance"))
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="use hidden terminal input instead of macOS dialogs",
    )
    args = parser.parse_args()

    gui = platform.system() == "Darwin" and not args.terminal

    path = (
        configure_longbridge(gui=gui)
        if args.connector == "longbridge"
        else configure_binance(gui=gui)
    )
    print(f"已安全保存到 {path}（仅当前用户可读）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

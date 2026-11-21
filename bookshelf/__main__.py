import argparse
import getpass
import json
import os
import secrets
from pathlib import Path

from waitress import serve
from werkzeug.security import generate_password_hash

from .app import create_app, start_worker
from .tts import ENDPOINTS


def main():
    parser = argparse.ArgumentParser(description="个人有声书库")
    parser.add_argument("command", choices=("init", "serve"))
    parser.add_argument("--data", type=Path, default=Path("book-data"), help="书库和配置目录")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--local-http", action="store_true", help="局域回环或 SSH 隧道试跑时允许 HTTP cookie")
    args = parser.parse_args()
    root = args.data.resolve()
    config_path = root / "credentials.json"

    if args.command == "init":
        if config_path.exists():
            parser.error("书库已经设置好。请运行 serve。")
        if not os.isatty(0):
            parser.error("请在交互式终端设置个人密码和 API Key。")
        password = getpass.getpass("为书库设置一个新的密码（至少 12 个字符）：")
        if len(password) < 12 or len(password) > 1024:
            parser.error("密码长度须为 12 到 1024 个字符。")
        if getpass.getpass("再输入一次书库密码：") != password:
            parser.error("两次密码不一致。")
        region = input("MiniMax Key 区域（cn / global，默认 cn）：").strip() or "cn"
        if region not in ENDPOINTS:
            parser.error("区域须为 cn 或 global。")
        key = getpass.getpass("MiniMax API Key（输入不回显）：").strip()
        if not key:
            parser.error("请输入 MiniMax API Key。")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        settings = {
            "password_hash": generate_password_hash(password),
            "session_key": secrets.token_hex(32),
            "region": region,
            "minimax_key": key,
        }
        with os.fdopen(os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as handle:
            json.dump(settings, handle)
        print("书库配置已保存。")
        return

    try:
        with config_path.open(encoding="utf-8") as handle:
            credentials = json.load(handle)
    except FileNotFoundError:
        parser.error("请先运行 init 并设置个人账号。")
    app = create_app(root, credentials, secure=not args.local_http)
    start_worker(app, root, credentials)
    print(f"书库正在监听 http://127.0.0.1:{args.port}", flush=True)
    serve(app, host="127.0.0.1", port=args.port, threads=4, max_request_body_size=50 * 1024 * 1024)


if __name__ == "__main__":
    main()

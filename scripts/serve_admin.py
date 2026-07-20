#!/usr/bin/env python3
"""管理ツール tools/admin.html をローカルで開くための起動用サーバー。

環境変数 YOUTUBE_API_KEY を GET /api/key で返すことで、admin.html が
APIキーを手入力せずに YouTube Data API を叩けるようにする。
リポジトリ直下を配信し、127.0.0.1 のみで待ち受ける（外部からは触れない）。

  python scripts/serve_admin.py
  → 表示された URL（http://127.0.0.1:8000/tools/admin.html）をブラウザで開く
"""
import argparse
import functools
import json
import os
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 8000


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # 環境変数のAPIキーをブラウザに渡す唯一のエンドポイント。localhost限定なので外部露出はない。
        if self.path == "/api/key":
            body = json.dumps({"key": os.environ.get("YOUTUBE_API_KEY", "")}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args):
        pass  # アクセスログは抑制（キー取得も含め静かに動かす）


def main():
    parser = argparse.ArgumentParser(description="管理ツール(tools/admin.html)のローカル起動用サーバー")
    parser.add_argument("--open", action="store_true",
                        help="起動時に既定のブラウザで管理ツールを自動で開く")
    args = parser.parse_args()

    handler = functools.partial(Handler, directory=str(ROOT))
    with ThreadingHTTPServer((HOST, PORT), handler) as httpd:
        url = f"http://{HOST}:{PORT}/tools/admin.html"
        key_state = "検出（自動で使用します）" if os.environ.get("YOUTUBE_API_KEY") \
            else "未設定（動画・チャンネル登録タブでは手入力が必要）"
        print("管理ツールを起動しました。ブラウザで次を開いてください:")
        print(f"  {url}")
        print(f"環境変数 YOUTUBE_API_KEY: {key_state}")
        print("停止するには Ctrl+C。")
        if args.open:
            # ソケットは既にbind+listen済みなので、この時点で開いて問題ない。
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n停止しました。")


if __name__ == "__main__":
    main()

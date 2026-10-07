#!/usr/bin/env python3
"""管理ツール tools/admin.html をローカルで開くための起動用サーバー。

環境変数 YOUTUBE_API_KEY を GET /api/key で返すことで、admin.html が
APIキーを手入力せずに YouTube Data API を叩けるようにする。
必要なHTML・JS・JSONだけを配信し、127.0.0.1 のみで待ち受ける。

  .venv/Scripts/python.exe scripts/serve_admin.py
  → 表示された URL（http://127.0.0.1:8000/tools/admin.html）をブラウザで開く
"""
import argparse
import functools
import json
import os
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 8000
# DNSリバインディング対策。127.0.0.1 で待ち受けていても、悪意あるサイトが自ドメインを
# 127.0.0.1 に向け直すとブラウザ経由で同一オリジン扱いで読まれてしまう。
# そのとき Host ヘッダーは相手のドメイン名になるので、ここに無い Host は拒否する。
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
ALLOWED_FILES = {
    "/tools/admin.html": "tools/admin.html",
    "/docs/index.html": "docs/index.html",
    "/docs/app.js": "docs/app.js",
    "/docs/videos.json": "docs/videos.json",
    "/docs/tags.json": "docs/tags.json",
    "/data/channels.json": "data/channels.json",
}


class Handler(SimpleHTTPRequestHandler):
    def host_allowed(self):
        hosts = self.headers.get_all("Host", [])
        if len(hosts) == 1 and hosts[0].lower() in ALLOWED_HOSTS:
            return True
        self.send_error(403, "Forbidden host")
        return False

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def request_path(self):
        try:
            parts = urlsplit(self.path)
        except ValueError:
            return ""
        return parts.path if not parts.scheme and not parts.netloc else ""

    def send_head(self):
        relative = ALLOWED_FILES.get(self.request_path())
        if relative is None:
            self.send_error(404, "Not found")
            return None
        expected = Path(self.directory).absolute() / relative
        # 許可したURLでも、実ファイルがリンク経由で別の場所を指す場合は配信しない。
        try:
            resolved = expected.resolve()
        except (OSError, RuntimeError):
            resolved = None
        if resolved != expected:
            self.send_error(404, "Not found")
            return None
        return super().send_head()

    def do_HEAD(self):
        self.serve_request(head_only=True)

    def do_GET(self):
        self.serve_request(head_only=False)

    def serve_request(self, head_only):
        if not self.host_allowed():
            return
        if self.request_path() == "/api/key":
            origin = self.headers.get("Origin")
            if (origin is not None and origin != f"http://{self.headers['Host'].lower()}") or \
                    self.headers.get("Sec-Fetch-Site") == "cross-site":
                self.send_error(403, "Forbidden origin")
                return
            body = json.dumps({"key": os.environ.get("YOUTUBE_API_KEY", "")}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return
        if head_only:
            super().do_HEAD()
        else:
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

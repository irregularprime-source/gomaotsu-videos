"""Offline regression checks. Dummy keys and temporary repositories only."""
import functools
import http.client
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import requests
import collect
import search_collect
import serve_admin


DUMMY_KEY = "AUDIT_DUMMY_KEY_DO_NOT_USE"


class ServerSecurityTests(unittest.TestCase):
    def setUp(self):
        key_env = mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": DUMMY_KEY})
        key_env.start()
        self.addCleanup(key_env.stop)

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name).resolve()
        for name in serve_admin.ALLOWED_FILES.values():
            path = cls.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        for name in [".git/config", "_local/private.txt", "docs/unlisted.html"]:
            path = cls.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("PRIVATE_FIXTURE", encoding="utf-8")
        handler = functools.partial(serve_admin.Handler, directory=str(cls.root))
        cls.server = serve_admin.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def request(self, path, method="GET", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, headers={"Host": "127.0.0.1:8000", **(headers or {})})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_allowed_files_get_and_head(self):
        for path in serve_admin.ALLOWED_FILES:
            for method in ["GET", "HEAD"]:
                with self.subTest(path=path, method=method):
                    status, headers, body = self.request(path, method)
                    self.assertEqual(status, 200)
                    self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                    self.assertEqual(headers["X-Frame-Options"], "DENY")
                    self.assertEqual(headers["Content-Security-Policy"], "frame-ancestors 'none'")
                    self.assertEqual(headers["Cache-Control"], "no-store")
                    self.assertEqual(body, b"fixture" if method == "GET" else b"")

    def test_directories_unlisted_and_traversal_denied(self):
        paths = ["/", "/docs/", "/.git/config", "/_local/private.txt", "/docs/unlisted.html",
                 "/docs/../.git/config", "/docs/%2e%2e/.git/config", "/%2egit/config",
                 "/docs%2f..%2f.git/config", "/docs/index.html/", "/data/event_tags.json"]
        for path in paths:
            for method in ["GET", "HEAD"]:
                with self.subTest(path=path, method=method):
                    status, _, body = self.request(path, method)
                    self.assertEqual(status, 404)
                    self.assertNotIn(b"PRIVATE_FIXTURE", body)

    def test_bad_host_denied(self):
        for method in ["GET", "HEAD"]:
            self.assertEqual(self.request("/api/key", method, {"Host": "attacker.example:8000"})[0], 403)

    def test_key_is_uncacheable_and_head_has_no_body(self):
        with mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": DUMMY_KEY}):
            status, headers, body = self.request("/api/key")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"key": DUMMY_KEY})
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertNotIn("Access-Control-Allow-Origin", headers)
            self.assertEqual(self.request("/api/key", "HEAD")[2], b"")

    def test_cross_origin_key_requests_denied(self):
        for headers in [{"Origin": "https://attacker.example"}, {"Sec-Fetch-Site": "cross-site"}]:
            for method in ["GET", "HEAD"]:
                self.assertEqual(self.request("/api/key", method, headers)[0], 403)
        self.assertEqual(self.request("/api/key", headers={"Origin": "http://127.0.0.1:8000"})[0], 200)

    def test_symlink_cannot_replace_an_allowed_file(self):
        path = self.root / "docs/app.js"
        target = self.root / "_local/private.txt"
        path.unlink()
        try:
            try:
                path.symlink_to(target)
            except OSError:
                self.skipTest("Creating symlinks requires developer mode or elevated privileges")
            for method in ["GET", "HEAD"]:
                status, _, body = self.request("/docs/app.js", method)
                self.assertEqual(status, 404)
                self.assertNotIn(b"PRIVATE_FIXTURE", body)
        finally:
            if path.is_symlink():
                path.unlink()
            path.write_text("fixture", encoding="utf-8")


class LoggingSecurityTests(unittest.TestCase):
    def failure(self, kind):
        url = f"https://www.googleapis.com/youtube/v3/videos?key={DUMMY_KEY}"
        if kind == "http":
            response = requests.Response()
            response.status_code, response.reason, response.url = 403, "Forbidden", url
            try:
                response.raise_for_status()
            except requests.HTTPError as error:
                return error
        return requests.Timeout(f"Timeout for {url}")

    def assert_safe(self, message):
        self.assertNotIn(DUMMY_KEY, message)
        self.assertNotIn("https://", message)
        self.assertNotIn("key=", message)

    def test_channel_errors_do_not_log_url_or_key(self):
        channel = {"channelId": "UC" + "a" * 22, "name": "fixture", "gomaOnly": True}
        for kind in ["http", "timeout"]:
            with self.subTest(kind=kind), mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": DUMMY_KEY}), \
                    mock.patch.object(collect, "load_channels", return_value=[channel]), \
                    mock.patch.object(collect, "load_videos", return_value={"videos": []}), \
                    mock.patch.object(collect, "fetch_uploads", side_effect=self.failure(kind)), \
                    mock.patch("sys.stderr", new_callable=io.StringIO) as errors, \
                    mock.patch("sys.stdout", new_callable=io.StringIO):
                collect.collect(dry_run=True)
                self.assert_safe(errors.getvalue())
                self.assertIn("HTTP 403" if kind == "http" else "Timeout", errors.getvalue())

    def test_search_and_metadata_failures_have_safe_logs_and_nonzero_exit(self):
        for endpoint in ["fetch_search_ids", "fetch_video_meta"]:
            for kind in ["http", "timeout"]:
                with self.subTest(endpoint=endpoint, kind=kind), \
                        mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": DUMMY_KEY}), \
                        mock.patch.object(search_collect, "load_videos", return_value={"videos": []}), \
                        mock.patch.object(search_collect, "fetch_search_ids", return_value=[("a" * 11, "ゴ魔乙")]), \
                        mock.patch.object(search_collect, endpoint, side_effect=self.failure(kind)), \
                        mock.patch("sys.argv", ["search_collect.py", "--dry-run"]), \
                        mock.patch("sys.stderr", new_callable=io.StringIO) as errors:
                    with self.assertRaises(SystemExit) as exit_info:
                        search_collect.main()
                    self.assertEqual(exit_info.exception.code, 1)
                    self.assert_safe(errors.getvalue())


class GitSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "Security Test",
                    "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "Security Test",
                    "GIT_COMMITTER_EMAIL": "test@example.invalid"}
        self.git("init", "-b", "main")
        (self.repo / "scripts").mkdir()
        for name in ["check_staged.py", "build_static.py"]:
            shutil.copy2(ROOT / "scripts" / name, self.repo / "scripts" / name)
        for name in ["変更を保存する.bat", "管理ツールを開く.bat"]:
            shutil.copy2(ROOT / name, self.repo / name)
        (self.repo / ".gitignore").write_text(".venv/\n__pycache__/\n", encoding="utf-8")
        (self.repo / "docs").mkdir()
        (self.repo / "data").mkdir()
        (self.repo / "docs/videos.json").write_text('{"updated":"2026-10-07T00:00:00+09:00","videos":[]}', encoding="utf-8")
        (self.repo / "docs/tags.json").write_text('{"tags":[]}', encoding="utf-8")
        (self.repo / "data/channels.json").write_text('{"channels":[]}', encoding="utf-8")
        (self.repo / "docs/index.html").write_text('<!-- BUILD:STATIC:START -->\n<!-- BUILD:STATIC:END -->\n', encoding="utf-8")
        subprocess.run([sys.executable, "-B", "scripts/build_static.py"], cwd=self.repo, env=self.env,
                       check=True, capture_output=True)
        self.git("add", ".")
        self.git("commit", "-m", "fixture")
        self.initial = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *args, check=True):
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env, capture_output=True, check=check)

    def check_staged(self):
        return subprocess.run([sys.executable, "-B", "scripts/check_staged.py"], cwd=self.repo,
                              env=self.env, capture_output=True)

    def test_unrelated_unicode_filename_is_rejected_without_changing_index(self):
        path = self.repo / "非公開 メモ.txt"
        path.write_text("PRIVATE_FIXTURE", encoding="utf-8")
        self.git("add", "--", path.name)
        before = self.git("diff", "--cached", "--binary").stdout
        result = self.check_staged()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.git("diff", "--cached", "--binary").stdout, before)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.initial)

    def test_rename_from_unlisted_file_is_rejected(self):
        path = self.repo / "private.txt"
        path.write_text("fixture", encoding="utf-8")
        self.git("add", "private.txt")
        self.git("commit", "-m", "fixture private")
        self.git("mv", "private.txt", "docs/new.json")
        self.assertEqual(self.check_staged().returncode, 1)

    def test_allowed_changes_accepted(self):
        (self.repo / "docs/tags.json").write_text('{"tags":[{"name":"fixture","color":"#fff"}]}', encoding="utf-8")
        self.git("add", "docs/tags.json")
        self.assertEqual(self.check_staged().returncode, 0)

    def batch(self, name):
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(self.repo / ".venv")],
                       env=self.env, check=True, capture_output=True)
        return subprocess.run(["cmd.exe", "/d", "/c", name], cwd=self.repo, env=self.env,
                              input=b"\r\n" * 12, capture_output=True, timeout=45)

    @unittest.skipUnless(os.name == "nt", "Windows batch regression")
    def test_save_batch_stops_before_build_or_commit_for_unrelated_staged_file(self):
        (self.repo / "private.txt").write_text("PRIVATE_FIXTURE", encoding="utf-8")
        self.git("add", "private.txt")
        before = (self.repo / "docs/index.html").read_bytes()
        result = self.batch("変更を保存する.bat")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.repo / "docs/index.html").read_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.initial)
        self.assertIn(b"private.txt", self.git("diff", "--cached", "--name-only").stdout)

    @unittest.skipUnless(os.name == "nt", "Windows batch regression")
    def test_save_batch_commits_only_allowed_changes_to_local_bare_remote(self):
        remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], env=self.env, check=True, capture_output=True)
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-u", "origin", "main")
        (self.repo / "docs/videos.json").write_text('{"updated":"2026-10-08T00:00:00+09:00","videos":[]}', encoding="utf-8")
        result = self.batch("変更を保存する.bat")
        self.assertEqual(result.returncode, 0, result.stdout.decode("cp932", errors="replace"))
        changed = set(self.git("diff", "--name-only", self.initial, "HEAD").stdout.splitlines())
        self.assertEqual(changed, {b"docs/videos.json", b"docs/index.html", b"docs/sitemap.xml"})
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, self.git("rev-parse", "origin/main").stdout)

    @unittest.skipUnless(os.name == "nt", "Windows batch regression")
    def test_admin_batch_does_not_start_server_after_pull_failure(self):
        (self.repo / "scripts/serve_admin.py").write_text('from pathlib import Path\nPath("server-started").write_text("bad")\n', encoding="utf-8")
        result = self.batch("管理ツールを開く.bat")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / "server-started").exists())


if __name__ == "__main__":
    unittest.main()

"""Offline checks for collect.py's one-off options (--channel / --all / --after / --before)."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import collect

TARGET = "UC" + "a" * 22
OTHER = "UC" + "b" * 22


def upload(video_id, title, published):
    return {
        "snippet": {"resourceId": {"videoId": video_id}, "title": title, "description": ""},
        "contentDetails": {"videoPublishedAt": published},
    }


class CollectOptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.channels_path = tmp / "channels.json"
        self.videos_path = tmp / "videos.json"
        self.channels_path.write_text(json.dumps({"channels": [
            {"channelId": TARGET, "name": "対象", "gomaOnly": False},
            {"channelId": OTHER, "name": "ほか", "gomaOnly": False},
        ]}), encoding="utf-8")
        self.videos_path.write_text(json.dumps({"videos": []}), encoding="utf-8")
        self.uploads = {
            TARGET: [upload("v_old_plain", "身内用 ブレイク", "2016-05-01T00:00:00Z"),
                     upload("v_old_goma", "ゴ魔乙 第50回スコア大会", "2016-05-02T00:00:00Z"),
                     upload("v_new_plain", "雑談配信", "2019-01-01T00:00:00Z")],
            OTHER: [upload("v_other", "ゴ魔乙 ギルバト", "2016-05-03T00:00:00Z")],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_collect(self, **kwargs):
        fetched = []

        def fake_fetch(channel_id, api_key, all_pages=False):
            fetched.append(channel_id)
            return self.uploads[channel_id]

        with mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": "AUDIT_DUMMY_KEY_DO_NOT_USE"}), \
                mock.patch.object(collect, "CHANNELS_PATH", self.channels_path), \
                mock.patch.object(collect, "VIDEOS_PATH", self.videos_path), \
                mock.patch.object(collect, "fetch_uploads", side_effect=fake_fetch), \
                mock.patch("sys.stdout", new_callable=io.StringIO), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            code = collect.collect(False, backfill=True, **kwargs)
        ids = [v["videoId"] for v in json.loads(self.videos_path.read_text(encoding="utf-8"))["videos"]]
        return code, fetched, ids

    def test_channel_all_and_period(self):
        code, fetched, ids = self.run_collect(channel_id=TARGET, take_all=True, before="2018-09-16")
        self.assertEqual(code, 0)
        self.assertEqual(fetched, [TARGET])
        self.assertEqual(ids, ["v_old_plain", "v_old_goma"])

    def test_without_all_keeps_keyword_check(self):
        code, _, ids = self.run_collect(channel_id=TARGET)
        self.assertEqual(code, 0)
        self.assertEqual(ids, ["v_old_goma"])

    def test_unknown_channel_is_error(self):
        code, fetched, ids = self.run_collect(channel_id="UC" + "c" * 22, take_all=True)
        self.assertEqual(code, 1)
        self.assertEqual(fetched, [])
        self.assertEqual(ids, [])

    def test_all_requires_channel(self):
        with mock.patch("sys.argv", ["collect.py", "--backfill", "--all"]), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as exit_info:
                collect.main()
        self.assertEqual(exit_info.exception.code, 2)

    def test_in_period(self):
        self.assertTrue(collect.in_period("2015-04-01T03:00:00Z", "2015-04-01", "2018-09-16"))
        self.assertTrue(collect.in_period("2018-09-15T23:59:59Z", "2015-04-01", "2018-09-16"))
        self.assertFalse(collect.in_period("2018-09-16T00:00:00Z", "2015-04-01", "2018-09-16"))
        self.assertTrue(collect.in_period("2020-01-01T00:00:00Z"))


if __name__ == "__main__":
    unittest.main()

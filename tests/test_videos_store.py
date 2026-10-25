"""Offline checks for the per-year video files (scripts/videos_store.py)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import videos_store


def video(video_id, published):
    return {"videoId": video_id, "title": "t", "publishedAt": published, "tags": []}


class VideosStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name) / "videos"

    def test_round_trip_splits_by_published_year(self):
        doc = {"updated": "2026-10-26T00:00:00+09:00", "videos": [
            video("a", "2019-12-31T23:59:59Z"), video("b", "2015-04-01T00:00:00Z"), video("c", "2019-01-01T00:00:00Z")]}
        videos_store.save_videos(doc, self.dir)
        index = json.loads((self.dir / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index, {"updated": "2026-10-26T00:00:00+09:00", "files": ["2015.json", "2019.json"]})
        y2019 = json.loads((self.dir / "2019.json").read_text(encoding="utf-8"))
        self.assertEqual(y2019["year"], "2019")
        self.assertEqual([v["videoId"] for v in y2019["videos"]], ["a", "c"])
        loaded = videos_store.load_videos(self.dir)
        self.assertEqual(loaded["updated"], doc["updated"])
        self.assertEqual(sorted(v["videoId"] for v in loaded["videos"]), ["a", "b", "c"])

    def test_empty_year_file_is_removed_and_unchanged_file_is_not_rewritten(self):
        videos_store.save_videos({"updated": "1", "videos": [video("a", "2015-05-01T00:00:00Z"),
                                                              video("b", "2016-05-01T00:00:00Z")]}, self.dir)
        before = (self.dir / "2016.json").stat().st_mtime_ns
        videos_store.save_videos({"updated": "2", "videos": [video("b", "2016-05-01T00:00:00Z")]}, self.dir)
        self.assertFalse((self.dir / "2015.json").exists())
        self.assertEqual((self.dir / "2016.json").stat().st_mtime_ns, before)
        self.assertEqual(json.loads((self.dir / "index.json").read_text(encoding="utf-8"))["files"], ["2016.json"])

    def test_format_matches_admin_serialize(self):
        videos_store.save_videos({"updated": "", "videos": [video("あ", "2020-01-01T00:00:00Z")]}, self.dir)
        text = (self.dir / "2020.json").read_text(encoding="utf-8")
        self.assertEqual(text, json.dumps({"year": "2020", "videos": [video("あ", "2020-01-01T00:00:00Z")]},
                                          ensure_ascii=False, indent=2) + "\n")

    def test_missing_published_year_is_an_error(self):
        with self.assertRaises(ValueError):
            videos_store.save_videos({"updated": "", "videos": [video("a", "")]}, self.dir)


if __name__ == "__main__":
    unittest.main()

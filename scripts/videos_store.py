"""docs/videos/ の年別ファイルの読み書き（収集・再分類・静的索引で共用）。

  docs/videos/index.json  … {"updated": 最終更新, "files": ["2015.json", ...]}
  docs/videos/2015.json   … {"year": "2015", "videos": [...]}（公開日 publishedAt の年。UTC）

呼び出し側は従来の videos.json と同じ {"updated", "videos"} の形で扱い、保存時に年ごとへ分ける。
Why 年別: 1ファイルが GitHub の警告（50MB）に近づいたため（2026-10-26 ユーザー判断 案A）。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# テストで差し替えられるよう、関数の中で参照する。
VIDEOS_DIR = ROOT / "docs" / "videos"
INDEX_NAME = "index.json"


def dumps(obj):
    """Python の json.dumps(ensure_ascii=False, indent=2)+改行。管理ツールの serialize と一致させる。"""
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def year_of(video):
    year = (video.get("publishedAt") or "")[:4]
    if not (len(year) == 4 and year.isdigit()):
        raise ValueError(f"publishedAt から年を取れません: {video.get('videoId')!r}")
    return year


def load_videos(directory=None):
    """年別ファイルをまとめて {"updated", "videos"} を返す（index.json の files の順）。"""
    directory = Path(directory or VIDEOS_DIR)
    index = json.loads((directory / INDEX_NAME).read_text(encoding="utf-8"))
    videos = []
    for name in index.get("files", []):
        videos.extend(json.loads((directory / name).read_text(encoding="utf-8"))["videos"])
    return {"updated": index.get("updated", ""), "videos": videos}


def save_videos(doc, directory=None):
    """{"updated", "videos"} を年ごとに分けて書く。中身が同じファイルは書き直さない。
    動画が無くなった年のファイルは消す。"""
    directory = Path(directory or VIDEOS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    by_year = {}
    for v in doc["videos"]:
        by_year.setdefault(year_of(v), []).append(v)
    files = []
    for year in sorted(by_year):
        name = f"{year}.json"
        files.append(name)
        write_if_changed(directory / name, dumps({"year": year, "videos": by_year[year]}))
    for old in directory.glob("[0-9][0-9][0-9][0-9].json"):
        if old.name not in files:
            old.unlink()
    write_if_changed(directory / INDEX_NAME, dumps({"updated": doc.get("updated", ""), "files": files}))


def write_if_changed(path, text):
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")

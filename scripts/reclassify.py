#!/usr/bin/env python3
"""既存 videos.json のタグを最新の分類ルールで再計算する（バックフィル）。

collect.py のキーワード表や抽出ルールを更新したとき、収集済みの自動分類エントリへ
新ルールを反映するために使う。手動確認済み（status:"確認済み"）は上書きしない。

  python scripts/reclassify.py            # 変更を書き込む
  python scripts/reclassify.py --dry-run  # 変更予定だけ表示
"""
import argparse
import json
import sys

from collect import VIDEOS_PATH, make_tags


def reclassify(dry_run):
    doc = json.loads(VIDEOS_PATH.read_text(encoding="utf-8"))
    changed = 0
    for v in doc["videos"]:
        # source:"auto" かつ status:"自動分類" のみ対象。手動登録・確認済みは保護する。
        # サンプル（運用者が削除する前提のダミー）は書き換えない。
        if v["videoId"].startswith("SAMPLE"):
            continue
        if v.get("source") != "auto" or v.get("status") != "自動分類":
            continue
        new_tags = make_tags(v.get("title", ""), v.get("description", ""))
        if new_tags != v["tags"]:
            if dry_run:
                print(f"  {v['videoId']}  {v['tags']} -> {new_tags}  {v['title']}")
            v["tags"] = new_tags
            changed += 1

    if dry_run:
        print(f"[dry-run] 再分類対象: {changed}件")
        return 0

    if changed:
        VIDEOS_PATH.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"{changed}件のタグを再計算しました。")
    return 0


def main():
    parser = argparse.ArgumentParser(description="videos.json のタグを再計算する")
    parser.add_argument("--dry-run", action="store_true",
                        help="書き込まず、変更予定のエントリを表示する")
    args = parser.parse_args()
    sys.exit(reclassify(args.dry_run))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ゴ魔乙動画の検索収集スクリプト（登録チャンネル収集とは別経路）。

YouTube search.list でキーワード横断検索し、docs/videos.json に未登録の動画を
source:"search" / status:"自動分類" で追記する。登録チャンネル収集(collect.py)が
拾えない未登録投稿者の動画を拾うのが目的。全件が未確認で入り、管理ツールの
レビューを経て取捨選択する。

  python scripts/search_collect.py                    # 直近6h（3hごとcronの常時スイープ）
  python scripts/search_collect.py --since-hours 24   # 直近24h
  python scripts/search_collect.py --after 2025-01-01 --before 2025-01-08  # 期間区切りの過去分バックフィル
  python scripts/search_collect.py --dry-run          # 書き込まず追加予定を表示

過去分は一気に入れず、--after/--before で公開期間ごと（1週間・1か月など）に
区切って少しずつ回す運用（PROJECT_STATE セクション8参照）。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

# collect.py と同じ scripts/ にあるため直接 import できる（reclassify.py と同じパターン）。
from collect import (
    VIDEOS_PATH, JST, GOMA_KEYWORDS,
    norm, is_gomaotsu, make_tags, load_videos,
)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def iso_z(dt):
    """datetime を search API 用の RFC3339（UTC・Z終端）文字列にする。"""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_search_ids(api_key, published_after, published_before=None):
    """検索条件に合う動画の (videoId, title) を返す。nextPageToken を辿って全ページ取得。

    q は GOMA_KEYWORDS を | (OR) で連結。type=video / order=date。
    件数はニッチな検索語のため通常わずか。過去分バックフィルで窓を広く取ると
    ページ数＝コスト（100ユニット/ページ）が増えるので、--after/--before で区切る。
    """
    results = []
    page_token = None
    while True:
        params = {
            "part": "snippet",
            "q": "|".join(GOMA_KEYWORDS),
            "type": "video",
            "order": "date",
            "maxResults": 50,
            "publishedAfter": published_after,
            "key": api_key,
        }
        if published_before:
            params["publishedBefore"] = published_before
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for it in data.get("items", []):
            vid = it.get("id", {}).get("videoId")
            title = it.get("snippet", {}).get("title", "")
            if vid:
                results.append((vid, title))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return results


def fetch_video_meta(video_ids, api_key):
    """videos.list で本メタ（title/channel/description/publishedAt）を取得する。id は50件ずつ。"""
    items = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        params = {
            "part": "snippet",
            "id": ",".join(chunk),
            "maxResults": 50,
            "key": api_key,
        }
        resp = requests.get(VIDEOS_URL, params=params, timeout=30)
        resp.raise_for_status()
        items.extend(resp.json().get("items", []))
    return items


def build_entry(item, now_iso):
    snip = item.get("snippet", {})
    title = snip.get("title", "")
    description = snip.get("description", "")
    return {
        "videoId": item.get("id"),
        "title": title,
        "channel": snip.get("channelTitle", ""),
        "description": description,
        "publishedAt": snip.get("publishedAt"),
        "registeredAt": now_iso,
        "source": "search",
        "tags": make_tags(title, description),
        "status": "自動分類",
        "note": "",
    }


def collect_search(dry_run, published_after, published_before):
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("環境変数 YOUTUBE_API_KEY が未設定です。", file=sys.stderr)
        return 1

    videos_doc = load_videos()
    existing_ids = {v["videoId"] for v in videos_doc["videos"]}

    found = fetch_search_ids(api_key, published_after, published_before)

    # 既存 videoId を除外（重複は videoId で単純排除。登録ch由来かどうかは問わない）。
    # ノイズ対策：判定はタイトルのみの is_gomaotsu。説明文の他ゲー言及に反応した
    # FF14型の紛れ込みを、確定前（登録前）に弾く。
    candidates, seen = [], set()
    for vid, title in found:
        if vid in existing_ids or vid in seen:
            continue
        if not is_gomaotsu(norm(title)):
            continue
        seen.add(vid)
        candidates.append(vid)

    now_iso = datetime.now(JST).isoformat(timespec="seconds")
    metas = fetch_video_meta(candidates, api_key) if candidates else []
    new_entries = [build_entry(m, now_iso) for m in metas]

    if dry_run:
        print(f"[dry-run] 検索ヒット {len(found)}件 → 追加予定 {len(new_entries)}件")
        for e in new_entries:
            print(f"  {e['videoId']}  {e['tags']}  {e['title']}  <{e['channel']}>")
        return 0

    if not new_entries:
        print("追加する新規動画はありませんでした。")
        return 0

    videos_doc["videos"].extend(new_entries)
    videos_doc["updated"] = now_iso
    VIDEOS_PATH.write_text(
        json.dumps(videos_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"動画{len(new_entries)}件を追加しました。")
    return 0


def main():
    parser = argparse.ArgumentParser(description="ゴ魔乙動画の検索収集")
    parser.add_argument("--dry-run", action="store_true",
                        help="videos.json を書き換えず、追加予定の動画一覧を表示する")
    parser.add_argument("--since-hours", type=int, default=6,
                        help="直近この時間内に公開された動画を対象（既定6h。3hごと実行に対し取りこぼし防止でやや広め）")
    parser.add_argument("--after",
                        help="この日付以降(YYYY-MM-DD, UTC基準)。過去分の期間区切りバックフィル用。指定時は --since-hours を無視")
    parser.add_argument("--before",
                        help="この日付より前(YYYY-MM-DD, UTC基準)。--after と組み合わせて期間を区切る")
    args = parser.parse_args()

    if args.after:
        published_after = args.after + "T00:00:00Z"
        published_before = args.before + "T00:00:00Z" if args.before else None
    else:
        published_after = iso_z(datetime.now(timezone.utc) - timedelta(hours=args.since_hours))
        published_before = None

    sys.exit(collect_search(args.dry_run, published_after, published_before))


if __name__ == "__main__":
    main()

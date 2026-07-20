#!/usr/bin/env python3
"""ゴ魔乙動画の定期収集スクリプト。

data/channels.json の各チャンネルのアップロード動画から、docs/videos.json に
未登録のゴ魔乙動画を抽出・自動分類して追記する。
"""
import argparse
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_PATH = ROOT / "data" / "channels.json"
VIDEOS_PATH = ROOT / "docs" / "videos.json"

API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
JST = timezone(timedelta(hours=9))

# ゴ魔乙動画の判定語（gomaOnly: false のチャンネル向け）。運用しながら追加しやすいよう定数化。
GOMA_KEYWORDS = ["ゴ魔乙", "ごまおつ", "ゴシックは魔法乙女"]

# タグ自動分類のキーワード表。dict の順序が付与タグの順序になる（index.html の表示順に合わせてある）。
# Why not「降臨」「復刻」: 発注者の指示によりイベントステージ判定には使わない。
TAG_KEYWORDS = {
    "スコア大会(週末)": ["土曜スコア", "週末スコア", "全国スコア大会"],
    "スコア大会(イベント)": ["イベントスコア"],
    "エーテルスコア大会": ["エーテルスコア"],
    "アリーナ": ["アリーナ"],
    "ギルドバトル": ["ギルドバトル", "ギルバト"],
    "イベントステージ": ["イベントステージ"],
    "メインストーリー": ["メインストーリー"],
    "キワメタワー": ["キワメタワー", "キワメ", "極タワー"],
}


def norm(text):
    """表記ゆれ対策：NFKC 正規化＋小文字化して判定用の文字列を返す。"""
    return unicodedata.normalize("NFKC", text or "").lower()


def is_gomaotsu(normalized_text):
    return any(norm(k) in normalized_text for k in GOMA_KEYWORDS)


def classify(normalized_text):
    """タイトル＋説明文（正規化済み）からタグ一覧を返す。該当なしは ['未分類']。"""
    tags = [tag for tag, kws in TAG_KEYWORDS.items()
            if any(norm(k) in normalized_text for k in kws)]
    return tags or ["未分類"]


def load_channels():
    data = json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))
    channels = []
    for ch in data.get("channels", []):
        cid = ch.get("channelId", "")
        # 外部入力のバリデーション：正規のチャンネルIDのみ対象にする。
        if not (cid.startswith("UC") and len(cid) == 24):
            print(f"[skip] 不正なchannelId: {cid!r} ({ch.get('name')})", file=sys.stderr)
            continue
        channels.append(ch)
    return channels


def load_videos():
    return json.loads(VIDEOS_PATH.read_text(encoding="utf-8"))


def fetch_uploads(channel_id, api_key):
    """チャンネルのアップロードプレイリスト最新50件を返す。

    アップロードプレイリストIDはチャンネルID先頭の UC を UU に置換したもの。
    channels.list を挟まず playlistItems.list を直接叩ける（1回=1クォータ）。
    """
    playlist_id = "UU" + channel_id[2:]
    params = {
        "part": "snippet,contentDetails",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": api_key,
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("items", [])


def build_entry(item, channel_name, now_iso):
    snip = item.get("snippet", {})
    video_id = snip.get("resourceId", {}).get("videoId")
    title = snip.get("title", "")
    description = snip.get("description", "")
    # contentDetails.videoPublishedAt が実際の公開日時。無ければ playlist 追加日時で代替。
    published = item.get("contentDetails", {}).get("videoPublishedAt") or snip.get("publishedAt")

    text = norm(title + "\n" + description)
    return {
        "videoId": video_id,
        "title": title,
        "channel": channel_name,
        "description": description,
        "publishedAt": published,
        "registeredAt": now_iso,
        "source": "auto",
        "tags": classify(text),
        "status": "自動分類",
        "note": "",
    }, text


def collect(dry_run):
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("環境変数 YOUTUBE_API_KEY が未設定です。", file=sys.stderr)
        return 1

    channels = load_channels()
    videos_doc = load_videos()
    existing_ids = {v["videoId"] for v in videos_doc["videos"]}

    now = datetime.now(JST)
    now_iso = now.isoformat(timespec="seconds")

    new_entries = []
    for ch in channels:
        try:
            items = fetch_uploads(ch["channelId"], api_key)
        except requests.RequestException as e:
            # あるチャンネルの取得失敗で全体を止めない。
            print(f"[error] {ch['name']} ({ch['channelId']}): {e}", file=sys.stderr)
            continue

        for item in items:
            entry, text = build_entry(item, ch["name"], now_iso)
            if not entry["videoId"] or entry["videoId"] in existing_ids:
                continue  # 既存 videoId は手動修正保護のためスキップ
            if not (ch.get("gomaOnly") or is_gomaotsu(text)):
                continue
            existing_ids.add(entry["videoId"])
            new_entries.append(entry)

    if dry_run:
        print(f"[dry-run] 追加予定: {len(new_entries)}件")
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
    parser = argparse.ArgumentParser(description="ゴ魔乙動画の定期収集")
    parser.add_argument("--dry-run", action="store_true",
                        help="videos.json を書き換えず、追加予定の動画一覧を表示する")
    args = parser.parse_args()
    sys.exit(collect(args.dry_run))


if __name__ == "__main__":
    main()

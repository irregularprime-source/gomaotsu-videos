#!/usr/bin/env python3
"""ゴ魔乙動画の定期収集スクリプト。

data/channels.json の各チャンネルのアップロード動画から、docs/videos.json に
未登録のゴ魔乙動画を抽出・自動分類して追記する。
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_PATH = ROOT / "data" / "channels.json"
VIDEOS_PATH = ROOT / "docs" / "videos.json"
EVENT_TAGS_PATH = ROOT / "data" / "event_tags.json"

API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
JST = timezone(timedelta(hours=9))

# ゴ魔乙動画の判定語（gomaOnly: false のチャンネル向け）。運用しながら追加しやすいよう定数化。
GOMA_KEYWORDS = ["ゴ魔乙", "ごまおつ", "ゴシックは魔法乙女", "ゴマ乙"]

# --- タグ自動分類の語彙 ---
# Why not「降臨」「復刻」: 発注者の指示によりイベントステージ判定には使わない。
# スコア大会系を示す語（略語含む）。ドヨアタ＝土曜アタック＝週末スコア大会。
SCORE_MARKERS = ["スコア大会", "スコアタ", "ドヨアタ", "どよあた"]
# スコア大会の週末/イベント振り分け語。いずれかを含めばイベント、含まなければ週末。
EVENT_WORDS = ["限定", "記念", "コラボ", "周年", "xmas", "クリスマス"]
# 単純な部分一致で付ける独立カテゴリ（dict の順序＝付与順）。
SIMPLE_KEYWORDS = {
    "アリーナ": ["アリーナ"],
    "イベントステージ": ["イベントステージ"],
    "メインストーリー": ["メインストーリー"],
    "キワメタワー": ["キワメタワー", "キワメ", "極タワー"],
    "ゴシック道": ["ゴシック道"],
    "ガチャ": ["ガチャ"],
}


def norm(text):
    """表記ゆれ対策：NFKC 正規化＋小文字化して判定用の文字列を返す。"""
    return unicodedata.normalize("NFKC", text or "").lower()


def is_gomaotsu(normalized_text):
    return any(norm(k) in normalized_text for k in GOMA_KEYWORDS)


# 回数抽出パターン。スコア数値（M/億/万等の単位付き）を回数と誤認しないよう、
# 「回/かい」やスコア大会系の語に隣接した数字だけを回数とみなす。上から順に最初の一致を採用。
ROUND_PATTERNS = [
    re.compile(r"第(\d+)回"),
    re.compile(r"(\d+)\s*回"),
    re.compile(r"(\d+)\s*かい"),
    re.compile(r"(?:ドヨアタ|どよあた)\s*(\d+)"),
    re.compile(r"(\d+)(?=スコアタ|ドヨアタ|どよあた)"),
]
# イベント名の簡易抽出：「○○限定」形式のみ拾う。
# Why not: タイトル書式が不揃いで、これ以外の形（接頭辞なしのイベント名等）は誤抽出が多いため対象外。
EVENT_RE = re.compile(r"([一-鿿ぁ-んァ-ヿー々〆]+)限定")


def load_event_tags():
    """スコア大会(イベント)のイベント名辞書を [(tag, [正規化済みkeyword, ...]), ...] で返す。
    『○○限定』形式は EVENT_RE が自動抽出するため辞書には入れない（重複回避）。"""
    data = json.loads(EVENT_TAGS_PATH.read_text(encoding="utf-8"))
    result = []
    for ev in data.get("events", []):
        tag = ev.get("tag")
        kws = [norm(k) for k in ev.get("keywords", []) if k]
        if tag and kws:
            result.append((tag, kws))
    return result


# イベント名辞書（モジュール読込時に1回だけロード。reclassify も import 経由で共用）。
EVENT_TAGS = load_event_tags()


def match_event_tags(ntitle):
    """正規化タイトルが辞書に一致したイベント名タグを、辞書順・重複排除で返す。"""
    matched = []
    for tag, kws in EVENT_TAGS:
        if tag not in matched and any(k in ntitle for k in kws):
            matched.append(tag)
    return matched


def classify(ntitle, has_round=False, has_event_dict=False):
    """正規化タイトルからカテゴリタグ一覧を返す。該当なしは ['未分類']。
    週末/イベントの判別は、説明文の別動画への言及を拾わないようタイトルのみで行う。
    has_round=True（回数「第○回」が取れた）はそれ自体を週末スコア大会の判定材料にする
    （「第579回 9,903万」のようにスコアタ表記が無くても回数付きは定期スコア大会のため）。"""
    tags = []

    # スコア大会ファミリー：親「スコア大会」＋下位1つ（週末/イベント/エーテル/リアル）
    is_ether = norm("エーテルスコア") in ntitle
    is_real = norm("団体戦") in ntitle            # リアルスコア大会（現状は団体戦のみ）
    is_score = is_ether or is_real or has_round or any(norm(m) in ntitle for m in SCORE_MARKERS)
    if is_score:
        tags.append("スコア大会")
        if is_ether:
            tags.append("エーテルスコア大会")
        elif is_real:
            tags.append("リアルスコア大会")
        elif any(norm(w) in ntitle for w in EVENT_WORDS) or has_event_dict:
            tags.append("スコア大会(イベント)")
        else:
            tags.append("スコア大会(週末)")

    # ギルドバトル：イベント（ギルイベ / ギルドイベント）を通常より優先
    if any(norm(k) in ntitle for k in ["ギルイベ", "ギルドイベント"]):
        tags.append("ギルドバトル(イベント)")
    elif any(norm(k) in ntitle for k in ["ギルドバトル", "ギルバト"]):
        tags.append("ギルドバトル(通常)")

    # 独立カテゴリ
    for tag, kws in SIMPLE_KEYWORDS.items():
        if any(norm(k) in ntitle for k in kws):
            tags.append(tag)

    return tags or ["未分類"]


def extract_round(ntitle):
    """タイトルから回数（整数）を1つ返す。無ければ None。"""
    for pat in ROUND_PATTERNS:
        m = pat.search(ntitle)
        if m:
            return int(m.group(1))
    return None


def make_tags(title, description):
    """1動画に付ける全タグ（カテゴリ＋回数＋イベント名）を返す。build_entry と reclassify で共用。
    分類はタイトル基準（description は収集判定 is_gomaotsu でのみ使う）。"""
    ntitle = norm(title)
    r = extract_round(ntitle)
    event_tags = match_event_tags(ntitle)
    tags = classify(ntitle, has_round=r is not None, has_event_dict=bool(event_tags))
    if r is not None:
        tags.append(f"第{r}回")
    e = EVENT_RE.search(ntitle)
    if e:
        tags.append(e.group(1))
    # 辞書由来のイベント名タグは「スコア大会」動画のときだけ付与する
    # （ガチャ/アリーナ等に季節名が誤爆しないよう限定）。
    if "スコア大会" in tags:
        for t in event_tags:
            if t not in tags:
                tags.append(t)
    return tags


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


def fetch_uploads(channel_id, api_key, all_pages=False):
    """チャンネルのアップロードプレイリスト最新50件を返す。

    アップロードプレイリストIDはチャンネルID先頭の UC を UU に置換したもの。
    channels.list を挟まず playlistItems.list を直接叩ける（1ページ=1クォータ）。
    all_pages=True なら nextPageToken を辿って全アップロードを返す（Phase3 バックフィル用）。
    """
    playlist_id = "UU" + channel_id[2:]
    items = []
    page_token = None
    while True:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("items", []))
        page_token = data.get("nextPageToken")
        if not all_pages or not page_token:
            break
    return items


def build_entry(item, channel_name, now_iso):
    snip = item.get("snippet", {})
    video_id = snip.get("resourceId", {}).get("videoId")
    title = snip.get("title", "")
    description = snip.get("description", "")
    # contentDetails.videoPublishedAt が実際の公開日時。無ければ playlist 追加日時で代替。
    published = item.get("contentDetails", {}).get("videoPublishedAt") or snip.get("publishedAt")

    return {
        "videoId": video_id,
        "title": title,
        "channel": channel_name,
        "description": description,
        "publishedAt": published,
        "registeredAt": now_iso,
        "source": "auto",
        "tags": make_tags(title, description),
        "status": "自動分類",
        "note": "",
    }


def collect(dry_run, backfill=False):
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
            items = fetch_uploads(ch["channelId"], api_key, all_pages=backfill)
        except requests.RequestException as e:
            # あるチャンネルの取得失敗で全体を止めない。
            print(f"[error] {ch['name']} ({ch['channelId']}): {e}", file=sys.stderr)
            continue

        for item in items:
            entry = build_entry(item, ch["name"], now_iso)
            if not entry["videoId"] or entry["videoId"] in existing_ids:
                continue  # 既存 videoId は手動修正保護のためスキップ
            text = norm(entry["title"] + "\n" + entry["description"])
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
    parser.add_argument("--backfill", action="store_true",
                        help="各チャンネルのアップロードを全件辿る（Phase3 過去動画一括登録・ローカル1回実行用）")
    args = parser.parse_args()
    sys.exit(collect(args.dry_run, args.backfill))


if __name__ == "__main__":
    main()

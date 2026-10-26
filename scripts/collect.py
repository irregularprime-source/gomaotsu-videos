#!/usr/bin/env python3
"""ゴ魔乙動画の定期収集スクリプト。

data/channels.json の各チャンネルのアップロード動画から、docs/videos/（年別ファイル）に
未登録のゴ魔乙動画を抽出・自動分類して追記する。

  python scripts/collect.py              # 各チャンネルの最新50件（6hごとcron）
  python scripts/collect.py --backfill   # 各チャンネルのアップロードを全件辿る（ローカル1回実行）
  python scripts/collect.py --backfill --channel UC… --all --after 2015-04-01 --before 2018-09-16
                                         # 1チャンネルだけ、その期間を判定語なしで全件（違う動画は後から除外）
  python scripts/collect.py --dry-run    # 書き込まず追加予定を表示（上のどれにも付けられる）
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import requests

import videos_store

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_PATH = ROOT / "data" / "channels.json"
EVENT_TAGS_PATH = ROOT / "data" / "event_tags.json"

API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
JST = timezone(timedelta(hours=9))

# ゴ魔乙動画の判定語（gomaOnly: false のチャンネル向け）。運用しながら追加しやすいよう定数化。
GOMA_KEYWORDS = ["ゴ魔乙", "ごまおつ", "ゴシックは魔法乙女", "ゴマ乙"]

# --- タグ自動分類の語彙 ---
# Why not「降臨」「復刻」: 発注者の指示によりイベントステージ判定には使わない。
# スコア大会系を示す語（略語含む）。ドヨアタ＝土曜アタック＝週末スコア大会。
SCORE_MARKERS = ["スコア大会", "スコアタ", "ドヨアタ", "どよあた", "ドョアタ", "土アタ",
                 "イベアタ", "記念アタ", "クリスマスアタ"]
# スコア大会の下位分類の判定語。優先順はエーテル→リアル→リーグ→月間→イベント→週末（classify 参照）。
LEAGUE_WORDS = ["リーグ"]
MONTHLY_WORDS = ["更なる高みへ", "さらなる高みへ", "月間スコアタ", "月間スコア大会",
                 "月刊スコアタ", "月間 スコアタ"]  # 月刊・空白入りは 2026-10-26 追加（ユーザー承認）
# 「1月スコアタ」「6月 スコアタ」「7月スコア大会」のような月の呼び方も月間にする（2026-10-20・21 ユーザー指示）。
# 「6月のスコアタ」「○月総合スコアタ」は含めない。
MONTHLY_RE = re.compile(r"(?<!\d)\d{1,2}月 ?スコア(?:タ|大会)")
# 明示的にイベントを示す語。
EVENT_WORDS = ["限定", "記念", "コラボ", "周年", "xmas", "クリスマス"]
# 週末と判定する根拠の語（回数が取れた場合も週末の根拠になる）。
# Why: 以前は「イベント語が無ければ週末」としていたため、弾幕神スコアタ等のイベントが週末に落ちていた。
# 週末は根拠があるときだけにし、根拠の無いスコア動画はイベントにする。
# 「土曜」（土曜日のスコアタ・土曜スコア大会）は 2026-10-26 追加（ユーザー承認）。
WEEKEND_WORDS = ["ドヨアタ", "どよあた", "ドョアタ", "土アタ", "週末", "今週", "土曜"]
# リアルスコア大会の予選。リアル＋イベントの両方に分類し、名前タグは辞書（団体戦予選）で付ける。
# ただし週末の根拠（3桁の回数か週末の語）もあれば週末だけにする（2026-10-15 ユーザー指示）。
# Why: リアル大会の予選ステージが過去のスコアタの流用で、週末の動画と見分けられず目視で処理するため。
# 3桁に限るのは「第3回ごまおつスコア大会 団体戦予選」のような大会自体の開催回を週末にしないため。
REAL_QUALIFIER = "団体戦予選"
# 第1回（2017）・第2回（2021）のリアルスコア大会は「団体戦」の語が無いため、これらの語でもリアルにする
# （2026-10-22 ユーザー指示）。週末の根拠（3桁の回数か週末の語）もあれば週末にする。
# Why not「リアアタ」: 「バリアアタック」に一致するため（リアアタの動画は「団体戦」でも拾える）。
REAL_WORDS = ["リアルスコア", "ごまおつスコア大会"]
WEEKEND_ROUND_MIN = 100
# 「第○回」があってもスコア大会の回数ではないカテゴリ（第42回裏ゴシック道・第34回ギルイベ・アリーナバトル第64回、
# 第2回ギルド実技試験・第60回ギルバト・第14回Gフェスタ、「ガチャに5回挑戦」（2026-10-23 ユーザー承認））。
# タイトルにスコア大会を示す語が無ければ、回数をスコア大会の根拠にしない。
NON_SCORE_ROUND_WORDS = ["ゴシック道", "裏ゴシック", "ギルイベ", "ギルド", "ギルバト", "実技試験", "gフェスタ",
                         "アリーナ", "ガチャ"]
# ギルドバトル(イベント)の判定語。ゴシックマーチ・実技試験・Gフェスタはギルドのイベント名（題名に「ギルイベ」が
# 無いものがある）。「ギルドイベ」は「ギルドイベント」と「ギルドイベ光有利」の書き方の両方に一致させる（2026-10-23 ユーザー指示）。
GUILD_EVENT_MARKERS = ["ギルイベ", "ギルドイベ", "ゴシックマーチ", "実技試験", "gフェスタ"]
# ギルドバトル(通常)の対戦名。明示語（ギルドバトル/ギルバト）に加え、属性有利ローテ
# （旧/新/三 × 火水風光闇）と闘技場マップ名を拾う。ただし「スコア大会」が付いた動画には
# 付けない（classify のガード参照）。Why「新火有利」だけ有利付き: 「新火」単体は
# スコア大会動画の武器名「新火鉢」に衝突するため。
GUILD_NORMAL_MARKERS = [
    "ギルドバトル", "ギルバト",
    "旧水", "旧風", "旧火", "旧光", "旧闇",
    "新水", "新風", "新光", "新闇", "新火有利",
    "三水有利", "三風有利", "三火有利", "三光有利", "三闇有利", "三色",
    "闘技場",
]
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
# 「回」が付かない書き方（第538 / D568 / 本戦482 / ゴ魔乙530）は3桁に限り、直後が単位なら回数にしない。
_NOT_SCORE_UNIT = r"(?![\d.,]*\s*(?:万|億|m|k|点|円|%|位))"
ROUND_PATTERNS = [
    re.compile(r"第(\d+)回"),
    # 「1日1回」「2回被弾」「被弾2回」「5回収」等は回数ではない（(?<!\d) は「被弾12回」の「2」だけ拾うのを防ぐ）
    re.compile(r"(?<!日)(?<!被弾)(?<!\d)(\d+)\s*回(?!被弾|くらい|ぐらい|ほど|目|収)"),
    re.compile(r"(\d+)\s*かい"),
    re.compile(r"(?:ドヨアタ|どよあた|ドョアタ|土アタ)\s*(\d+)"),
    re.compile(r"(\d+)(?=スコアタ|ドヨアタ|どよあた|ドョアタ)"),
    re.compile(r"第\s*(\d{3})(?!\d)" + _NOT_SCORE_UNIT),
    re.compile(r"(?<![a-z0-9])d(\d{3})(?!\d)" + _NOT_SCORE_UNIT),
    re.compile(r"(?:本戦|復習|予習)\s*(\d{3})(?!\d)" + _NOT_SCORE_UNIT),
    re.compile(r"ゴ魔乙\s*(\d{3})(?!\d)" + _NOT_SCORE_UNIT),
    # 「スコアタ250ダチュ杯」「スコア大会438」「182スコア大会」も3桁なら回数（2026-10-26 ユーザー承認）。
    # 直後が「,」「.」なら「スコアタ 187,247,891」のような点数なので回数にしない。
    re.compile(r"(?:スコアタ|スコア大会)\s*(\d{3})(?![\d,.])" + _NOT_SCORE_UNIT),
    re.compile(r"(?<![\d,.])(\d{3})(?=\s*スコア大会)"),
]
# イベント名の簡易抽出：「○○限定」形式のみ拾う。
# Why not: タイトル書式が不揃いで、これ以外の形（接頭辞なしのイベント名等）は誤抽出が多いため対象外。
EVENT_RE = re.compile(r"([一-鿿ぁ-んァ-ヿー々〆]+)限定")


def load_event_tags():
    """スコア大会(イベント)のイベント名辞書を読み、
    ([(tag, [正規化済みkeyword, ...]), ...], [スコア大会の根拠にする正規化済みkeyword, ...],
     {『○○限定』の○○の表記ゆれ: 寄せる名前}, {『○○限定スコアタ』を付けない○○}) を返す。
    "score": true のエントリ（ゴライコウ襲来など「スコアタ」の語が付かないイベント名）は、
    keyword 自体をスコア大会の根拠にする。
    『○○限定』形式は EVENT_RE が自動抽出するため辞書には入れない（重複回避）。"""
    data = json.loads(EVENT_TAGS_PATH.read_text(encoding="utf-8"))
    result, score_keywords = [], []
    for ev in data.get("events", []):
        tag = ev.get("tag")
        kws = [norm(k) for k in ev.get("keywords", []) if k]
        if tag and kws:
            result.append((tag, kws))
            if ev.get("score") is True:
                score_keywords.extend(kws)
    aliases = {norm(k): v for k, v in data.get("limited_aliases", {}).items() if not k.startswith("_")}
    no_score_tag = {norm(n) for n in data.get("limited_no_score_tag", [])}
    return result, score_keywords, aliases, no_score_tag


# イベント名辞書（モジュール読込時に1回だけロード。reclassify も import 経由で共用）。
EVENT_TAGS, EVENT_SCORE_KEYWORDS, LIMITED_ALIASES, LIMITED_NO_SCORE_TAG = load_event_tags()


def limited_name(ntitle):
    """『○○限定』の○○（表記ゆれは辞書の limited_aliases で寄せる）。無ければ None。"""
    e = EVENT_RE.search(ntitle)
    if e is None:
        return None
    return LIMITED_ALIASES.get(e.group(1), e.group(1))


def event_name_tags(ntitle):
    """スコア大会(イベント)の動画に付ける名前タグ（○○・○○限定スコアタ・辞書の一致）を重複排除で返す。
    『○○限定』のイベントには「○○限定スコアタ」も表示する（2026-10-16 ユーザー指示。属性限定などは除く）。"""
    names = []
    name = limited_name(ntitle)
    if name:
        names.append(name)
        if name not in LIMITED_NO_SCORE_TAG:
            names.append(f"{name}限定スコアタ")
    for t in match_event_tags(ntitle):
        if t not in names:
            names.append(t)
    return names


def match_event_tags(ntitle):
    """正規化タイトルが辞書に一致したイベント名タグを、辞書順・重複排除で返す。"""
    matched = []
    for tag, kws in EVENT_TAGS:
        if tag not in matched and any(k in ntitle for k in kws):
            matched.append(tag)
    return matched


def classify(ntitle, has_round=False, round_no=None):
    """正規化タイトルからカテゴリタグ一覧を返す。該当なしは ['未分類']。
    週末/イベントの判別は、説明文の別動画への言及を拾わないようタイトルのみで行う。
    has_round=True（回数「第○回」が取れた）はそれ自体を週末スコア大会の判定材料にする
    （「第579回 9,903万」のようにスコアタ表記が無くても回数付きは定期スコア大会のため）。
    回数はイベント名辞書の一致より優先する（週末の動画にも武器名「HYCレーザー」等が出るため）。
    ただし回数の直後が辞書の語なら、extract_round の段階で回数にしない（イベントの開催回）。
    「団体戦予選」はリアル＋イベントの両方にする。週末の根拠（round_no が3桁以上か週末の語）も
    あれば週末だけにする（REAL_QUALIFIER 参照）。"""
    tags = []
    has_score_marker = (any(norm(m) in ntitle for m in SCORE_MARKERS)
                        or any(k in ntitle for k in EVENT_SCORE_KEYWORDS))
    if has_round and not has_score_marker and any(norm(w) in ntitle for w in NON_SCORE_ROUND_WORDS):
        has_round = False

    # スコア大会ファミリー：親「スコア大会」＋下位1つ（エーテル/リアル/リーグ/月間/イベント/週末）
    is_ether = norm("エーテルスコア") in ntitle
    has_weekend_evidence = ((round_no is not None and round_no >= WEEKEND_ROUND_MIN)
                            or any(norm(w) in ntitle for w in WEEKEND_WORDS))
    is_real = (norm("団体戦") in ntitle             # リアルスコア大会
               or (any(norm(w) in ntitle for w in REAL_WORDS) and not has_weekend_evidence))
    is_real_qualifier = norm(REAL_QUALIFIER) in ntitle
    if is_real_qualifier and has_weekend_evidence:
        is_real = is_real_qualifier = False     # 週末の根拠もある → 週末として下へ
    is_league = any(norm(w) in ntitle for w in LEAGUE_WORDS)
    is_monthly = any(norm(w) in ntitle for w in MONTHLY_WORDS) or bool(MONTHLY_RE.search(ntitle))
    is_score = is_ether or is_real or is_league or is_monthly or has_round or has_score_marker
    if is_score:
        tags.append("スコア大会")
        if is_ether:
            tags.append("エーテルスコア大会")
        elif is_real:
            tags.append("リアルスコア大会")
            if is_real_qualifier:
                tags.append("スコア大会(イベント)")
        elif is_league:
            tags.append("スコア大会(リーグ)")
        elif is_monthly:
            tags.append("スコア大会(月間)")
        elif any(norm(w) in ntitle for w in EVENT_WORDS):
            tags.append("スコア大会(イベント)")
        elif has_round or any(norm(w) in ntitle for w in WEEKEND_WORDS):
            tags.append("スコア大会(週末)")
        else:
            tags.append("スコア大会(イベント)")

    # ギルドバトル：イベント（ギルイベ / ギルドイベント / ゴシックマーチ）を通常より優先。
    # 通常は「スコア大会が付かなかった」動画に限定して付与する（属性有利名などが
    # スコア大会動画の別要素に一致しても誤爆させないためのガード）。
    if any(norm(k) in ntitle for k in GUILD_EVENT_MARKERS):
        tags.append("ギルドバトル(イベント)")
    elif "スコア大会" not in tags and any(norm(k) in ntitle for k in GUILD_NORMAL_MARKERS):
        tags.append("ギルドバトル(通常)")

    # 独立カテゴリ
    for tag, kws in SIMPLE_KEYWORDS.items():
        if any(norm(k) in ntitle for k in kws):
            tags.append(tag)

    return tags or ["未分類"]


def _round_match(ntitle):
    for pat in ROUND_PATTERNS:
        m = pat.search(ntitle)
        if m:
            return m
    return None


def extract_round(ntitle):
    """タイトルから回数（整数）を1つ返す。無ければ None。
    回数の直後（空白を挟んでもよい）がイベント名辞書の語なら、イベントの開催回
    （「第2回 コンボブレイクスコアタ」等）なので週末の回数にしない（2026-10-14 ユーザー指示）。"""
    m = _round_match(ntitle)
    if m is None:
        return None
    rest = ntitle[m.end():].lstrip()
    if any(rest.startswith(k) for _, kws in EVENT_TAGS for k in kws):
        return None
    return int(m.group(1))


def make_tags(title, description):
    """1動画に付ける全タグ（カテゴリ＋回数＋イベント名）を返す。build_entry と reclassify で共用。
    分類はタイトル基準（description は収集判定 is_gomaotsu でのみ使う）。"""
    ntitle = norm(title)
    r = extract_round(ntitle)
    tags = classify(ntitle, has_round=r is not None, round_no=r)
    if r is not None:
        tags.append(f"第{r}回")
    name = limited_name(ntitle)
    if name:
        tags.append(name)
    # 辞書由来のイベント名タグと「○○限定スコアタ」は「スコア大会(イベント)」の動画のときだけ付与する
    # （ガチャ/アリーナ等への季節名や、週末の動画への武器名「HYCレーザー」の誤爆を防ぐ）。
    if "スコア大会(イベント)" in tags:
        for t in event_name_tags(ntitle):
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
    return videos_store.load_videos()


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


def is_channel_target(entry):
    """登録チャンネルの動画をゴ魔乙の動画として収集するか。
    タイトルに判定語があれば対象。説明文にしか無い場合は、タイトルがゴ魔乙の分類
    （スコア大会・ギルバト等。未分類以外）に当たるときだけ対象にする。
    Why: 説明文の定型文やハッシュタグにだけ判定語がある別ゲームの動画が紛れ込んでいた。
    タイトルだけにしないのは「第553回 24.5億」のような判定語の無い正しい動画が多いため。"""
    if is_gomaotsu(norm(entry["title"])):
        return True
    return is_gomaotsu(norm(entry["description"])) and entry["tags"] != ["未分類"]


def in_period(published, after=None, before=None):
    """公開日（UTC の YYYY-MM-DD）が after 以上・before 未満か。指定が無い側は制限しない。"""
    day = (published or "")[:10]
    return (after is None or day >= after) and (before is None or day < before)


def collect(dry_run, backfill=False, channel_id=None, take_all=False, after=None, before=None):
    """channel_id を指定するとそのチャンネルだけ、take_all はその回だけ gomaOnly 扱いにする
    （ゴ魔乙の語が無い動画の多いチャンネルを1回だけ全件取り込み、違う動画は後から除外するため。2026-10-26）。
    Why not channels.json の gomaOnly: 立てたままだと定時収集が別ゲームの新着も入れ、除外した動画も戻ってくる。"""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("環境変数 YOUTUBE_API_KEY が未設定です。", file=sys.stderr)
        return 1

    channels = load_channels()
    if channel_id:
        channels = [ch for ch in channels if ch["channelId"] == channel_id]
        if not channels:
            print(f"channels.json に無いチャンネルです: {channel_id}", file=sys.stderr)
            return 1
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
            print(f"[error] {ch['name']} ({ch['channelId']}): {request_error_summary(e)}", file=sys.stderr)
            continue

        for item in items:
            entry = build_entry(item, ch["name"], now_iso)
            if not entry["videoId"] or entry["videoId"] in existing_ids:
                continue  # 既存 videoId は手動修正保護のためスキップ
            if not in_period(entry["publishedAt"], after, before):
                continue
            if not (take_all or ch.get("gomaOnly") or is_channel_target(entry)):
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
    videos_store.save_videos(videos_doc)
    print(f"動画{len(new_entries)}件を追加しました。")
    return 0


def request_error_summary(error):
    """例外に含まれるキー付きURLやレスポンス本文はログに出さない。"""
    status = error.response.status_code if error.response is not None else None
    return f"{type(error).__name__}" + (f" (HTTP {status})" if status is not None else "")


def date_arg(text):
    """YYYY-MM-DD だけを受け付ける。"""
    try:
        date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"日付は YYYY-MM-DD で指定してください: {text!r}")
    if len(text) != 10:
        raise argparse.ArgumentTypeError(f"日付は YYYY-MM-DD で指定してください: {text!r}")
    return text


def channel_arg(text):
    if not (text.startswith("UC") and len(text) == 24):
        raise argparse.ArgumentTypeError(f"チャンネルIDは UC で始まる24文字で指定してください: {text!r}")
    return text


def main():
    parser = argparse.ArgumentParser(description="ゴ魔乙動画の定期収集")
    parser.add_argument("--dry-run", action="store_true",
                        help="動画データを書き換えず、追加予定の動画一覧を表示する")
    parser.add_argument("--backfill", action="store_true",
                        help="各チャンネルのアップロードを全件辿る（Phase3 過去動画一括登録・ローカル1回実行用）")
    parser.add_argument("--channel", type=channel_arg,
                        help="対象を channels.json のこのチャンネルIDだけにする")
    parser.add_argument("--all", action="store_true",
                        help="その回だけ判定語なしで全動画を取り込む（--channel と一緒に使う）")
    parser.add_argument("--after", type=date_arg, help="この日以降に公開された動画だけ（YYYY-MM-DD、UTC）")
    parser.add_argument("--before", type=date_arg, help="この日より前に公開された動画だけ（YYYY-MM-DD、UTC）")
    args = parser.parse_args()
    if args.all and not args.channel:
        parser.error("--all は --channel と一緒に指定してください")
    sys.exit(collect(args.dry_run, args.backfill, args.channel, args.all, args.after, args.before))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""スコア大会(イベント)のイベント名タグを見直すための集計と、確認済みへの名前タグの追加。

data/event_tags.json（イベント名辞書）を定期的に見直すときに使う。既定は表示だけで何も書き換えない。

  python scripts/event_name_report.py           # 集計を表示（辞書の一致数・名前の無いイベント動画・候補）
  python scripts/event_name_report.py --apply   # イベント動画に辞書の名前タグを追加して videos.json に書き込む

--apply は確認済みも含むスコア大会(イベント)の動画に、辞書に一致した名前タグを「追加だけ」する。
分類・状態・ほかのタグは変えず、タグの削除もしない（確認済みはユーザーの判断を保護する方針のため）。
分類そのものの変更は reclassify.py（未確認だけが対象）で行う。
"""
import argparse
import json
import re
import sys
from collections import Counter

from collect import VIDEOS_PATH, EVENT_RE, EVENT_TAGS, match_event_tags, norm

EVENT = "スコア大会(イベント)"
DICT_TAGS = {tag for tag, _ in EVENT_TAGS}
# 「○○スコアタ」「○○アタ」の○○を、辞書に足す候補として数える。
CANDIDATE_RE = re.compile(r"([一-鿿ぁ-んァ-ヿー々a-z0-9・]{2,12}?)(?:スコアタ|スコア大会|アタ)")


def missing_names(video):
    """イベント動画に付いていない、辞書に一致した名前タグ。"""
    return [t for t in match_event_tags(norm(video.get("title", ""))) if t not in video["tags"]]


def has_name(video):
    return any(t in DICT_TAGS for t in video["tags"]) or bool(EVENT_RE.search(norm(video.get("title", ""))))


def report(videos, limit):
    events = [v for v in videos if EVENT in v["tags"]]
    print(f"スコア大会(イベント)の動画: {len(events)}件")

    print("\n## 辞書エントリの一致数（イベント動画 / それ以外。一致0件は最後にまとめる）")
    zero = []
    for tag, kws in EVENT_TAGS:
        hits = [v for v in videos if any(k in norm(v.get("title", "")) for k in kws)]
        if not hits:
            zero.append(tag)
            continue
        ev = sum(EVENT in v["tags"] for v in hits)
        print(f"  {tag}: {ev} / {len(hits) - ev}")
    print(f"  一致0件（{len(zero)}件）: {' / '.join(zero)}")

    adds = [(v, missing_names(v)) for v in events]
    adds = [(v, m) for v, m in adds if m]
    by_status = Counter(v["status"] for v, _ in adds)
    print(f"\n## 辞書の名前タグを追加できるイベント動画: {len(adds)}件 {dict(by_status)}（--apply で追加）")
    for v, m in adds[:limit]:
        print(f"  [{v['status'][:2]}] +{m}  {v['title'][:60]}")

    nameless = [v for v in events if not has_name(v) and not missing_names(v)]
    print(f"\n## 名前の付かないイベント動画: {len(nameless)}件（辞書に足す候補を探す）")
    counts = Counter(m.group(1) for v in nameless for m in CANDIDATE_RE.finditer(norm(v.get("title", ""))))
    print("  「○○スコアタ／○○アタ」の○○: " + ", ".join(f"{k}({n})" for k, n in counts.most_common(30)))
    for v in nameless[:limit]:
        print(f"  [{v['status'][:2]}] {v['title'][:70]}")


def apply(doc):
    changed = 0
    for v in doc["videos"]:
        if EVENT not in v["tags"]:
            continue
        missing = missing_names(v)
        if missing:
            v["tags"].extend(missing)
            changed += 1
    if changed:
        VIDEOS_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{changed}件のイベント動画に名前タグを追加しました。")


def main():
    parser = argparse.ArgumentParser(description="イベント名タグの見直し")
    parser.add_argument("--apply", action="store_true",
                        help="イベント動画に辞書の名前タグを追加して書き込む（追加だけ。削除・分類変更はしない）")
    parser.add_argument("--limit", type=int, default=40, help="一覧に出す件数（既定40）")
    args = parser.parse_args()
    doc = json.loads(VIDEOS_PATH.read_text(encoding="utf-8"))
    if args.apply:
        apply(doc)
    else:
        report(doc["videos"], args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""docs/videos.json から検索エンジン・AIクローラー向けの静的な成果物を生成する。

生成するもの:
  1. docs/index.html の BUILD:STATIC マーカー間に、全動画の静的な一覧 + JSON-LD を差し込む
  2. docs/sitemap.xml

なぜ必要か:
  index.html は videos.json を fetch して JS で描画するため、HTML そのものには
  動画が 1 件も書かれていない。Googlebot は JS を実行するので一応読めるが、
  GPTBot / ClaudeBot / PerplexityBot などの AI クローラーは基本的に JS を実行せず、
  空のページとして扱ってしまう。そこで同じ内容を HTML に直接書き出しておく。

使い方:
  python scripts/build_static.py
収集スクリプト（collect.py / search_collect.py）の後に実行する。
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
VIDEOS_JSON = DOCS / "videos.json"
INDEX_HTML = DOCS / "index.html"
SITEMAP_XML = DOCS / "sitemap.xml"

SITE_URL = "https://irregularprime-source.github.io/gomaotsu-videos/"
SITE_NAME = "ゴ魔乙 動画索引"
SITE_DESC = (
    "ゴシックは魔法乙女（ゴ魔乙）のYouTubeプレイ動画をカテゴリ別に検索できる一覧サイト。"
)

START_MARKER = "<!-- BUILD:STATIC:START"
END_MARKER = "<!-- BUILD:STATIC:END -->"

# JSON-LD の ItemList に載せる件数。全件載せると巨大になるだけで得がないので直近のみ。
JSONLD_ITEMS = 50

JST = timezone(timedelta(hours=9))


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def published_sort_key(v: dict):
    """公開日で降順ソートするためのキー。日付が壊れている動画は末尾に送る。"""
    raw = (v.get("publishedAt") or "").replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def jst_date(v: dict) -> str:
    """公開日を JST の YYYY-MM-DD で返す。"""
    dt = published_sort_key(v)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return ""
    return dt.astimezone(JST).strftime("%Y-%m-%d")


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def group_by_tag(videos: list[dict]) -> dict[str, list[dict]]:
    """タグ見出しごとに動画をまとめる。1本の動画は必ず1つの見出しにだけ現れる。

    「第580回」のような自動採番タグまで見出しにすると数百セクションになるので、
    docs/tags.json に定義された主要タグだけを見出しにする。

    1本が「スコア大会」と「スコア大会(週末)」の両方を持つことがあるため、
    そのまま全タグに載せると同じ動画が何度も出て HTML が 1.8 倍に膨らむ。
    親タグ（他タグの接頭辞になっているもの）を落として最も具体的な 1 つに寄せる。
    各動画のタグは行内に全部書き出しているので、情報は失われない。
    """
    try:
        tags_def = json.loads((DOCS / "tags.json").read_text(encoding="utf-8"))
        main_tags = [t["name"] for t in tags_def.get("tags", [])]
    except (OSError, ValueError, KeyError):
        main_tags = []
    order = {name: i for i, name in enumerate(main_tags)}

    grouped: dict[str, list[dict]] = {name: [] for name in main_tags}
    for v in videos:
        cands = [t for t in (v.get("tags") or []) if t in order]
        if not cands:
            continue
        specific = [
            t for t in cands if not any(o != t and o.startswith(t) for o in cands)
        ]
        grouped[min(specific or cands, key=lambda t: order[t])].append(v)
    return {name: items for name, items in grouped.items() if items}


def render_list(videos: list[dict]) -> str:
    lines = []
    for v in videos:
        title = esc(v.get("title"))
        url = esc(watch_url(v.get("videoId") or ""))
        channel = esc(v.get("channel"))
        date = esc(jst_date(v))
        tags = esc(" / ".join(v.get("tags") or []))
        meta = "　".join(x for x in (channel, date, tags) if x)
        lines.append(
            f'<li><a href="{url}" rel="noopener">{title}</a>'
            f'<span class="si-meta">{meta}</span></li>'
        )
    return "<ul>\n" + "\n".join(lines) + "\n</ul>"


def render_jsonld(videos: list[dict], updated: str) -> str:
    """CollectionPage + ItemList の構造化データ。

    他人の YouTube 動画に VideoObject を付けるのは Google のガイドライン上リスクが
    あるため、あくまで「一覧ページ」としてのマークアップに留める。
    """
    items = [
        {
            "@type": "ListItem",
            "position": i,
            "name": v.get("title") or "",
            "url": watch_url(v.get("videoId") or ""),
        }
        for i, v in enumerate(videos[:JSONLD_ITEMS], start=1)
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": SITE_NAME,
        "alternateName": "ゴシックは魔法乙女 プレイ動画アーカイブ",
        "description": SITE_DESC,
        "url": SITE_URL,
        "inLanguage": "ja",
        "about": {
            "@type": "VideoGame",
            "name": "ゴシックは魔法乙女",
            "alternateName": ["ゴ魔乙", "Gothic wa Mahou Otome"],
        },
        "mainEntity": {
            "@type": "ItemList",
            "name": f"{SITE_NAME} 収録動画",
            "numberOfItems": len(videos),
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": items,
        },
    }
    if updated:
        data["dateModified"] = updated
    body = json.dumps(data, ensure_ascii=False, indent=2)
    # 動画タイトルに "</script>" が含まれると HTML が壊れるので封じる（JSON としては等価）
    body = body.replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{body}\n</script>'


def build_block(videos: list[dict], updated: str) -> str:
    grouped = group_by_tag(videos)
    total = len(videos)
    updated_disp = esc(updated[:10]) if updated else "-"

    parts = [
        '<section id="static-index" aria-label="全動画の索引">',
        "<h2>収録動画の全一覧</h2>",
        f"<p>ゴシックは魔法乙女（ゴ魔乙）のプレイ動画 {total} 件の索引です。"
        f"最終更新 {updated_disp}。"
        "各リンクは YouTube の動画ページへ移動します。</p>",
    ]

    for name, items in grouped.items():
        items = sorted(items, key=published_sort_key, reverse=True)
        parts.append(f"<h2>{esc(name)}（{len(items)} 件）</h2>")
        parts.append(render_list(items))

    # どの主要タグにも属さない動画（未分類など）を取りこぼさない
    covered = {v.get("videoId") for items in grouped.values() for v in items}
    rest = [v for v in videos if v.get("videoId") not in covered]
    if rest:
        parts.append(f"<h2>その他（{len(rest)} 件）</h2>")
        parts.append(render_list(rest))

    parts.append("</section>")
    parts.append(render_jsonld(videos, updated))
    return "\n".join(parts)


def inject(block: str) -> bool:
    """index.html のマーカー間を差し替える。変更があれば True。"""
    src = INDEX_HTML.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?-->" + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    if not pattern.search(src):
        raise SystemExit(
            f"index.html に {START_MARKER} … {END_MARKER} が見つかりません。"
            "マーカーを消してしまっていないか確認してください。"
        )
    head = (
        f"{START_MARKER} この区間は scripts/build_static.py が自動生成します。"
        "手で編集しても次回の収集で上書きされます。 -->"
    )
    new = pattern.sub(lambda _: f"{head}\n{block}\n{END_MARKER}", src, count=1)
    if new == src:
        return False
    INDEX_HTML.write_text(new, encoding="utf-8")
    return True


def build_sitemap(updated: str) -> bool:
    lastmod = (updated or datetime.now(JST).isoformat())[:10]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{SITE_URL}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        "    <changefreq>daily</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    if SITEMAP_XML.exists() and SITEMAP_XML.read_text(encoding="utf-8") == xml:
        return False
    SITEMAP_XML.write_text(xml, encoding="utf-8")
    return True


def main() -> None:
    data = json.loads(VIDEOS_JSON.read_text(encoding="utf-8"))
    videos = sorted(data.get("videos") or [], key=published_sort_key, reverse=True)
    updated = data.get("updated") or ""

    changed_html = inject(build_block(videos, updated))
    changed_map = build_sitemap(updated)

    print(f"静的索引を生成しました: {len(videos)} 件")
    print(f"  index.html : {'更新' if changed_html else '変更なし'}")
    print(f"  sitemap.xml: {'更新' if changed_map else '変更なし'}")


if __name__ == "__main__":
    main()

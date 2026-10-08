"use strict";

/* タグ定義は docs/tags.json から読み込む（タグ追加はデータ編集だけで済む）。
   読めない環境向けのフォールバック定義のみここに残す。 */
const DEFAULT_TAGS = [
  ["スコア大会(週末)",   "#d9a441"],
  ["スコア大会(イベント)","#d4566a"],
  ["エーテルスコア大会", "#4fb8a8"],
  ["アリーナ",           "#5b8dd9"],
  ["ギルドバトル",       "#cf5b4f"],
  ["イベントステージ",   "#58b368"],
  ["メインストーリー",   "#9b6fd4"],
  ["キワメタワー",       "#c76a2e"],
  ["未分類",             "#8a8598"],
];
let TAGS = DEFAULT_TAGS;
let TAG_COLOR = Object.fromEntries(DEFAULT_TAGS);

/* tags.json に無いタグ（第○回・イベント名など）はタグ名から決定的に採色する */
function tagColor(name) {
  if (TAG_COLOR[name]) return TAG_COLOR[name];
  let h = 0;
  for (const c of name) h = (h * 31 + c.codePointAt(0)) % 360;
  return `hsl(${h} 45% 62%)`;
}

/* videos.json が読めない環境（プレビュー等）用のフォールバック */
const FALLBACK = {updated:"", videos:[
  {videoId:"SAMPLE00001",title:"【サンプル】videos.json を読み込めなかったため内蔵サンプルを表示しています",channel:"（フォールバック表示）",description:"GitHub Pages 上では docs/videos.json が自動的に読み込まれます。",publishedAt:"2026-07-18T21:00:00+09:00",registeredAt:"2026-07-20T00:00:00+09:00",source:"manual",tags:["スコア大会(週末)"],status:"確認済み",note:""},
  {videoId:"SAMPLE00002",title:"【サンプル】エーテルスコア大会の例",channel:"（フォールバック表示）",description:"",publishedAt:"2026-07-15T12:00:00+09:00",registeredAt:"2026-07-20T00:00:00+09:00",source:"auto",tags:["エーテルスコア大会"],status:"自動分類",note:""},
  {videoId:"SAMPLE00003",title:"【サンプル】複数タグの例（ギルドバトル＋アリーナ）",channel:"（フォールバック表示）",description:"",publishedAt:"2026-07-10T19:30:00+09:00",registeredAt:"2026-07-20T00:00:00+09:00",source:"auto",tags:["ギルドバトル","アリーナ"],status:"自動分類",note:""},
]};

const PAGE_SIZE = 100; // 段階描画：一度に描画するカード数

const state = {
  videos: [],
  selectedTags: new Set(),
  query: "",
  status: "",
  sortDesc: true,
  dateFrom: null,    // Date（この日を含む）
  dateToEnd: null,   // Date（翌日0時＝この日を含む上限）
  visibleCount: PAGE_SIZE,
};

const $ = (id) => document.getElementById(id);
const norm = (s) => (s || "").normalize("NFKC").toLowerCase();
const fmtDate = (iso) => {
  const d = new Date(iso);
  return isNaN(d) ? "----/--/--"
    : `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")}`;
};
// 公開日時を JST（日本に固定。DSTなしのため常に+9時間）で「YYYY/MM/DD HH:MM」表示する
const fmtDateTime = (iso) => {
  const d = new Date(iso);
  if (isNaN(d)) return "----/--/-- --:--";
  const j = new Date(d.getTime() + (9 * 60 + d.getTimezoneOffset()) * 60000);
  const p = (n) => String(n).padStart(2, "0");
  return `${j.getFullYear()}/${p(j.getMonth()+1)}/${p(j.getDate())} ${p(j.getHours())}:${p(j.getMinutes())}`;
};

async function loadTags() {
  try {
    const res = await fetch("tags.json", {cache:"no-cache"});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (Array.isArray(data.tags) && data.tags.length)
      return data.tags.map(t => [t.name, t.color]);
  } catch (e) { /* フォールバック定義で続行 */ }
  return DEFAULT_TAGS;
}

async function loadData() {
  try {
    const res = await fetch("videos.json", {cache:"no-cache"});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    const box = document.createElement("div");
    box.className = "error-box";
    // 公開サイトの閲覧者向けの文面。ローカル確認の手順は README に書く（閲覧者には BAT が無い）。
    box.textContent = `動画データを読み込めませんでした（${e.message}）。` +
      `時間をおいてページを再読み込みしてください。` +
      `下の「収録動画の全一覧」は表示できます（カード表示は内蔵サンプルです）。`;
    $("error-area").replaceChildren(box);
    // グリッドが本物のデータを描けないので、HTML に埋め込んである静的索引を見せて内容を失わせない
    document.documentElement.classList.remove("js");
    return FALLBACK;
  }
}

function tagCounts() {
  const c = {};
  for (const v of state.videos)
    for (const t of v.tags || []) c[t] = (c[t] || 0) + 1;
  return c;
}

function renderChips() {
  const counts = tagCounts();
  $("tag-chips").innerHTML = "";
  for (const [name] of TAGS) {
    const b = document.createElement("button");
    b.className = "chip";
    b.style.setProperty("--c", TAG_COLOR[name]);
    b.setAttribute("aria-pressed", state.selectedTags.has(name));
    b.textContent = name;
    const count = document.createElement("span");
    count.className = "cnt";
    count.textContent = String(counts[name] || 0);
    b.appendChild(count);
    b.addEventListener("click", () => {
      state.selectedTags.has(name) ? state.selectedTags.delete(name) : state.selectedTags.add(name);
      b.setAttribute("aria-pressed", state.selectedTags.has(name));
      renderList();
    });
    $("tag-chips").appendChild(b);
  }
}

function filtered() {
  const q = norm(state.query);
  return state.videos.filter(v => {
    if (state.selectedTags.size &&
        !(v.tags || []).some(t => state.selectedTags.has(t))) return false;
    if (state.status && v.status !== state.status) return false;
    if (state.dateFrom || state.dateToEnd) {
      const d = new Date(v.publishedAt);
      if (isNaN(d)) return false;
      if (state.dateFrom && d < state.dateFrom) return false;
      if (state.dateToEnd && d >= state.dateToEnd) return false;
    }
    if (q) {
      const hay = norm(`${v.title} ${v.channel} ${v.description} ${v.note}`);
      if (!hay.includes(q)) return false;
    }
    return true;
  }).sort((a, b) => {
    const d = new Date(a.publishedAt) - new Date(b.publishedAt);
    return state.sortDesc ? -d : d;
  });
}

function card(v) {
  const a = document.createElement("a");
  a.className = "card";
  a.href = `https://www.youtube.com/watch?v=${encodeURIComponent(v.videoId)}`;
  a.target = "_blank";
  a.rel = "noopener";

  const thumb = document.createElement("div");
  thumb.className = "thumb";
  const img = document.createElement("img");
  img.loading = "lazy";
  img.alt = "";
  img.src = `https://i.ytimg.com/vi/${encodeURIComponent(v.videoId)}/mqdefault.jpg`;
  img.addEventListener("error", () => {
    img.remove();
    thumb.insertAdjacentHTML("beforeend", `<div class="ph">❖</div>`);
  });
  thumb.appendChild(img);

  const body = document.createElement("div");
  body.className = "card-body";

  const title = document.createElement("div");
  title.className = "card-title";
  title.textContent = v.title;

  const meta = document.createElement("div");
  meta.className = "card-meta";
  const ch = document.createElement("span");
  ch.textContent = v.channel;
  const dt = document.createElement("span");
  dt.className = "date";
  dt.textContent = fmtDateTime(v.publishedAt);
  meta.append(ch, dt);

  const tags = document.createElement("div");
  tags.className = "card-tags";
  for (const t of v.tags || []) {
    const s = document.createElement("span");
    s.className = "tag";
    s.style.setProperty("--c", tagColor(t));
    s.textContent = t;
    tags.appendChild(s);
  }
  if (v.status === "自動分類") {
    const b = document.createElement("span");
    b.className = "badge-unchecked";
    b.textContent = "未確認";
    tags.appendChild(b);
  }

  body.append(title, meta, tags);
  a.append(thumb, body);
  return a;
}

function renderList(keepCount = false) {
  // 絞り込み条件が変わったら先頭から描画し直す。「もっと見る」のときだけ件数を維持して伸ばす。
  if (!keepCount) state.visibleCount = PAGE_SIZE;
  const list = filtered();
  const shown = list.slice(0, state.visibleCount);
  const grid = $("video-grid");
  grid.innerHTML = "";
  for (const v of shown) grid.appendChild(card(v));
  $("hit-count").textContent = list.length;
  $("shown-count").textContent = shown.length;
  $("empty-msg").hidden = list.length > 0;
  const more = $("more-btn");
  more.hidden = list.length <= state.visibleCount;
  if (!more.hidden) more.textContent = `もっと見る（残り ${list.length - state.visibleCount} 件）`;
}

function bindControls() {
  $("search-box").addEventListener("input", e => {
    state.query = e.target.value;
    renderList();
  });
  $("status-filter").addEventListener("change", e => {
    state.status = e.target.value;
    renderList();
  });
  $("sort-btn").addEventListener("click", () => {
    state.sortDesc = !state.sortDesc;
    $("sort-btn").textContent = state.sortDesc ? "公開日 ↓ 新しい順" : "公開日 ↑ 古い順";
    renderList();
  });
  // 日付は JST の日単位で比較する（publishedAt はタイムゾーン付き ISO のため Date 同士で比較できる）
  $("date-from").addEventListener("change", e => {
    state.dateFrom = e.target.value ? new Date(`${e.target.value}T00:00:00+09:00`) : null;
    renderList();
  });
  $("date-to").addEventListener("change", e => {
    state.dateToEnd = e.target.value
      ? new Date(new Date(`${e.target.value}T00:00:00+09:00`).getTime() + 86400000)
      : null;
    renderList();
  });
  $("more-btn").addEventListener("click", () => {
    state.visibleCount += PAGE_SIZE;
    renderList(true);
  });
  $("clear-btn").addEventListener("click", () => {
    state.selectedTags.clear();
    state.query = "";
    state.status = "";
    state.dateFrom = null;
    state.dateToEnd = null;
    $("search-box").value = "";
    $("status-filter").value = "";
    $("date-from").value = "";
    $("date-to").value = "";
    renderChips();
    renderList();
  });
}

(async function init() {
  const [data, tags] = await Promise.all([loadData(), loadTags()]);
  TAGS = tags;
  TAG_COLOR = Object.fromEntries(TAGS);
  state.videos = data.videos || [];
  $("total-count").textContent = state.videos.length;
  $("last-updated").textContent = data.updated ? fmtDate(data.updated) : "-";
  renderChips();
  bindControls();
  renderList();
})();

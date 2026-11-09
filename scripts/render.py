#!/usr/bin/env python3
"""
CSSLTD CYBER BRIEFING — renderer.

Reads data/feed.json (+ optional council intel fragments) and writes index.html:
a single self-contained page with engraved pirate line-art, category columns,
dark-web board, red-team playbook and a live "now" ticker.

Also writes data/intel_summary.json for the weekly digest and a
site/version stamp used by the auto-refresh check.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import art  # noqa: E402
import caricature as caric  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "index.html"

CATEGORY_BLURB = {
    "ransomware": "Crew manifests, leak sites and the people paying the ransom.",
    "darkweb": "Markets, stealer logs, access brokers and the plumbing of the pit.",
    "exploits": "Fresh CVEs, KEV additions and weaponised proof-of-concept.",
    "redteam": "TTPs, tradecraft and the tradecrafters.",
    "actors": "Who did what, to whom, and how much it annoyed them.",
    "defense": "Mitigations, detections and the boring work that actually works.",
    "tooling": "New toys for the rack, the red cell and the basement.",
}

CAT_ORDER = ["ransomware", "darkweb", "exploits", "redteam", "actors", "defense", "tooling"]

CAT_ICON = {
    "ransomware": "hook",
    "darkweb": "tentacle",
    "exploits": "dagger",
    "redteam": "compass",
    "actors": "skull",
    "defense": "shield",
    "tooling": "wrench",
}

CAT_TAG = {
    "ransomware": "EXFIL",
    "darkweb": "PIT",
    "exploits": "CVE",
    "redteam": "TTP",
    "actors": "APT",
    "defense": "HARDEN",
    "tooling": "GEAR",
}


def e(t: str) -> str:
    return html.escape(t or "", quote=True)


def rel(ts: str | None) -> str:
    if not ts:
        return "—"
    try:
        d = dt.datetime.fromisoformat(ts)
    except ValueError:
        return "—"
    delta = dt.datetime.now(dt.timezone.utc) - d
    mins = int(delta.total_seconds() // 60)
    if mins < 1:
        return "now"
    if mins < 60:
        return f"{mins}m"
    if mins < 1440:
        return f"{mins // 60}h"
    return f"{mins // 1440}d"


def ts_fmt(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        d = dt.datetime.fromisoformat(ts).astimezone(dt.timezone.utc)
    except ValueError:
        return ""
    return d.strftime("%d.%m %H:%M UTC")


def pick_summary(it: dict) -> str:
    s = it.get("summary") or ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < 40:
        s = it.get("title", "")
    if len(s) > 300:
        s = s[:297].rstrip() + "…"
    return s


def item_card(it: dict, idx: int) -> str:
    cat = it.get("category", "redteam")
    url = it.get("url", "")
    title = it.get("title", "")
    src = it.get("source", "")
    pub = it.get("published")
    fresh = it.get("age_days", 0) == 0 and it.get("first_seen")
    badge = "NEW" if fresh else "AGAIN"
    face = caric.caricature(it.get("hash", str(idx)), 66, "face")
    return f"""<article class="card" data-cat="{e(cat)}">
  <div class="card-face">{face}</div>
  <div class="card-body">
    <div class="card-top">
      <span class="tag t-{e(cat)}">{e(CAT_TAG.get(cat, "INT"))}</span>
      <span class="meta-src">{e(src)}</span>
      <span class="meta-rel">{e(rel(pub))}</span>
      <span class="badge b-{badge.lower()}">{badge}</span>
    </div>
    <h3 class="card-title"><a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(title)}</a></h3>
    <p class="card-sum">{e(pick_summary(it))}</p>
    <div class="card-foot"><span class="ts">{e(ts_fmt(pub))}</span><a class="src-link" href="{e(url)}" target="_blank" rel="noopener noreferrer">↗ source</a></div>
  </div>
</article>"""


def section(cat_id: str, items: list[dict], limit: int = 12) -> str:
    title = {
        "ransomware": "RANSOMWARE &amp; EXTORTION",
        "darkweb": "DARK WEB UNDERGROUND",
        "exploits": "EXPLOITS &amp; VULNERABILITIES",
        "redteam": "RED TEAM OPS &amp; TACTICS",
        "actors": "THREAT ACTORS &amp; CAMPAIGNS",
        "defense": "DEFENCE &amp; PATCHING",
        "tooling": "TOOLING &amp; RELEASES",
    }[cat_id]
    icon = art.icon(CAT_ICON[cat_id], 58, "ic sec-ic")
    blurb = CATEGORY_BLURB[cat_id]
    cards = "\n".join(item_card(it, i) for i, it in enumerate(items[:limit]))
    if not cards:
        cards = '<p class="empty">Nothing on the radar today. Even the sea is quiet.</p>'
    # section portrait — a distinct face for every category
    face = caric.caricature(f"cat:{cat_id}", 128, "cat-face")
    crew = "".join(caric.caricature(f"cat:{cat_id}:crew{i}", 54, "crew-face") for i in range(5))
    return f"""<section class="cat" id="cat-{e(cat_id)}">
  <header class="cat-head">
    <div class="cat-ic">{icon}</div>
    <div class="cat-tt"><h2>{title}</h2><p class="cat-blurb">{e(blurb)}</p></div>
    <div class="cat-count"><span>{len(items)}</span><small>items</small></div>
    <div class="cat-face">{face}</div>
  </header>
  <div class="crew-strip">{crew}<span class="crew-lbl">the crew on watch</span></div>
  <div class="grid">
{cards}
  </div>
</section>"""


def darkweb_board(items: list[dict]) -> str:
    rows = []
    for it in items[:24]:
        extra = it.get("extra") or {}
        grp = extra.get("group", "")
        ctry = extra.get("country", "")
        rows.append(
            f"""<tr>
  <td class="dv-g">{e(grp or it.get('source',''))}</td>
  <td><a href="{e(it.get('url',''))}" target="_blank" rel="noopener noreferrer">{e(it.get('title',''))}</a></td>
  <td class="dv-c">{e(ctry)}</td>
  <td class="dv-d">{e(rel(it.get('published')))}</td>
</tr>"""
        )
    if not rows:
        rows.append('<tr><td colspan="4" class="empty">No fresh leak-site manifests this cycle.</td></tr>')
    return "\n".join(rows)


def intel_card(f: dict) -> str:
    """A council finding — the agent's own pick, marked as such."""
    cat = f.get("beat", "redteam")
    face = caric.caricature(f"intel:{f.get('hash','')}", 74, "face")
    return f"""<article class="card intel-card" data-cat="{e(cat)}">
  <div class="card-face">{face}</div>
  <div class="card-body">
    <div class="card-top">
      <span class="tag t-{e(cat)}">{e(f.get('ticker',''))}</span>
      <span class="who">{e(f.get('agent','').upper())}</span>
      <span class="meta-src">{e(f.get('source',''))}</span>
      <span class="badge b-new">UNIQUE</span>
    </div>
    <h3 class="card-title"><a href="{e(f.get('url',''))}" target="_blank" rel="noopener noreferrer">{e(f.get('title',''))}</a></h3>
    <p class="card-sum">{e(f.get('comment',''))}</p>
    <div class="card-foot"><span class="ts">{e(f.get('date',''))}</span><a class="src-link" href="{e(f.get('url',''))}" target="_blank" rel="noopener noreferrer">↗ source</a></div>
  </div>
</article>"""


def council_block(intel: list[dict]) -> str:
    """Council agent findings — the human-ish layer on top of the feed."""
    if not intel:
        return ""
    cards = "\n".join(intel_card(f) for f in intel)
    return f"""<section class="council" id="council">
  <h2 class="sec-title">THE COUNCIL&rsquo;S PICKS</h2>
  <p class="sec-sub">ATHENA on ransomware, VULCAN on exploits, IRIS on the pit, PROMETHEUS on the crews &mdash; findings they dug up themselves, de-duplicated against everything else on this page, and each one carries a link that actually resolves.</p>
  <div class="grid">
{cards}
  </div>
</section>"""


def ticker(items: list[dict]) -> str:
    picks = []
    for it in items[:22]:
        t = re.sub(r"\s+", " ", it.get("title", ""))
        picks.append(f"{e(it.get('source',''))} :: {e(t)}")
    if not picks:
        picks = ["no intel on the radar"]
    body = "   ///   ".join(picks)
    return f"""<div class="ticker-wrap"><div class="ticker"><span class="tk-label">LIVE FEED</span><div class="tk-track"><div class="tk-inner">{body}   ///   {body}</div></div></div></div>"""


CSS = r"""
:root{
  --ink:#efe6d4; --ink-dim:#a9a08c; --ink-faint:#5d5a50;
  --bg:#07090c; --bg2:#0c1016; --card:#111722; --card2:#0d141d;
  --crimson:#c0392b; --gold:#d8a54a; --sea:#4fa8a0; --violet:#8b6fc4;
  --line:#1e2734; --line2:#2a3546;
  --mono:"JetBrains Mono","IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --serif:"Cormorant Garamond","Iowan Old Style","Palatino Linotype",Georgia,serif;
  --disp:"Pirata One","UnifrakturMaguntia","Cinzel Decorative",Georgia,serif;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:
    radial-gradient(1200px 700px at 12% -10%, #131c28 0%, transparent 60%),
    radial-gradient(900px 600px at 92% 4%, #1a1410 0%, transparent 55%),
    var(--bg);
  color:var(--ink);
  font-family:var(--mono);
  font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
  overflow-x:hidden;
}
body::before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:999;
  background:repeating-linear-gradient(0deg, rgba(255,255,255,.018) 0 1px, transparent 1px 3px);
  mix-blend-mode:overlay;
}
body::after{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:998;
  background:radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.55) 100%);
}
a{color:inherit}
.wrap{max-width:1280px;margin:0 auto;padding:0 22px 90px;position:relative;z-index:2}
.wm{position:fixed;right:-40px;top:120px;width:520px;height:520px;z-index:0;pointer-events:none;opacity:.5}

/* ---------------- header */
header.top{
  position:relative; z-index:3; padding:34px 0 8px;
  border-bottom:1px solid var(--line);
  display:grid; grid-template-columns:1fr auto; gap:20px; align-items:end;
}
.brand{display:flex; align-items:center; gap:16px}
.brand-mark{width:76px;height:76px;flex:0 0 auto;filter:drop-shadow(0 0 14px rgba(192,57,43,.35))}
.brand h1{
  font-family:var(--disp); font-size:clamp(30px,5.2vw,60px); margin:0; letter-spacing:.5px;
  color:var(--ink); text-shadow:0 2px 0 #000, 0 0 26px rgba(216,165,74,.22);
}
.brand h1 .tlde{color:var(--crimson)}
.brand .sub{font-size:12px; letter-spacing:.32em; color:var(--ink-dim); text-transform:uppercase; margin-top:6px}
.edition{text-align:right;font-size:12px;color:var(--ink-dim);letter-spacing:.12em}
.edition b{color:var(--gold);font-size:15px;display:block;letter-spacing:.06em}
.chip{
  display:inline-block;border:1px solid var(--line2);background:var(--card2);
  color:var(--ink-dim);padding:3px 9px;border-radius:2px;margin:4px 0 0 6px;font-size:11px;
}
.chip.live{border-color:#245c3a;color:#7ee787}
.chip.live::before{content:"●";color:#7ee787;margin-right:5px;animation:blink 1.6s infinite}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:.15}}

/* ---------------- ticker */
.ticker-wrap{margin:18px 0 6px;border:1px solid var(--line);background:linear-gradient(180deg,#0a0e14,#070a0f);overflow:hidden}
.ticker{display:flex;align-items:stretch}
.tk-label{
  flex:0 0 auto;padding:7px 12px;font-size:11px;letter-spacing:.2em;color:#0b0d10;
  background:linear-gradient(180deg,var(--crimson),#8f2a20);font-weight:700;
}
.tk-track{overflow:hidden;flex:1}
.tk-inner{white-space:nowrap;padding:7px 0;font-size:12px;color:var(--ink-dim);animation:scroll 64s linear infinite}
.tk-inner:hover{animation-play-state:paused}
@keyframes scroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* ---------------- hero */
.hero{position:relative;margin:26px 0 8px;border:1px solid var(--line);background:linear-gradient(160deg,#0b1017 0%,#080b10 60%,#100c0a 100%);overflow:hidden}
.hero-art{display:block;width:100%;height:auto}
.hero-copy{
  position:absolute;left:26px;top:24px;max-width:430px;
}
.hero-copy h2{font-family:var(--serif);font-size:clamp(22px,3vw,34px);margin:0 0 10px;color:var(--ink);font-style:italic}
.hero-copy p{color:var(--ink-dim);font-size:13px;margin:0 0 14px;max-width:400px}
.kpis{display:flex;gap:10px;flex-wrap:wrap}
.kpi{border:1px solid var(--line2);background:rgba(10,14,20,.82);padding:9px 13px;min-width:104px}
.kpi b{display:block;font-size:24px;color:var(--gold);line-height:1.1}
.kpi span{font-size:10px;letter-spacing:.18em;color:var(--ink-dim);text-transform:uppercase}
.kpi.c b{color:var(--crimson)} .kpi.s b{color:var(--sea)} .kpi.v b{color:var(--violet)}

/* ---------------- nav */
nav.catnav{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 8px}
nav.catnav a{
  text-decoration:none;border:1px solid var(--line2);padding:7px 12px;font-size:12px;
  letter-spacing:.12em;color:var(--ink-dim);background:var(--card2);transition:.15s;
}
nav.catnav a:hover{color:var(--ink);border-color:var(--gold);background:#141a24;transform:translateY(-1px)}
nav.catnav a span{color:var(--gold)}

/* ---------------- sections */
section.cat{margin:38px 0 0;scroll-margin-top:20px}
.cat-head{display:flex;align-items:center;gap:16px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:16px}
.sec-ic{width:58px;height:58px;flex:0 0 auto;filter:drop-shadow(0 0 10px rgba(0,0,0,.6))}
.cat-tt h2{font-family:var(--disp);font-size:clamp(20px,2.6vw,30px);margin:0;letter-spacing:.5px;color:var(--ink)}
.cat-blurb{margin:2px 0 0;color:var(--ink-dim);font-size:12.5px;font-style:italic}
.cat-count{margin-left:auto;text-align:right;color:var(--gold);font-family:var(--disp)}
.cat-count span{font-size:30px;display:block;line-height:1}
.cat-count small{font-size:10px;letter-spacing:.2em;color:var(--ink-dim);font-family:var(--mono);text-transform:uppercase}
.cat-face{flex:0 0 auto;opacity:.9;filter:drop-shadow(0 6px 16px rgba(0,0,0,.65))}
.cat-face .cat-face{width:128px;height:128px}
.crew-strip{display:flex;align-items:center;gap:8px;margin:-4px 0 14px;opacity:.5;flex-wrap:wrap}
.crew-strip .crew-face{width:44px;height:44px}
.crew-lbl{font-size:10px;letter-spacing:.24em;color:var(--ink-dim);text-transform:uppercase;margin-left:4px}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px}
.card{
  border:1px solid var(--line);background:linear-gradient(180deg,var(--card),var(--card2));
  padding:13px 15px 12px;position:relative;transition:.16s;overflow:hidden;
  display:grid;grid-template-columns:66px 1fr;gap:13px;align-items:start;
}
.card-face{opacity:.95;filter:drop-shadow(0 4px 10px rgba(0,0,0,.6))}
.card-face .face{width:66px;height:66px}
.card-body{min-width:0}
.card::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:2px;background:var(--crimson);opacity:.65;
}
.card[data-cat="darkweb"]::before{background:var(--violet)}
.card[data-cat="exploits"]::before{background:var(--gold)}
.card[data-cat="redteam"]::before{background:var(--sea)}
.card[data-cat="actors"]::before{background:#b5651d}
.card[data-cat="defense"]::before{background:#4c8eda}
.card[data-cat="tooling"]::before{background:#8a8f98}
.card:hover{border-color:var(--line2);transform:translateY(-2px);box-shadow:0 14px 34px rgba(0,0,0,.55)}
.card-top{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.tag{font-size:10px;letter-spacing:.16em;padding:2px 7px;border:1px solid currentColor;color:var(--gold);border-radius:2px}
.t-darkweb{color:var(--violet)} .t-exploits{color:var(--gold)} .t-redteam{color:var(--sea)}
.t-actors{color:#b5651d} .t-defense{color:#4c8eda} .t-tooling{color:#8a8f98}
.stampwrap{margin-left:auto;opacity:.85}
.stamp{width:34px;height:34px}
.meta-src{font-size:11px;color:var(--ink-dim);letter-spacing:.06em}
.meta-rel{font-size:11px;color:var(--gold)}
.badge{font-size:9.5px;letter-spacing:.16em;padding:2px 6px;border:1px solid var(--line2);color:var(--ink-dim)}
.b-new{border-color:#245c3a;color:#7ee787;background:rgba(46,160,67,.08)}
.b-again{border-color:#4a3a1c;color:var(--gold)}
.card-title{font-family:var(--serif);font-size:18.5px;line-height:1.28;margin:0 0 7px;font-weight:600}
.card-title a{text-decoration:none;color:var(--ink);background-image:linear-gradient(var(--crimson),var(--crimson));background-size:0 1px;background-repeat:no-repeat;background-position:0 100%;transition:.2s}
.card-title a:hover{color:#fff;background-size:100% 1px}
.card-sum{margin:0;color:var(--ink-dim);font-size:12.8px;line-height:1.5}
.card-foot{display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding-top:8px;border-top:1px dashed var(--line);font-size:10.5px;color:var(--ink-dim)}
.src-link{color:var(--sea);text-decoration:none;letter-spacing:.1em}
.src-link:hover{text-decoration:underline;color:#7fd6ce}
.empty{color:var(--ink-dim);font-style:italic;padding:20px;border:1px dashed var(--line)}

/* ---------------- dark web board */
.board{margin:26px 0 0;border:1px solid var(--line);background:linear-gradient(180deg,#0e1119,#080b11)}
.board-head{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line);background:#0a0d14}
.board-head h3{margin:0;font-family:var(--disp);font-size:20px;letter-spacing:.5px}
.board-head .dot{width:9px;height:9px;border-radius:50%;background:var(--crimson);box-shadow:0 0 12px var(--crimson);animation:blink 1.4s infinite}
.board-head p{margin:0;font-size:11.5px;color:var(--ink-dim);letter-spacing:.08em}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:8px 16px;border-bottom:1px solid #131a25}
th{font-size:10px;letter-spacing:.2em;color:var(--ink-dim);text-transform:uppercase;background:#0a0e15}
tbody tr:hover{background:#0f141d}
td a{text-decoration:none;color:var(--ink)}
td a:hover{color:var(--gold)}
.dv-g{color:var(--crimson);font-weight:700;letter-spacing:.08em;width:140px}
.dv-c{color:var(--sea);width:70px;text-align:center}
.dv-d{color:var(--ink-dim);width:70px;text-align:right}

/* ---------------- council */
.council{margin:44px 0 0}
.sec-title{font-family:var(--disp);font-size:clamp(22px,3vw,34px);margin:0;letter-spacing:.5px}
.sec-sub{color:var(--ink-dim);font-size:13px;margin:4px 0 16px;font-style:italic;max-width:900px}
.intel-card{border-color:#2c3a2e;background:linear-gradient(180deg,#0f1519,#0b1015)}
.intel-card::before{background:var(--gold);opacity:.8}
.intel-card .who{font-size:9.5px;letter-spacing:.2em;color:var(--gold);border:1px solid #4a3a1c;padding:1px 6px}
.council-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:13px}
.council-card{border:1px solid var(--line);background:var(--card2);padding:14px}
.cc-name{font-size:10px;letter-spacing:.24em;color:var(--gold)}
.cc-head{font-family:var(--serif);font-size:17px;margin:4px 0 7px;color:var(--ink)}
.cc-body{font-size:12.6px;color:var(--ink-dim);margin:0;line-height:1.55}

/* ---------------- footer */
footer.bot{margin:54px 0 0;border-top:1px solid var(--line);padding-top:18px;color:var(--ink-dim);font-size:12px;display:grid;grid-template-columns:1fr 1fr;gap:18px}
footer.bot .sig{text-align:right}
footer.bot a{color:var(--sea)}
.note{font-size:11.5px;color:#6f6a5e;font-style:italic;margin-top:6px}
.ascii{font-size:10px;color:#3d4350;white-space:pre;line-height:1.15;margin:8px 0 0}
@media (max-width:760px){
  header.top{grid-template-columns:1fr}
  .edition{text-align:left}
  .hero-copy{position:static;padding:18px}
  footer.bot{grid-template-columns:1fr}
  .sig{text-align:left !important}
}
"""


def build(feed: dict, intel: list[dict]) -> str:
    buckets = feed.get("buckets", {})
    cats = feed.get("categories", [])
    all_items: list[dict] = []
    for c in CAT_ORDER:
        all_items.extend(buckets.get(c, []))
    all_items.sort(key=lambda x: x.get("published") or "", reverse=True)

    gen = feed.get("generated")
    gdt = dt.datetime.fromisoformat(gen) if gen else dt.datetime.now(dt.timezone.utc)
    newn = feed.get("new_count", 0)
    total = feed.get("total", len(all_items))

    secs = "\n".join(section(c, buckets.get(c, []), limit=12) for c in CAT_ORDER)

    nav = "\n".join(
        f'<a href="#cat-{c}">{CATEGORY_BLURB and CAT_TAG.get(c,"INT")} {c.upper()}<span> {len(buckets.get(c,[]))}</span></a>'
        for c in CAT_ORDER
    )

    kpis = f"""<div class="kpis">
  <div class="kpi c"><b>{newn}</b><span>fresh finds</span></div>
  <div class="kpi"><b>{total}</b><span>items scanned</span></div>
  <div class="kpi s"><b>{len(buckets.get('darkweb',[]))}</b><span>dark web leads</span></div>
  <div class="kpi v"><b>{len(buckets.get('redteam',[]))}</b><span>red team tips</span></div>
</div>"""

    board = f"""<section class="board" id="board">
  <div class="board-head">
    <span class="dot"></span>
    <h3>LEAK-SITE BOARD</h3>
    <p>fresh manifests scraped from crew sites &amp; trackers — every row is a company that learned the hard way</p>
  </div>
  <table>
    <thead><tr><th>CREW</th><th>CLAIM</th><th>GEO</th><th>AGE</th></tr></thead>
    <tbody>
{darkweb_board(buckets.get('ransomware', []))}
    </tbody>
  </table>
</section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DAILY CYBER BRIEFING — the pirate's take</title>
<meta name="description" content="Daily cyber security and red team briefing with a pirate's eye: ransomware, dark web underground, exploits, TTPs and the crews who keep breaking things.">
<meta property="og:title" content="DAILY CYBER BRIEFING">
<meta property="og:description" content="Ransomware, dark web, exploits and red team tradecraft — daily, with a pirate's eye.">
<meta property="og:type" content="website">
<meta http-equiv="refresh" content="3600">
<style>{CSS}</style>
</head>
<body>
{art.watermark()}
<div class="wrap">

<header class="top">
  <div class="brand">
    <div class="brand-mark">{art.icon('skull', 76, 'ic')}</div>
    <div>
      <h1>DAILY CYBER <span class="tlde">BRIEFING</span></h1>
      <div class="sub">cybersecurity &amp; red team · with a pirate's eye</div>
    </div>
  </div>
  <div class="edition">
    <b>{gdt.strftime('%A %d %B %Y')}</b>
    <span>issue no. {gdt.strftime('%j')}-{gdt.strftime('%Y')}</span><br>
    <span class="chip live">AUTO-REFRESH</span>
    <span class="chip">WEEKLY DEEP DIVE</span>
  </div>
</header>

{ticker(all_items)}

<section class="hero">
  {art.hero_svg()}
  <div class="hero-copy">
    <h2>Ahoy, security folk.</h2>
    <p>Another day, another set of crews sailing straight into the same reef. Here is what the water looks like: what got breached, what got weaponised, what the pit is selling, and what you should patch before someone else does it for you.</p>
    {kpis}
  </div>
</section>

<nav class="catnav">
{nav}
  <a href="#board">LEAK-SITE BOARD</a>
  <a href="#council">THE COUNCIL</a>
</nav>

{secs}

{board}

{council_block(intel)}

<footer class="bot">
  <div>
    <strong>DAILY CYBER BRIEFING</strong> — assembled by the CSSLTD agent council from public RSS, vendor advisories, CVE feeds and crew leak-site trackers.
    <div class="note">Every item is linked to its origin. Nothing is paraphrased beyond the source headline; the commentary is ours, the facts are theirs.</div>
    <pre class="ascii">{art.ascii_banner()}</pre>
  </div>
  <div class="sig">
    <div>generated {gdt.strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div>next issue 08:00 · self-updating weekly</div>
    <div><a href="https://github.com/zi3lak/cyber-briefing">source @ github</a></div>
  </div>
</footer>

</div>
</body>
</html>"""


def main() -> int:
    feed_path = DATA / "feed.json"
    if not feed_path.exists():
        print("no data/feed.json — run collect.py first", file=sys.stderr)
        return 1
    feed = json.loads(feed_path.read_text())

    intel: list[dict] = []
    intel_path = DATA / "intel.json"
    if intel_path.exists():
        try:
            intel = json.loads(intel_path.read_text()).get("findings", [])
        except Exception:
            intel = []

    page = build(feed, intel)
    OUT.write_text(page, encoding="utf-8")
    (DATA / "intel_summary.json").write_text(
        json.dumps({"generated": feed.get("generated"), "findings": len(intel)}, indent=1)
    )
    print(f"index.html written: {len(page):,} bytes, council findings: {len(intel)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

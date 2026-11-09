#!/usr/bin/env python3
"""
CSSLTD DAILY CYBER BRIEFING — collector.

Pulls from public RSS/API endpoints, normalises every item, hashes it for
cross-run uniqueness, buckets it into editorial categories, and writes:

    data/feed.json          latest items (feeds + APIs only)
    data/archive/YYYY-MM-DD.json   snapshot for that run
    data/history.json       {hash: first_seen_iso, first_seen_date} — grows forever
    data/state.json         run metadata (counts, sources, errors)

Pure stdlib. No secrets. Safe to run from GitHub Actions.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARCHIVE = DATA / "archive"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")
STALE_LIMIT = int(os.environ.get("BRIEFING_MAX_AGE_H", "96"))

# ---------------------------------------------------------------- categories
CATEGORIES = [
    {
        "id": "ransomware",
        "title": "RANSOMWARE & EXTORTION",
        "icon": "hook",
        "blurb": "Crew manifests, leak sites and the people paying the ransom.",
    },
    {
        "id": "darkweb",
        "title": "DARK WEB UNDERGROUND",
        "icon": "tentacle",
        "blurb": "Markets, stealer logs, access brokers and the plumbing of the pit.",
    },
    {
        "id": "exploits",
        "title": "EXPLOITS & VULNERABILITIES",
        "icon": "dagger",
        "blurb": "Fresh CVEs, KEV additions and weaponised proof-of-concept.",
    },
    {
        "id": "redteam",
        "title": "RED TEAM OPS & TACTICS",
        "icon": "compass",
        "blurb": "TTPs, tradecraft and the tradecrafters.",
    },
    {
        "id": "actors",
        "title": "THREAT ACTORS & CAMPAIGNS",
        "icon": "skull",
        "blurb": "Who did what, to whom, and how much it annoyed them.",
    },
    {
        "id": "defense",
        "title": "DEFENCE & PATCHING",
        "icon": "shield",
        "blurb": "Mitigations, detections and the boring work that actually works.",
    },
    {
        "id": "tooling",
        "title": "TOOLING & RELEASES",
        "icon": "wrench",
        "blurb": "New toys for the rack, the red cell and the basement.",
    },
]

RULES = [
    # (regex, category id)
    (r"ransom|ransomware|extortion|lock ?bit|blackcat|akira|clop|play|medusa|qilin|locker|leak site|data breach|victim", "ransomware"),
    (r"dark ?web|darknet|onion|tor |tor\b|marketplace|broker|stolen (data|credential)|infostealer|stealer|carding|carded|market share|initial access|broker", "darkweb"),
    (r"cve-|exploit|poc\b|proof.of.concept|vulnerab|bypass|privilege escalation|rce\b|remote code|0day|zero.day|patch(ed|ing)? vulnerab", "exploits"),
    (r"red team|redteam|pentest|penetration test|offensive|adversary sim|attack simulation|command and control|c2\b|beacon|impersonat|phishing|social engineering|credential|dump|mimikatz|post.?", "redteam"),
    (r"apt\b|apt-|threat actor|campaign|espionage|nation.state|apt29|apt28|lazarus|scattered spider|suspected|attributed", "actors"),
    (r"detection|mitigat|defen[cs]e|mfa\b|2fa|patch tuesday|advisory|hardening|edr|xdr|siem|backup|zero trust|guidance|kev\b", "defense"),
    (r"release|open.?source|toolkit|framework|tool\b|new tool|library|repo|sdk\b|plugin|checker|scanner|fuzzer|framework update", "tooling"),
]
COMPILED = [(re.compile(p, re.I), c) for p, c in RULES]


def categorise(text: str, fallback: str = "redteam") -> str:
    best, best_hits = fallback, 0
    for rx, cat in COMPILED:
        hits = len(rx.findall(text))
        if hits > best_hits:
            best, best_hits = cat, hits
    return best


# ---------------------------------------------------------------- helpers
def fetch(url: str, timeout: int = 25, headers: dict | None = None) -> bytes:
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


def clean(text: str | None, limit: int = 400) -> str:
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", text)
    t = (
        t.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&mdash;", "—")
        .replace("&hellip;", "…")
    )
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        t = t[: limit - 1].rstrip() + "…"
    return t


def norm_title(t: str) -> str:
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def item_hash(title: str, url: str) -> str:
    key = norm_title(title) + "|" + (url or "")
    return hashlib.sha256(key.encode("utf-8", "ignore")).hexdigest()[:16]


def parse_date(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    s = s.strip()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S",
    ):
        try:
            d = dt.datetime.strptime(s, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return d.astimezone(dt.timezone.utc)
        except ValueError:
            continue
    try:  # RFC 822 leftovers
        from email.utils import parsedate_to_datetime

        d = parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


XML_BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
XML_BAD_B = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def parse_xml(raw: bytes):
    """Parse XML, stripping raw control chars some feeds (Rapid7) embed."""
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        try:
            return ET.fromstring(XML_BAD_B.sub(b"", raw))
        except ET.ParseError as e:
            raise e


def rss_items(url: str, source: str, default_cat: str | None = None) -> list[dict]:
    try:
        raw = fetch(url)
    except Exception as e:
        print(f"  ! {source}: {type(e).__name__} {e}", file=sys.stderr)
        return []
    try:
        root = parse_xml(raw)
    except ET.ParseError as e:
        print(f"  ! {source}: bad xml {e}", file=sys.stderr)
        return []

    out: list[dict] = []
    nodes = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for n in nodes:
        def txt(*tags: str) -> str:
            for t in tags:
                el = n.find(t)
                if el is None:
                    el = n.find(f"{{http://www.w3.org/2005/Atom}}{t}")
                if el is not None:
                    if el.text:
                        return el.text
                    href = el.get("href")
                    if href:
                        return href
            return ""

        title = clean(txt("title"), 220)
        link = (txt("link") or txt("guid")).strip()
        desc = clean(txt("description") or txt("summary") or txt("content"), 460)
        date = txt("pubDate") or txt("published") or txt("updated") or txt("date")
        if not title or not link:
            continue
        d = parse_date(date)
        out.append(
            {
                "title": title,
                "url": link,
                "summary": desc,
                "source": source,
                "published": d.isoformat() if d else None,
                "category": categorise(title + " " + desc, default_cat or "redteam"),
                "origin": "feed",
            }
        )
    return out


def google_news(query: str, source: str, default_cat: str) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        raw = fetch(url)
    except Exception as e:
        print(f"  ! {source}: {type(e).__name__} {e}", file=sys.stderr)
        return []
    try:
        root = parse_xml(raw)
    except ET.ParseError:
        return []
    out = []
    for n in root.findall(".//item"):
        title = clean(n.findtext("title"), 220)
        link = (n.findtext("link") or "").strip()
        desc = clean(n.findtext("description"), 460)
        d = parse_date(n.findtext("pubDate"))
        if not title or not link:
            continue
        out.append(
            {
                "title": title,
                "url": link,
                "summary": desc,
                "source": source,
                "published": d.isoformat() if d else None,
                "category": categorise(title + " " + desc, default_cat),
                "origin": "feed",
            }
        )
    return out


# ---------------------------------------------------------------- API collectors
def api_kev() -> list[dict]:
    url = "https://raw.githubusercontent.com/cisagov/kev-data/main/known_exploited_vulnerabilities.json"
    try:
        data = json.loads(fetch(url, timeout=30))
    except Exception as e:
        print(f"  ! KEV: {e}", file=sys.stderr)
        return []
    out = []
    for v in data.get("vulnerabilities", []):
        added = v.get("dateAdded")
        if not added:
            continue
        d = parse_date(added)
        if not d or (NOW - d).days > 30:
            continue
        title = f"KEV: {v.get('cveID')} — {v.get('vendorProject')} {v.get('product')}"
        out.append(
            {
                "title": title,
                "url": v.get("notes", "").split(" ;")[0] or "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                "summary": clean(v.get("shortDescription"), 460)
                + " | ransomware use: "
                + str(v.get("knownRansomwareCampaignUse")),
                "source": "CISA KEV",
                "published": d.isoformat(),
                "category": "exploits",
                "origin": "api",
                "extra": {"due": v.get("dueDate"), "ransom": v.get("knownRansomwareCampaignUse")},
            }
        )
    return out


def api_ghsa() -> list[dict]:
    url = "https://api.github.com/advisories?per_page=40&sort=published&direction=desc"
    try:
        data = json.loads(fetch(url, timeout=30, headers={"Accept": "application/vnd.github+json"}))
    except Exception as e:
        print(f"  ! GHSA: {e}", file=sys.stderr)
        return []
    out = []
    for a in data:
        d = parse_date(a.get("published_at"))
        if not d or (NOW - d).days > 14:
            continue
        summary = clean(a.get("summary"), 220)
        body = clean(a.get("description"), 460)
        out.append(
            {
                "title": f"GHSA {a.get('ghsa_id')}: {summary}",
                "url": a.get("html_url", ""),
                "summary": body,
                "source": "GitHub Advisories",
                "published": d.isoformat(),
                "category": "exploits",
                "origin": "api",
                "extra": {"severity": a.get("severity"), "cve": a.get("cve_id")},
            }
        )
    return out


def api_nvd() -> list[dict]:
    start = (NOW - dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000")
    end = (NOW + dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000")
    url = (
        "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=60"
        f"&pubStartDate={start}&pubEndDate={end}"
    )
    try:
        data = json.loads(fetch(url, timeout=40))
    except Exception as e:
        print(f"  ! NVD: {e}", file=sys.stderr)
        return []
    out = []
    for v in data.get("vulnerabilities", []):
        c = v.get("cve", {})
        desc = ""
        for dd in c.get("descriptions", []):
            if dd.get("lang") == "en":
                desc = dd.get("value", "")
                break
        d = parse_date(c.get("published"))
        if not d:
            continue
        out.append(
            {
                "title": f"{c.get('id')}: {clean(desc, 150)}",
                "url": f"https://nvd.nist.gov/vuln/detail/{c.get('id')}",
                "summary": clean(desc, 460),
                "source": "NVD",
                "published": d.isoformat(),
                "category": "exploits",
                "origin": "api",
            }
        )
    return out


def api_ransomware_live() -> list[dict]:
    url = "https://api.ransomware.live/v2/recentvictims"
    try:
        data = json.loads(fetch(url, timeout=30))
    except Exception as e:
        print(f"  ! ransomware.live: {e}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    out = []
    for v in data[:120]:
        d = parse_date(v.get("discovered") or v.get("attackdate"))
        if not d or (NOW - d).days > 21:
            continue
        group = (v.get("group") or "unattributed").upper()
        dom = v.get("domain") or v.get("name") or "unknown victim"
        country = v.get("country") or "??"
        size = v.get("data_size") or "size unknown"
        out.append(
            {
                "title": f"LEAK SITE: {dom} ({country}) claimed by {group}",
                "url": v.get("claim_url") or v.get("url") or "https://www.ransomware.live",
                "summary": clean(v.get("description"), 460)
                + f" | data: {size} | discovered {d.strftime('%Y-%m-%d %H:%M UTC')}",
                "source": "ransomware.live",
                "published": d.isoformat(),
                "category": "ransomware",
                "origin": "api",
                "extra": {"group": group, "country": country},
            }
        )
    return out


def api_exploitdb() -> list[dict]:
    url = "https://www.exploit-db.com/rss.xml"
    try:
        raw = fetch(url, timeout=30)
    except Exception as e:
        print(f"  ! Exploit-DB: {e}", file=sys.stderr)
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    out = []
    for n in root.findall(".//item"):
        title = clean(n.findtext("title"), 220)
        link = (n.findtext("link") or "").strip()
        d = parse_date(n.findtext("pubDate"))
        if not title or not link or not d:
            continue
        if (NOW - d).days > 10:
            continue
        out.append(
            {
                "title": f"PoC: {title}",
                "url": link,
                "summary": clean(n.findtext("description"), 460),
                "source": "Exploit-DB",
                "published": d.isoformat(),
                "category": "exploits",
                "origin": "api",
            }
        )
    return out


# ---------------------------------------------------------------- source table
FEEDS = [
    ("https://krebsonsecurity.com/feed/", "Krebs on Security", "actors"),
    ("https://www.bleepingcomputer.com/feed/", "BleepingComputer", "ransomware"),
    ("https://thehackernews.com/feeds/posts/default", "The Hacker News", "redteam"),
    ("https://www.darkreading.com/rss.xml", "Dark Reading", "redteam"),
    ("https://therecord.media/feed", "The Record", "actors"),
    ("https://www.cisa.gov/cybersecurity-advisories/all.xml", "CISA Advisories", "defense"),
    ("https://securityaffairs.com/feed", "Security Affairs", "ransomware"),
    ("https://www.helpnetsecurity.com/feed/", "Help Net Security", "exploits"),
    ("https://unit42.paloaltonetworks.com/feed/", "Unit 42", "actors"),
    ("https://blog.talosintelligence.com/rss/", "Cisco Talos", "exploits"),
    ("https://www.crowdstrike.com/en-us/blog/feed/", "CrowdStrike", "actors"),
    ("https://cloud.google.com/blog/topics/threat-intelligence/rss/", "Google Cloud TI", "actors"),
    ("https://blog.qualys.com/feed", "Qualys", "exploits"),
    ("https://www.rapid7.com/blog/rss", "Rapid7", "tooling"),
    ("https://redcanary.com/blog/feed/", "Red Canary", "defense"),
    ("https://www.horizon3.ai/feed", "Horizon3", "redteam"),
    ("https://thecybersecuritynews.com/feed/", "CyberSecurityNews", "tooling"),
    ("https://www.kelacyber.com/feed", "KELA Cyber", "darkweb"),
    ("https://feeds.feedburner.com/TheHackersNews", "HackerNews (burner)", "redteam"),
]

GNEWS = [
    ("dark web OR darknet OR leak site OR infostealer when:2d", "GNews: darkweb", "darkweb"),
    ("ransomware attack OR extortion OR data leak victim when:2d", "GNews: ransomware", "ransomware"),
    ("red team OR pentest OR adversary simulation technique when:3d", "GNews: redteam", "redteam"),
    ("APT OR threat actor campaign attribution when:3d", "GNews: actors", "actors"),
    ("CVE exploited OR zero-day OR actively exploited when:2d", "GNews: exploits", "exploits"),
    ("detection engineering OR EDR OR SIEM detection technique when:3d", "GNews: defense", "defense"),
]

API_FUNCS = [api_kev, api_ghsa, api_nvd, api_ransomware_live, api_exploitdb]


# ---------------------------------------------------------------- main
def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    items: list[dict] = []
    errors: list[str] = []

    def run_feed(args):
        url, source, cat = args
        try:
            return rss_items(url, source, cat)
        except Exception as e:
            errors.append(f"{source}: {e}")
            return []

    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(run_feed, FEEDS):
            items.extend(res)

    def run_gnews(args):
        q, source, cat = args
        try:
            return google_news(q, source, cat)
        except Exception as e:
            errors.append(f"{source}: {e}")
            return []

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(run_gnews, GNEWS):
            items.extend(res)

    def run_api(fn):
        try:
            return fn()
        except Exception as e:
            errors.append(f"{fn.__name__}: {e}")
            return []

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(run_api, API_FUNCS):
            items.extend(res)

    # ---- normalise + dedupe + freshness
    seen_h: set[str] = set()
    clean_items: list[dict] = []
    cutoff = NOW - dt.timedelta(hours=STALE_LIMIT)
    for it in items:
        t = it.get("title") or ""
        if not t or len(t) < 12:
            continue
        pub = parse_date(it.get("published"))
        if pub and pub < cutoff:
            continue
        h = item_hash(t, it.get("url", ""))
        if h in seen_h:
            continue
        seen_h.add(h)
        it["hash"] = h
        it["published"] = pub.isoformat() if pub else NOW.isoformat()
        if not it.get("summary"):
            it["summary"] = ""
        clean_items.append(it)

    # load history (previous run hashes + first seen)
    hist_path = DATA / "history.json"
    history = {}
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text())
        except Exception:
            history = {}

    new_items, returning = [], []
    for it in clean_items:
        h = it["hash"]
        if h in history:
            it["first_seen"] = history[h].get("first_seen")
            it["age_days"] = round((NOW - dt.datetime.fromisoformat(history[h]["first_seen"])).total_seconds() / 86400, 1)
            returning.append(it)
        else:
            it["first_seen"] = NOW.isoformat()
            it["age_days"] = 0.0
            history[h] = {"first_seen": NOW.isoformat(), "first_seen_date": TODAY, "title": it["title"][:160]}
            new_items.append(it)

    hist_path.write_text(json.dumps(history, indent=1, ensure_ascii=False))
    (DATA / "archive" / f"{TODAY}.json").write_text(json.dumps({"generated": NOW.isoformat(), "items": clean_items}, indent=1, ensure_ascii=False))

    # ---- bucket
    buckets: dict[str, list[dict]] = {c["id"]: [] for c in CATEGORIES}
    for it in clean_items:
        buckets.setdefault(it["category"], []).append(it)
    for k in buckets:
        buckets[k].sort(key=lambda x: x.get("published") or "", reverse=True)

    feed = {
        "generated": NOW.isoformat(),
        "date": TODAY,
        "buckets": buckets,
        "categories": CATEGORIES,
        "new_count": len(new_items),
        "returning_count": len(returning),
        "total": len(clean_items),
        "errors": errors,
    }
    (DATA / "feed.json").write_text(json.dumps(feed, indent=1, ensure_ascii=False))
    (DATA / "state.json").write_text(
        json.dumps(
            {
                "generated": NOW.isoformat(),
                "date": TODAY,
                "total": len(clean_items),
                "new": len(new_items),
                "returning": len(returning),
                "per_category": {k: len(v) for k, v in buckets.items()},
                "errors": errors,
                "history_size": len(history),
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    print(json.dumps({k: v for k, v in feed.items() if k not in ("buckets", "categories")}, indent=1)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())

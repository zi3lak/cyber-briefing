#!/usr/bin/env python3
"""
CSSLTD CYBER BRIEFING — intel merger.

Reads the council fragments (data/intel/*.md), drops anything already published
in the feed or seen on a previous run (so every issue carries UNIQUE findings),
verifies each URL actually resolves, and writes:

    data/intel.json     clean, validated findings grouped by beat
    data/seen_intel.json hash ledger for cross-run uniqueness
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INTEL_DIR = DATA / "intel"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BEAT_OF = {
    "athena": "ransomware",
    "vulcan": "exploits",
    "iris": "darkweb",
    "prometheus": "actors",
}


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t.lower())).strip()


def hsh(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()[:16]


def url_ok(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            return 200 <= r.status < 400
    except urllib.error.HTTPError as e:
        return 200 <= e.code < 400
    except Exception:
        return False


def main() -> int:
    feed = json.loads((DATA / "feed.json").read_text())
    feed_titles = set()
    feed_urls = set()
    for bucket in feed.get("buckets", {}).values():
        for it in bucket:
            feed_titles.add(norm(it.get("title", ""))[:70])
            feed_urls.add(it.get("url", "").split("?")[0].rstrip("/"))

    seen_path = DATA / "seen_intel.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}

    out: list[dict] = []
    dropped = {"duplicate": 0, "url_dead": 0, "bad_format": 0}
    for f in sorted(INTEL_DIR.glob("*.md")):
        agent = f.stem
        for ln in f.read_text().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 6:
                dropped["bad_format"] += 1
                continue
            ticker, title, source, url, date, comment = parts[:6]
            if not url.startswith("http"):
                dropped["bad_format"] += 1
                continue
            key = hsh(norm(title) + "|" + url.split("?")[0])
            if key in seen:
                dropped["duplicate"] += 1
                continue
            # not already published in the feed under a similar title
            nt = norm(title)
            if any(nt[:55] and nt[:55] in ft for ft in feed_titles):
                dropped["duplicate"] += 1
                continue
            if url.split("?")[0].rstrip("/") in feed_urls:
                dropped["duplicate"] += 1
                continue
            if not url_ok(url):
                dropped["url_dead"] += 1
                continue
            seen[key] = {"first_seen": dt.datetime.now(dt.timezone.utc).isoformat(), "title": title[:160]}
            out.append(
                {
                    "agent": agent,
                    "beat": BEAT_OF.get(agent, "redteam"),
                    "ticker": ticker,
                    "title": title,
                    "source": source,
                    "url": url,
                    "date": date,
                    "comment": comment,
                    "hash": key,
                }
            )

    seen_path.write_text(json.dumps(seen, indent=1, ensure_ascii=False))
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "findings": out,
        "dropped": dropped,
    }
    (DATA / "intel.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    print(json.dumps({"kept": len(out), "dropped": dropped}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

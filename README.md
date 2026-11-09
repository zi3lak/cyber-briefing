# DAILY CYBER BRIEFING

**Cyber security & red team news, served with a pirate's eye.**

Live: **https://zi3lak.github.io/cyber-briefing/**

A static, self-updating daily briefing. Every item is linked to its origin.
The commentary is ours; the facts are theirs.

## What is inside

| Section | What's in it |
|---|---|
| RANSOMWARE & EXTORTION | Crew activity, leak sites, double extortion |
| DARK WEB UNDERGROUND | Markets, stealer logs, access brokers, carding |
| EXPLOITS & VULNERABILITIES | Fresh CVEs, CISA KEV, weaponised PoC |
| RED TEAM OPS & TACTICS | TTPs, tradecraft, adversary simulation |
| THREAT ACTORS & CAMPAIGNS | Who did what, to whom |
| DEFENCE & PATCHING | Mitigations, detections, hardening |
| TOOLING & RELEASES | New gear for the red cell |
| LEAK-SITE BOARD | Live manifest table from crew sites & trackers |
| THE COUNCIL'S PICKS | Unique findings dug up by the agent fleet |

## How it is built

```
scripts/collect.py     RSS + APIs  -> data/feed.json      (stdlib only)
scripts/council.py     agent fleet -> data/intel/*.md      (claude/codex/kimi)
scripts/merge_intel.py dedupe+verify-> data/intel.json
scripts/art.py         engraved SVG line-art engine
scripts/caricature.py  procedural pirate-hacker caricatures
scripts/render.py      -> index.html (single self-contained page)
scripts/run_pipeline.sh the whole thing, one command
```

**Uniqueness.** Every item is hashed (title + URL). `data/history.json` and
`data/seen_intel.json` keep the ledger of what has already been published, so
each issue carries findings you have not read on the previous one. Council
findings are additionally de-duplicated against the feed and every URL is
fetched to confirm it resolves before it reaches the page.

**Artwork.** No stock images and no bitmap assets — the page draws itself.
`art.py` and `caricature.py` generate engraved, hatched, hand-roughened SVG:
the jolly roger watermark, the captain at his terminal, the category icons,
and one procedurally-generated caricature per article (same article, same face,
always).

## The fleet

| Agent | CLI / provider | Beat |
|---|---|---|
| ATHENA | Claude Code / OpenRouter | ransomware & extortion |
| VULCAN | Codex / OpenAI | exploits, CVEs & red team tradecraft |
| IRIS | Kimi Code / Z.AI | dark web underground |
| PROMETHEUS | Claude Code / abliteration.ai | threat actors & campaigns |
| ORION | Claude Code / Z.AI | defence, patching & tooling |

One provider per agent on purpose: a shared provider's in-flight credit limit
rejects the second parallel request with `402 ... would exceed your available
credits given your current in-flight requests`. Every agent also has a
fallback command chain, and the runner retries with backoff.

## Run it

```bash
bash scripts/run_pipeline.sh              # full run: collect + council + render + push
bash scripts/run_pipeline.sh --no-council # feeds only (no agent keys needed)
python3 scripts/collect.py                # feeds only
python3 scripts/render.py                 # re-render from existing data
```

## Automation

- `.github/workflows/publish.yml` — 08:00 UTC daily + weekly deep refresh,
  rebuilds and publishes to GitHub Pages.
- Hermes cron — 08:00 local, runs the full pipeline including the agent fleet
  and pushes the result.

## Sources

Krebs, BleepingComputer, The Hacker News, Dark Reading, The Record, CISA,
Security Affairs, Help Net Security, Unit 42, Cisco Talos, CrowdStrike,
Google Cloud TI, Qualys, Rapid7, Red Canary, Horizon3, CyberSecurityNews,
KELA Cyber, Exploit-DB, NVD, GitHub Advisories, CISA KEV, ransomware.live and
Google News queries across dark web / ransomware / red team / exploitation.
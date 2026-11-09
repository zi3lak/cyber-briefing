#!/usr/bin/env python3
"""
CSSLTD CYBER BRIEFING — council runner.

Runs the CSSLTD agent fleet headless, in parallel, each on one beat of the
briefing. Every agent must return UNIQUE findings (things that are not in
data/feed.json) with a source URL and one line of pirate commentary.

Output: data/intel/<agent>.md  (one fragment per agent)
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INTEL = DATA / "intel"
LOGS = DATA / "logs"

BEATS = [
    {
        "agent": "athena",
        "beat": "RANSOMWARE & EXTORTION",
        "focus": (
            "Active ransomware crews, leak-site activity, double extortion, "
            "RaaS affiliates, recent breaches with real consequences"
        ),
    },
    {
        "agent": "vulcan",
        "beat": "EXPLOITS, CVEs & RED TEAM TECHNIQUES",
        "focus": (
            "Newly weaponised CVEs, CISA KEV additions, exploit chains, "
            "new offensive tooling, red team tradecraft and novel attack techniques"
        ),
    },
    {
        "agent": "iris",
        "beat": "DARK WEB UNDERGROUND",
        "focus": (
            "Dark web marketplaces, initial-access brokers, infostealer log markets, "
            "stolen credentials and certificates for sale, carding activity, "
            "and how these get advertised and resold"
        ),
    },
    {
        "agent": "prometheus",
        "beat": "THREAT ACTORS & CAMPAIGNS",
        "focus": (
            "Named threat actors, intrusion campaigns, supply-chain compromises, "
            "insider and nation-state activity, and attribution news"
        ),
    },
    {
        "agent": "orion",
        "beat": "DEFENCE, PATCHING & TOOLING",
        "focus": (
            "New detection engineering, EDR/SIEM techniques, hardening guidance, "
            "newly released offensive and security tooling, and exploitable "
            "vulnerability details that defenders need to act on today"
        ),
    },
]

SYSTEM = """You are one voice of the CSSLTD daily cyber briefing. Your beat: {beat}.

TASK: find things that happened in the LAST 24-72 HOURS in this area:
{focus}

RULES
- Use WebSearch and WebFetch. You MUST search the live web - do not rely on memory.
- Every finding must be UNIQUE: a concrete, dated event, not a generic trend, not a tutorial.
- Every finding MUST have a real, working source URL that you actually visited.
- Prefer primary sources: vendor advisories, CISA, leak sites, security vendor blogs, reputable newsrooms.
- Skip anything you cannot source. 5 excellent findings beat 20 vague ones.

OUTPUT FORMAT (plain text, no markdown headers beyond the two lines below):
FIRST LINE: a one-line verdict about your beat, max 120 chars, in the pirate voice (no emoji).
THEN: for each finding, exactly this shape, blank line between findings:

TICKER | one short uppercase title | source name | URL | date | one-sentence commentary in the pirate voice (max 220 chars, sarcastic, sharp, no emoji)

5 to 9 findings. Nothing else. No preamble, no closing, no explanation of your process."""

CLAUDE = ["claude", "-p", "--model", "sonnet", "--permission-mode", "acceptEdits"]
CLAUDE_ABL = ["claude", "-p", "--settings", "/home/cssltd/.claude-abliteration/settings.json"]
KIMI = ["kimi", "-p"]
KIMI_OR = ["kimi", "-m", "openrouter/kimi-k3", "-p"]
# ORION: NanoGPT has no credit balance ("Credit balance is too low") and
# Kimi's WebSearch token is rejected, so ORION runs Claude Code against the
# Z.AI GLM endpoint instead — same CLI family as ATHENA, different model.
CLAUDE_ZAI = ["claude", "-p", "--settings", "/home/cssltd/.claude-zai/settings.json"]
CODEX = ["codex", "exec", "--skip-git-repo-check"]

AGENT_CMD = {
    "athena": CLAUDE,
    "vulcan": CODEX,
    "iris": KIMI_OR,
    "prometheus": CLAUDE_ABL,
    "orion": CLAUDE_ZAI,
}

TIMEOUT = 900


def clean_output(raw: str) -> str:
    """Strip CLI noise, keep the agent's prose."""
    lines = raw.splitlines()
    keep = []
    for ln in lines:
        s = ln.rstrip()
        # drop common CLI banners
        if re.match(r"^\s*(\[|To resume this session|Setting up|Loading)", s) and len(s) < 200:
            continue
        if "tokens used" in s.lower():
            continue
        if re.match(r"^⏵|^╭|^╰|^│", s):
            continue
        keep.append(s)
    txt = "\n".join(keep).strip()
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt


def parse_findings(text: str) -> list[dict]:
    out = []
    for ln in text.splitlines():
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) < 6:
            if "|" not in ln and ("FIRST LINE" in ln or ":" in ln) and ln.strip():
                continue  # the agent's verdict line, not a finding
            continue
        ticker, title, source, url, date = parts[:5]
        comment = "|".join(parts[5:]).strip()
        if not url.startswith("http"):
            continue
        out.append(
            {
                "ticker": ticker,
                "title": title,
                "source": source,
                "url": url,
                "date": date,
                "comment": comment,
            }
        )
    return out


def run_agent(beat: dict, attempt: int = 1) -> dict:
    name = beat["agent"]
    INTEL.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    prompt = SYSTEM.format(beat=beat["beat"], focus=beat["focus"])
    cmd = AGENT_CMD[name] + [prompt]
    env = dict(os.environ)
    env.setdefault("HOME", str(Path.home()))
    # Providers that price by reserved output reject the request with an empty
    # `provider.api_error` when max_tokens is too high. Cap it.
    env["KIMI_MODEL_MAX_OUTPUT_SIZE"] = "3000"
    env["KIMI_MODEL_MAX_COMPLETION_TOKENS"] = "3000"
    print(f"[council] {name} -> {beat['beat']}", file=sys.stderr)
    try:
        p = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        raw = (p.stdout or "") + ("\n" + (p.stderr or "") if p.returncode else "")
    except subprocess.TimeoutExpired:
        raw = ""
        print(f"[council] {name} TIMEOUT", file=sys.stderr)
    except Exception as e:
        raw = ""
        print(f"[council] {name} error {e}", file=sys.stderr)

    text = clean_output(raw)
    (LOGS / f"{name}.log").write_text(raw[-20000:])

    # Providers reject parallel bursts with "would exceed your available credits
    # given your current in-flight requests". Retry with backoff.
    rate_limited = any(
        marker in raw
        for marker in (
            "would exceed your available credits",
            "in-flight requests",
            "provider.api_error",
            "429",
        )
    )
    if attempt < 3 and rate_limited and not parse_findings(text):
        wait = 45 * attempt
        print(f"[council] {name} rate-limited, retry in {wait}s", file=sys.stderr)
        time.sleep(wait)
        return run_agent(beat, attempt + 1)

    findings = parse_findings(text)
    if not findings:
        # agent failed or format drifted - keep the raw prose so nothing is lost
        (INTEL / f"{name}.md").write_text(
            f"# {name.upper()} — {beat['beat']}\n\n{text[:1500] if text else '(no output)'}\n"
        )
        return {"agent": name, "ok": False, "findings": 0}
    lines = [f"# {name.upper()} — {beat['beat']}"]
    for f in findings:
        lines.append(
            f"{f['ticker']} | {f['title']} | {f['source']} | {f['url']} | {f['date']} | {f['comment']}"
        )
    (INTEL / f"{name}.md").write_text("\n".join(lines) + "\n")
    return {"agent": name, "ok": True, "findings": len(findings)}


def main() -> int:
    INTEL.mkdir(parents=True, exist_ok=True)
    for f in INTEL.glob("*.md"):
        if f.name.lower() == "readme.md":
            continue
        f.unlink()
    results = []
    def staggered(beat: dict) -> dict:
        # spread the burst so shared providers are not hit simultaneously
        time.sleep(6 * BEATS.index(beat))
        return run_agent(beat)

    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(staggered, b): b for b in BEATS}
        for fut in cf.as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"agent": futs[fut]["agent"], "ok": False, "error": str(e)})
    results.sort(key=lambda r: r["agent"])
    print(json.dumps(results, indent=1))
    (DATA / "council_run.json").write_text(
        json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(), "results": results}, indent=1)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

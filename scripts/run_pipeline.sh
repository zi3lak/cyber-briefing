#!/usr/bin/env bash
# =============================================================================
# CSSLTD DAILY CYBER BRIEFING — full pipeline (local).
#
#   1. collect.py    — feeds + APIs (CISA KEV, NVD, GHSA, ransomware.live, Exploit-DB)
#   2. council.py    — the agent fleet digs for unique findings (ATHENA/VULCAN/IRIS/PROMETHEUS)
#   3. merge_intel.py — dedupe against the feed + verify every URL resolves
#   4. render.py     — build index.html with the generated line-art
#   5. git push      — GitHub Actions publishes to Pages
#
# Usage:  run_pipeline.sh [--no-council] [--no-push]
# =============================================================================
set -uo pipefail

ROOT="/home/cssltd/cyber-briefing"
cd "$ROOT" || exit 1

RUN_COUNCIL=1
PUSH=1
for a in "$@"; do
  case "$a" in
    --no-council) RUN_COUNCIL=0 ;;
    --no-push)    PUSH=0 ;;
  esac
done

# shellcheck source=/dev/null
source "$ROOT/scripts/agent_env.sh"

log() { echo "[$(date -u +%H:%M:%S)] $*"; }

log "STEP 1/5 — collecting feeds and APIs"
python3 scripts/collect.py || log "WARN: collect.py exited non-zero"

if [ "$RUN_COUNCIL" = "1" ]; then
  log "STEP 2/5 — convening the council (agents dig for unique findings)"
  python3 scripts/council.py || log "WARN: council.py exited non-zero"

  log "STEP 3/5 — merging + verifying council intel"
  python3 scripts/merge_intel.py || log "WARN: merge_intel.py exited non-zero"
else
  log "STEP 2/5 — SKIP (council disabled)"
  log "STEP 3/5 — SKIP (council disabled)"
fi

log "STEP 4/5 — rendering index.html"
python3 scripts/render.py || { log "FATAL: render failed"; exit 1; }

if [ "$PUSH" = "1" ]; then
  log "STEP 5/5 — committing and pushing"
  git add -A
  if git diff --staged --quiet; then
    log "nothing new to commit"
  else
    git -c user.name="zi3lak" -c user.email="zi3lak@users.noreply.github.com" \
        commit -m "briefing: refresh $(date -u +%Y-%m-%d)" || log "WARN: commit failed"
    for i in 1 2 3; do
      if git pull --rebase --autostash origin main && git push origin main; then
        log "pushed to origin"
        break
      fi
      log "push retry $i"
      sleep 5
    done
  fi
else
  log "STEP 5/5 — SKIP (push disabled)"
fi

log "DONE — $(python3 -c "import json;d=json.load(open('data/state.json'));print(f\"items={d['total']} new={d['new']}\")" 2>/dev/null)"

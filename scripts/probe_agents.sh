#!/usr/bin/env bash
# Probe: which council CLIs answer headless right now?
cd /home/cssltd/cyber-briefing
source scripts/agent_env.sh

echo "### ATHENA (claude/openrouter) ###"
timeout 180 claude -p "Odpowiedz jednym slowem: OK" --model sonnet 2>&1 | tail -3

echo "### PROMETHEUS (claude/abliteration) ###"
timeout 180 claude -p "Odpowiedz jednym slowem: OK" --settings /home/cssltd/.claude-abliteration/settings.json 2>&1 | tail -3

echo "### VULCAN (codex) ###"
timeout 240 codex exec --skip-git-repo-check "Odpowiedz jednym slowem: OK" 2>&1 | tail -5

echo "### IRIS (kimi/openrouter) ###"
timeout 180 kimi -p "Odpowiedz jednym slowem: OK" -m openrouter/kimi-k3 2>&1 | tail -3

echo "### ORION (kimi/nanogpt) ###"
timeout 180 kimi -p "Odpowiedz jednym slowem: OK" -m nanogpt/qwen3.8-max-prime 2>&1 | tail -3

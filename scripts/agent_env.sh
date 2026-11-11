#!/usr/bin/env bash
# Shared env for the CSSLTD council CLIs (headless runs).
# Sources live secrets without echoing them.
set -a
[ -f "$HOME/.hermes/.env" ] && . "$HOME/.hermes/.env"
[ -f "$HOME/.config/herdr/agent-providers/env.sh" ] && . "$HOME/.config/herdr/agent-providers/env.sh"
set +a

# The kimi CLI lives outside the default PATH (only ~/.zshrc exports it).
# Without this, IRIS dies instantly with FileNotFoundError and an empty log.
[ -d "$HOME/.kimi-code/bin" ] && export PATH="$HOME/.kimi-code/bin:$PATH"

# Claude Code must go through the OpenRouter Anthropic skin (native OAuth expired).
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_API_KEY=""
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1

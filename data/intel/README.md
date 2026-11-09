# Council fragments

One file per agent, regenerated on every pipeline run:

| File | Agent | Beat |
|---|---|---|
| `athena.md` | ATHENA (Claude Code / OpenRouter) | ransomware & extortion |
| `vulcan.md` | VULCAN (Codex) | exploits, CVEs & red team tradecraft |
| `iris.md` | IRIS (Kimi Code / OpenRouter) | dark web underground |
| `prometheus.md` | PROMETHEUS (Claude Code / abliteration.ai) | threat actors & campaigns |
| `orion.md` | ORION (Claude Code / Z.AI GLM) | defence, patching & tooling |

Format per line — `TICKER | TITLE | SOURCE | URL | DATE | COMMENT`.
`scripts/merge_intel.py` parses these, drops anything already published or
previously seen, and verifies each URL resolves before it reaches the page.

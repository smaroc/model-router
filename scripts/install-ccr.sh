#!/usr/bin/env bash
# model-router — install LIVE mode (real model switching via claude-code-router).
#
# This does NOT touch the hook (router.py). It installs musistudio/claude-code-router,
# drops our custom router (score.js + custom-router.js) into the CCR config dir, and
# writes a starter config.json wired to CUSTOM_ROUTER_PATH. Then: `ccr code`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # repo root
CCR_DIR="${HOME}/.claude-code-router"
CONFIG="${CCR_DIR}/config.json"

echo "▸ model-router — LIVE mode installer"

# 1. Install claude-code-router (the proxy that actually switches models)
if ! command -v ccr >/dev/null 2>&1; then
  echo "▸ installing @musistudio/claude-code-router (npm -g)…"
  npm install -g @musistudio/claude-code-router
else
  echo "▸ claude-code-router already installed ($(ccr --version 2>/dev/null || echo present))"
fi

# 2. Drop our scoring engine + custom router into the CCR config dir
mkdir -p "${CCR_DIR}"
cp "${HERE}/ccr/score.js"         "${CCR_DIR}/score.js"
cp "${HERE}/ccr/custom-router.js" "${CCR_DIR}/custom-router.js"
echo "▸ copied score.js + custom-router.js -> ${CCR_DIR}/"

# 3. Write a starter config.json only if none exists (never clobber your config)
if [ -f "${CONFIG}" ]; then
  echo "▸ ${CONFIG} already exists — leaving it untouched."
  echo "  Make sure it has:  \"CUSTOM_ROUTER_PATH\": \"~/.claude-code-router/custom-router.js\""
else
  cp "${HERE}/ccr/config.example.json" "${CONFIG}"
  # inject the Anthropic key from env if available
  if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    if command -v python3 >/dev/null 2>&1; then
      python3 - "$CONFIG" "$ANTHROPIC_API_KEY" <<'PY'
import json, sys
p, key = sys.argv[1], sys.argv[2]
c = json.load(open(p))
for prov in c.get("Providers", []):
    if prov.get("name") == "anthropic":
        prov["api_key"] = key
json.dump(c, open(p, "w"), indent=2)
PY
      echo "▸ wrote ${CONFIG} (Anthropic key taken from \$ANTHROPIC_API_KEY)"
    fi
  else
    echo "▸ wrote ${CONFIG} — edit it and replace sk-ant-REPLACE_WITH_YOUR_ANTHROPIC_KEY"
  fi
fi

cat <<EOF

✓ LIVE mode ready.
  1) Start the router:                      ccr start
  2) Launch Claude Code THROUGH it:
        CCR v3+ :  ccr default-claude-code       (run 'ccr' to list your profiles)
        older   :  ccr code
  Manage it in the UI:                      ccr ui
  Turn it off:                              ccr stop  (then run plain 'claude')

  Editing:
    custom-router.js -> applies on the NEXT request (CCR hot-reloads it, no restart)
    config.json      -> run 'ccr restart' (it's imported on first start, then kept in SQLite)

  How it routes (edit ~/.claude-code-router/custom-router.js to change):
    simple/mechanical  -> Haiku      hard/architecture -> Opus
    standard dev       -> Sonnet     writing/design    -> Fable
EOF

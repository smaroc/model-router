#!/bin/bash
# Registers model-router as a UserPromptSubmit hook in ~/.claude/settings.json (idempotent).
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROUTER="$DIR/router.py"
python3 - "$ROUTER" << 'PY'
import json, os, pathlib, sys
router = sys.argv[1]
p = pathlib.Path.home()/".claude"/"settings.json"
cfg = {}
if p.exists():
    try: cfg = json.loads(p.read_text() or "{}")
    except Exception: cfg = {}
cmd = f"python3 {router}"
ups = cfg.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
if any(h.get("command","").endswith("router.py") for blk in ups for h in blk.get("hooks",[])):
    print("• model-router hook already present in", p); raise SystemExit
ups.append({"matcher":"*","hooks":[{"type":"command","timeout":8,"command":cmd}]})
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print("✓ model-router hook installed in", p)
print("  -> restart Claude Code to activate")
PY

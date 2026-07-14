#!/bin/bash
# Removes the model-router hook from ~/.claude/settings.json.
python3 - << 'PY'
import json, pathlib
p = pathlib.Path.home()/".claude"/"settings.json"
if not p.exists(): print("nothing to do"); raise SystemExit
cfg = json.loads(p.read_text() or "{}")
ups = cfg.get("hooks", {}).get("UserPromptSubmit", [])
new = []
for blk in ups:
    blk["hooks"] = [h for h in blk.get("hooks",[]) if not h.get("command","").endswith("router.py")]
    if blk["hooks"]: new.append(blk)
cfg.setdefault("hooks", {})["UserPromptSubmit"] = new
if not new: cfg["hooks"].pop("UserPromptSubmit", None)
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print("✓ model-router hook removed")
PY

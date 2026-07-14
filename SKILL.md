---
name: model-router
description: >
  Automatic model router for Claude Code. A UserPromptSubmit hook scores each prompt's complexity
  and recommends the right model (a cheap tier for simple tasks, the top tier for hard ones) so you
  stop paying for the top model on trivial work. Bilingual FR/EN, configurable, 100% local.
  Trigger: 'model router', 'auto model', 'which model', 'route model', or installing the hook.
user_invocable: true
tags: [claude-code, hook, cost, model, routing]
---

# model-router

Runs `router.py` as a `UserPromptSubmit` hook. It reads your prompt, scores complexity, and injects a
recommendation (⚡ low / ⚙️ mid / 🧠 high tier) plus a visible nudge. A hook can't switch the model
itself, so you flip it with `/model haiku|sonnet|opus` in one keystroke.

Install: `./scripts/install.sh` (registers the hook in `~/.claude/settings.json` without touching
existing hooks). Config: `~/.config/model-router/config.json`. Quiet mode: `MODEL_ROUTER_QUIET=1`.

See README.md for details.

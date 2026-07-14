# model-router

**Stop paying for the top model on trivial tasks.** `model-router` is a tiny [Claude Code](https://code.claude.com) hook that reads every prompt, scores its complexity, and **recommends the right model** — ⚡ Haiku for simple work, ⚙️ Sonnet for standard dev, 🧠 Opus for hard problems, and ✨ **Fable (Mythos)** for creative/design/copy — so you switch with one keystroke instead of running the top model for everything.

- 🪶 **Zero dependencies** — one Python file, <50 ms, no network.
- 🌍 **Bilingual** — French + English signals out of the box.
- 🧩 **Configurable** — override models, thresholds, and keywords via a JSON file.
- 🔒 **Local & private** — your prompts never leave your machine.

> **Honest note:** a Claude Code hook **cannot change the model itself** (no JSON field allows it, verified mid-2026). `model-router` **injects a recommendation** into the turn's context and shows a nudge; you flip the model with `/model haiku|sonnet|opus` (one keystroke). It's the cleanest automation possible without breaking Claude Code.

## Why

Most people leave **Opus** running on everything — renaming a variable, formatting, answering a question — and pay the top price for work a cheaper model does just as well. The reverse is also true: coding a complex architecture on Haiku produces weak code. The right reflex ("the right model at the right time") is real, but nobody does it by hand on every prompt. This hook does.

## How it works

On every `UserPromptSubmit`, `router.py`:

1. Reads your prompt from the hook's stdin JSON.
2. **Scores** it: architecture / security / performance / hard debug / multi-file / long brief → higher; rename / format / list / short question / slash-command → lower.
3. **Recommends** a model and injects it as context, plus a visible one-line nudge when it's worth it (save money on a downgrade, protect quality on an upgrade).

| Prompt | Recommends |
|---|---|
| `renomme cette variable` / `git status` / `what is the command to…` | ⚡ Haiku |
| `écris une fonction qui valide un email` / `fix the bug on the profile page` | ⚙️ Sonnet |
| `design a multi-tenant architecture with cache and security` | 🧠 Opus |
| `why does this deadlock happen intermittently under load` | 🧠 Opus |
| `refactor auth.ts and session.ts to share logic` (multi-file) | 🧠 Opus |
| `write the landing page copy` / `find a brand name` / `rédige un post` | ✨ Fable |
| `/model opus` (slash-command) | — skipped |

The **creative lane** (writing, design, copywriting, branding, naming, storytelling) routes to **Fable / Mythos**, which sits *beside* the technical tiers rather than above them — a technical prompt like *"design an architecture"* still goes to Opus, not Fable.

## Install

```bash
git clone https://github.com/smaroc/model-router.git
cd model-router
./scripts/install.sh
```

The installer registers a `UserPromptSubmit` hook in `~/.claude/settings.json` **without touching your existing hooks**. Restart Claude Code and it's live.

### Manual install

Add this to `~/.claude/settings.json` (point the path at your clone):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "matcher": "*", "hooks": [
        { "type": "command", "timeout": 8,
          "command": "python3 /absolute/path/to/model-router/router.py" }
      ]}
    ]
  }
}
```

### As a Claude Code skill

`SKILL.md` is included, so you can also drop the folder into `~/.claude/skills/model-router/`.

## Enable / disable / pause

| Goal | How |
|---|---|
| **Enable** | `./scripts/install.sh` (registers the hook), then **restart Claude Code** |
| **Pause** (keep it installed) | `export MODEL_ROUTER_OFF=1` — no injection, no nudge. Re-enable with `unset MODEL_ROUTER_OFF` |
| **Quiet** (inject context, hide the visible nudge) | `export MODEL_ROUTER_QUIET=1` |
| **Disable** (remove the hook) | `./scripts/uninstall.sh`, then restart Claude Code |
| **Check state** | `grep -A6 UserPromptSubmit ~/.claude/settings.json` |

> ⚠️ **Environment variables are read from the shell that launched Claude Code.** After an `export`,
> **restart your Claude Code session** for it to take effect (or add the line to your `~/.zshrc` /
> `~/.bashrc` to make it permanent). To toggle mid-session reliably, use `install.sh` / `uninstall.sh`
> and restart.

## Configuration (optional)

Create `~/.config/model-router/config.json`:

```json
{
  "models":     { "low": "Haiku 4.5", "mid": "Sonnet 5", "high": "Opus 4.8", "creative": "Fable 5" },
  "aliases":    { "low": "haiku", "mid": "sonnet", "high": "opus", "creative": "fable" },
  "thresholds": { "high": 3, "mid": 1 },
  "extra":      { "high": ["\\bkubernetes\\b"], "creative": ["\\bmoodboard\\b"], "low": ["\\bwip\\b"] }
}
```

- **`models`** — display names for each tier (`low`/`mid`/`high` + the `creative` lane → Fable).
- **`aliases`** — the `/model <alias>` shorthand injected in the nudge. If `/model fable` isn't recognized in your setup, set `"creative": "claude-fable-5"`.
- **`thresholds`** — score cutoffs (`>= high` → top model, `>= mid` → mid, else low).
- **`extra`** — your own regex signals per tier, including `"creative"` (added to the built-in FR/EN lists).

Environment:

- `MODEL_ROUTER_OFF=1` — **pause** the router (no injection, no nudge) without uninstalling the hook.
- `MODEL_ROUTER_QUIET=1` — keep the context injection but hide the visible nudge.

## Test it

```bash
echo '{"user_input":"rename this variable"}'                | python3 router.py
echo '{"user_input":"design the auth architecture + cache"}' | python3 router.py
python3 tests/test_router.py   # runs the assertions
```

## Uninstall

```bash
./scripts/uninstall.sh
```

## License

MIT — see [LICENSE](LICENSE). PRs welcome (new keywords, other languages, better scoring).

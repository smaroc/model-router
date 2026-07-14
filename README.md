# model-router

**Stop paying for the top model on trivial tasks.** `model-router` is a tiny [Claude Code](https://code.claude.com) hook that reads every prompt, scores its complexity, and **recommends the right model** — ⚡ Haiku for simple work, ⚙️ Sonnet for standard dev, 🧠 Opus for hard problems, and ✨ **Fable (Mythos)** for creative/design/copy — so you switch with one keystroke instead of running the top model for everything.

- 🪶 **Zero dependencies** — one Python file, <50 ms, no network.
- 🌍 **Bilingual** — French + English signals out of the box.
- 🧩 **Configurable** — override models, thresholds, and keywords via a JSON file.
- 🔒 **Local & private** — your prompts never leave your machine.

## Two modes

| Mode | What it does | Model switch |
|---|---|---|
| **Recommend** (default, `router.py`) | A `UserPromptSubmit` hook that scores each prompt and **suggests** the model. Works in stock Claude Code, zero risk. | You press `/model` (one keystroke). |
| **Live** (`ccr/`, via [claude-code-router](https://github.com/musistudio/claude-code-router)) | The **same scoring** runs as a routing proxy in front of Claude Code and **actually routes** each request to the chosen model. | **Automatic** — nothing to press. |

> **Why two modes?** A Claude Code hook **cannot change the model itself** (no JSON field allows it, verified mid-2026) — so the hook can only recommend. To switch *for real, automatically*, put a router **proxy** in front of Claude Code. `model-router` ships both: the honest hook, and a live router that reuses the exact same scoring. Jump to [**Live mode**](#live-mode--actually-switch-the-model).

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

## Live mode — actually switch the model

The hook recommends; **live mode switches for real**, automatically, with no `/model` keystroke. It reuses the *exact same scoring* (`ccr/score.js` is a 1:1 port of `router.py`), but runs it as a **custom router** inside [`musistudio/claude-code-router`](https://github.com/musistudio/claude-code-router) (CCR) — a proxy that sits in front of Claude Code and routes every request to the model you return.

```bash
./scripts/install-ccr.sh          # installs CCR + drops our router into ~/.claude-code-router/
ccr start                         # start the router (gateway on 127.0.0.1:3456)
ccr default-claude-code           # launch Claude Code THROUGH it (CCR v3+; older CCR: `ccr code`)
```

> Verified end-to-end against `@musistudio/claude-code-router` **v3.0.4**: CCR calls our router on every request and routes `renomme…`→Haiku, `écris une fonction…`→Sonnet, `conçois une architecture…`→Opus, `rédige le copy…`→Fable — live, no `/model`. Editing `custom-router.js` applies on the **next request** (hot-reloaded); after editing `config.json`, run `ccr restart` (it's imported on first start, then kept in SQLite).

The installer:

1. `npm install -g @musistudio/claude-code-router` (if missing).
2. Copies `ccr/score.js` + `ccr/custom-router.js` into `~/.claude-code-router/`.
3. Writes a starter `~/.claude-code-router/config.json` (from [`ccr/config.example.json`](ccr/config.example.json)) wiring `CUSTOM_ROUTER_PATH` — and injects your `$ANTHROPIC_API_KEY` if it's set.

**How it routes** (every request, live):

| Prompt | Routes to |
|---|---|
| `renomme cette variable` / `git status` | ⚡ Haiku |
| `écris une fonction qui valide un email` | ⚙️ Sonnet |
| `design an architecture with cache + security` | 🧠 Opus |
| `write the landing page copy` / `find a brand name` | ✨ Fable |

Edit the tier → model map (and provider) at the top of `~/.claude-code-router/custom-router.js` — changes apply on the next request (no restart). To turn live mode off, run `ccr stop` and use plain `claude` again.

**How it works under the hood:** CCR calls our exported `function (request, config, ctx)` on every request; we read the latest user message from `request.body.messages`, score it, and return `"anthropic,<model>"`. Returning `undefined` (slash-commands, tool results, internal turns) defers to CCR's own `Router` rules. See [`ccr/custom-router.js`](ccr/custom-router.js).

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
python3 tests/test_router.py   # hook (recommend) assertions
node   tests/test_ccr.mjs      # live router (CCR) assertions
```

## Uninstall

```bash
./scripts/uninstall.sh
```

## License

MIT — see [LICENSE](LICENSE). PRs welcome (new keywords, other languages, better scoring).

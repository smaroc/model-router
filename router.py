#!/usr/bin/env python3
"""model-router — score the complexity of a Claude Code prompt and recommend the right model.

Runs as a `UserPromptSubmit` hook. Reads the hook JSON on stdin, writes a JSON result on stdout
(`hookSpecificOutput.additionalContext` + an optional `systemMessage`). A hook cannot switch the
model itself, so it INJECTS a recommendation — you (or Claude) switch with `/model` in one keystroke.

100% local, <50 ms, no network, no dependencies (Python 3.8+). Bilingual FR/EN.

Config (optional): ~/.config/model-router/config.json
  {
    "models":     {"low": "Haiku 4.5", "mid": "Sonnet 5", "high": "Opus 4.8"},
    "thresholds": {"high": 3, "mid": 1},
    "extra":      {"high": ["\\bkubernetes\\b"], "low": ["\\bwip\\b"]}
  }
Env: MODEL_ROUTER_QUIET=1  -> keep the context injection but hide the visible systemMessage.
"""
import sys, json, re, os

# ---- Default target models (display names; the /model aliases are low/mid/high) ----
DEFAULTS = {
    "models":     {"low": "Haiku 4.5", "mid": "Sonnet 5", "high": "Opus 4.8"},
    "aliases":    {"low": "haiku", "mid": "sonnet", "high": "opus"},
    "thresholds": {"high": 3, "mid": 1},
}

# ---- Weighted signals (FR + EN) ----
HIGH = [  # +3 : needs reasoning / whole-system view
    r"architect", r"concev", r"conception", r"design (system|d'|de|the|a )", r"syst[eè]me",
    r"refactor.*(global|ensemble|tout|archi|entire|whole|across)", r"multi[- ]?file", r"multi[- ]?fichier",
    r"plusieurs fichiers", r"several files", r"optimi[sz]", r"performance", r"s[eé]curit", r"security",
    r"vuln[eé]rab", r"algorithm", r"complexit", r"race condition", r"concurren", r"deadlock", r"\bthread",
    r"root cause", r"pourquoi (ça|ca|cela|ce)", r"why (is|does|do|are|would)", r"trade[- ]?off", r"compromis",
    r"strat[eé]g", r"strategy", r"planifie", r"\bplan\b", r"migration", r"migrer", r"migrate",
    r"cryptograph", r"chiffrement", r"encrypt", r"debug.*(complex|difficile|bizarre|intermittent|weird|hard)",
    r"refonte", r"repense", r"rethink", r"scalab", r"passe à l'échelle", r"distribu", r"cache invalidation",
    r"data model", r"mod[eè]le de donn[eé]es", r"state machine", r"consistency", r"idempoten",
]
MID = [  # +1 : standard dev
    r"impl[eé]mente", r"implement", r"ajoute.*(fonctionnalit|feature|écran|page|endpoint|route|composant)",
    r"add (a |an |the )?(feature|screen|page|endpoint|route|component|button)", r"build (a|an|the)",
    r"[eé]cris.*(fonction|composant|classe|module|test)", r"write (a|an|the)?(function|component|class|module|test)",
    r"corrige.*(bug|erreur)", r"fix (the |a )?(bug|error|issue)", r"\bdebug\b", r"d[eé]bogue",
    r"refactor", r"\bapi\b", r"endpoint", r"middleware", r"int[eè]gre", r"integrate",
    r"connecte", r"connect", r"\bparse\b", r"g[eé]n[eè]re.*(script|composant|component)", r"validate", r"valider",
]
LOW = [  # -2 : mechanical / read-only / short question
    r"renomme", r"rename", r"formate", r"format\b", r"indente", r"indent", r"typo", r"faute",
    r"commente", r"add a comment", r"ajoute un commentaire", r"traduis", r"translate", r"liste", r"\blist\b",
    r"affiche", r"montre[- ]moi", r"show me", r"quel(le)?s?\b", r"o[uù] (est|se trouve|sont)",
    r"where (is|are)", r"what (is|are|does) the", r"combien", r"how many", r"git (status|log|diff|add|commit|push)",
    r"\bls\b", r"petit(e)?\b", r"\bsimple\b", r"rapide", r"\bquick\b", r"\bjuste\b", r"\bjust\b",
    r"console\.log", r"\bprint\b", r"bump", r"\bversion\b", r"\blint\b", r"readme", r"rephrase", r"reformule",
]
CODEFILE = r"[\w\-/]+\.(py|ts|tsx|js|jsx|go|rs|java|rb|php|c|cpp|h|hpp|sql|kt|swift|scala|clj|ex|css|html|vue|svelte)"


def load_config():
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    path = os.path.expanduser("~/.config/model-router/config.json")
    try:
        user = json.loads(open(path).read())
        for k in ("models", "thresholds", "aliases"):
            if isinstance(user.get(k), dict):
                cfg[k].update(user[k])
        cfg["extra"] = user.get("extra", {})
    except Exception:
        cfg["extra"] = {}
    return cfg


def score_prompt(p: str, extra: dict) -> int:
    low = p.lower()
    s = 0
    for rx in HIGH + list(extra.get("high", [])):
        if re.search(rx, low): s += 3
    for rx in MID + list(extra.get("mid", [])):
        if re.search(rx, low): s += 1
    for rx in LOW + list(extra.get("low", [])):
        if re.search(rx, low): s -= 2
    words = len(re.findall(r"\w+", low))
    if words <= 4:  s -= 2          # very short order = usually trivial
    if words >= 100: s += 2         # long brief / spec = complex
    files = len(re.findall(CODEFILE, low))
    if files >= 2:  s += 2          # touches several files
    if re.search(r"```", p): s += 1  # pasted code / stack trace
    # explicit multi-step ("do A, then B, then C")
    if len(re.findall(r"\b(then|puis|ensuite|after that|également|aussi|and also)\b", low)) >= 2: s += 1
    return s


def pick(s: int, cfg: dict):
    th, m = cfg["thresholds"], cfg["models"]
    if s >= th["high"]: return m["high"], "high", "🧠", "complex (reasoning / architecture / hard debug)"
    if s >= th["mid"]:  return m["mid"],  "mid",  "⚙️", "standard (everyday dev)"
    return m["low"], "low", "⚡", "simple (mechanical / read-only / short question)"


def read_prompt():
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        return ""
    if not raw.strip():
        return ""
    try:
        d = json.loads(raw)
        return (d.get("user_input") or d.get("prompt") or "").strip()
    except Exception:
        return raw.strip()  # allow: echo "text" | router.py


def main():
    prompt = read_prompt()
    # skip empty prompts and slash-commands (not model-worthy)
    if not prompt or prompt.lstrip().startswith("/"):
        print(json.dumps({"continue": True})); return

    cfg = load_config()
    s = score_prompt(prompt, cfg.get("extra", {}))
    model, tier, icon, label = pick(s, cfg)
    alias = cfg["aliases"][tier]

    ctx = (f"[model-router] Estimated complexity: {label} (score {s}). "
           f"Recommended model for this request: **{model}**. "
           f"If the active model differs, switch with `/model {alias}`. "
           f"Rule of thumb: keep the top model for architecture and hard problems, "
           f"the cheaper tiers for everything else (typically -50% to -80% cost).")

    sys_msg = None
    if tier == "low":
        sys_msg = f"{icon} model-router: simple task -> **{model}** is enough (cheaper). /model {alias}"
    elif tier == "high":
        sys_msg = f"{icon} model-router: complex task -> keep **{model}**. /model {alias}"

    out = {"continue": True, "suppressOutput": False,
           "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
    if sys_msg and os.environ.get("MODEL_ROUTER_QUIET") != "1":
        out["systemMessage"] = sys_msg
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

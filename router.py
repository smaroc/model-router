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

# ---- Default target models (display names; the /model aliases are low/mid/high/creative) ----
# `creative` routes writing/design/copy work to Fable (Mythos), a dedicated lane that sits
# *beside* the technical tiers rather than above them.
DEFAULTS = {
    "models":     {"low": "Haiku 4.5", "mid": "Sonnet 5", "high": "Opus 4.8", "creative": "Fable 5"},
    "aliases":    {"low": "haiku", "mid": "sonnet", "high": "opus", "creative": "fable"},
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

# ---- Creative lane (routes to Fable / Mythos) : writing / design / copy / brand ----
CREATIVE = [
    r"landing page", r"page de vente", r"copywrit", r"\bcopy for\b", r"ad copy", r"ux writing", r"microcopy",
    r"onboarding copy", r"ui copy", r"marketing (copy|email|campaign)", r"campagne", r"newsletter",
    r"blog post", r"article de blog", r"\bstorytelling\b", r"narrati", r"\bslogan\b", r"tagline", r"headline",
    r"accroche", r"tone of voice", r"ton de voix", r"branding", r"\bbrand\b", r"charte", r"\blogo\b",
    r"naming", r"nom de (marque|produit|domaine|projet)", r"name (ideas|for (my|the|a))", r"moodboard",
    r"r[eé]dige.{0,20}(texte|post|article|email|newsletter|caption|l[eé]gende|bio|description|pitch|annonce)",
    r"write.{0,20}(the |a |some )?(copy|post|article|email|newsletter|caption|bio|slogan|tagline|headline|description|ad|pitch|story)",
    r"[eé]cris.{0,20}(un|le|la|des)?.{0,6}(texte|post|article|email|slogan|accroche|pitch|caption|l[eé]gende|scénario|histoire)",
    r"script (de|du|vidéo|reel|pub)", r"scénario", r"pitch deck", r"value proposition", r"proposition de valeur",
]
# If the prompt is clearly technical, do NOT hijack it into the creative lane.
TECH_OVERRIDE = [
    r"architect", r"\bsyst[eè]me\b", r"\bsystem\b", r"algorithm", r"database", r"base de donn", r"\bapi\b",
    r"endpoint", r"deadlock", r"concurren", r"migration", r"refactor", r"s[eé]curit", r"security",
    r"performance", r"optimi[sz]", r"\bschema\b", r"kubernetes", r"terraform", r"\bsql\b", r"backend",
]

# ---- Slash-command / skill routing ----
# Bare CLI control commands: instant, no model reasoning involved -> never route these.
CLI_CONTROL = {
    "model", "clear", "compact", "config", "cost", "doctor", "help", "hooks", "init",
    "login", "logout", "mcp", "permissions", "resume", "status", "theme", "vim", "agents",
    "bug", "release-notes", "add-dir", "review-comment",
}
# Skill/command name patterns that imply heavy reasoning -> +3 (same weight as HIGH).
SKILL_HIGH = [
    r"architect", r"debug", r"investigate", r"forensics", r"audit", r"security-review",
    r"security", r"review", r"plan", r"research", r"migrat", r"design-review", r"verify",
    r"deploy", r"performance", r"benchmark", r"incident", r"consensus", r"orchestrat",
    r"new-project", r"new-milestone", r"roadmap", r"execute-phase", r"^execute$",
    r"complete-milestone", r"^phase$", r"map-codebase",
]
# Skill/command name patterns that imply a quick/mechanical action -> -2 (same weight as LOW).
SKILL_LOW = [
    r"^status$", r"^list$", r"^logs?$", r"^health$", r"^metrics$", r"^help$", r"^stats$",
    r"^progress$", r"^note$", r"^stop$", r"list-", r"-status$", r"-logs$", r"-metrics$",
]
# Skill/command name patterns that route straight to the creative lane.
SKILL_CREATIVE = [
    r"copy", r"brand", r"slide", r"design(?!-review|-system)", r"post-", r"post$", r"reel",
    r"script", r"newsletter", r"landing", r"deck", r"hook-generator", r"content", r"seo",
]


def parse_slash_command(prompt: str):
    """Return (name, rest) for a leading `/cmd` or `/ns:cmd`, else None."""
    m = re.match(r"^/([A-Za-z0-9_.:-]+)(?:\s+(.*))?$", prompt.strip(), re.S)
    if not m:
        return None
    name, rest = m.group(1), (m.group(2) or "").strip()
    return name, rest


def skill_score(name: str) -> int:
    low = name.lower()
    if any(re.search(rx, low) for rx in SKILL_HIGH): return 3
    if any(re.search(rx, low) for rx in SKILL_LOW):  return -2
    return 0


def is_creative(low: str, extra: dict) -> bool:
    if any(re.search(rx, low) for rx in TECH_OVERRIDE):
        return False
    return any(re.search(rx, low) for rx in (CREATIVE + list(extra.get("creative", []))))


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


def score_keywords(text: str, extra: dict) -> int:
    """Pure keyword-bucket score, no length/structure heuristics — safe to reuse on
    short fragments (e.g. a skill invocation's trailing arguments)."""
    low = text.lower()
    s = 0
    for rx in HIGH + list(extra.get("high", [])):
        if re.search(rx, low): s += 3
    for rx in MID + list(extra.get("mid", [])):
        if re.search(rx, low): s += 1
    for rx in LOW + list(extra.get("low", [])):
        if re.search(rx, low): s -= 2
    return s


def score_prompt(p: str, extra: dict) -> int:
    low = p.lower()
    s = score_keywords(p, extra)
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
    # kill switch: pause the router without uninstalling the hook
    if os.environ.get("MODEL_ROUTER_OFF") == "1":
        print(json.dumps({"continue": True})); return
    prompt = read_prompt()
    if not prompt:
        print(json.dumps({"continue": True})); return

    cfg = load_config()
    extra = cfg.get("extra", {})

    slash = parse_slash_command(prompt)
    if slash and ":" not in slash[0] and slash[0] in CLI_CONTROL:
        # bare, unnamespaced CLI control command (/model, /clear, ...) -> instant, nothing to route
        print(json.dumps({"continue": True})); return

    if slash:
        # skill/slash-command invocation: classify by the command name itself, then
        # blend in keyword scoring on any arguments/text that follow it (keyword hits
        # only — the short-argument length penalty in score_prompt doesn't apply here,
        # a skill call with terse args isn't the same as a terse standalone prompt).
        name, rest = slash
        short = name.split(":")[-1]
        is_tech = any(re.search(rx, rest.lower()) for rx in TECH_OVERRIDE)
        if any(re.search(rx, short.lower()) for rx in SKILL_CREATIVE) and not is_tech:
            model, tier, icon, label = cfg["models"]["creative"], "creative", "✨", f"creative skill (/{name})"
        else:
            s = skill_score(short) + (score_keywords(rest, extra) if rest else 0)
            model, tier, icon, label = pick(s, cfg)
            label = f"{label} (/{name})"
    elif is_creative(prompt.lower(), extra):
        model, tier, icon, label = cfg["models"]["creative"], "creative", "✨", "creative (writing / design / copy / brand)"
    else:
        s = score_prompt(prompt, extra)
        model, tier, icon, label = pick(s, cfg)
    alias = cfg["aliases"][tier]

    ctx = (f"[model-router] Detected: {label}. "
           f"Recommended model for this request: **{model}**. "
           f"If the active model differs, switch with `/model {alias}`. "
           f"Rule of thumb: creative/design/copy -> Fable; architecture and hard problems -> the top model; "
           f"everything else -> the cheaper tiers (typically -50% to -80% cost).")

    sys_msg = None
    if tier == "low":
        sys_msg = f"{icon} model-router: simple task -> **{model}** is enough (cheaper). /model {alias}"
    elif tier == "high":
        sys_msg = f"{icon} model-router: complex task -> keep **{model}**. /model {alias}"
    elif tier == "creative":
        sys_msg = f"{icon} model-router: creative/design task -> **{model}** shines here. /model {alias}"

    out = {"continue": True, "suppressOutput": False,
           "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
    if sys_msg and os.environ.get("MODEL_ROUTER_QUIET") != "1":
        out["systemMessage"] = sys_msg
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

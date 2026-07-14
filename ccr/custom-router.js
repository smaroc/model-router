// model-router — LIVE mode for claude-code-router (CCR).
//
// This is a CCR "custom router". Unlike the hook (router.py) which only *recommends*
// a model, CCR runs this on EVERY request and ACTUALLY routes it to the model we return —
// no manual /model, the switch happens live.
//
// Contract (verified against musistudio/claude-code-router):
//   module.exports = async function (request, config, ctx) -> string | undefined
//   - return "<providerName>,<modelId>"  -> CCR routes this request to that provider/model
//   - return undefined                   -> CCR falls back to its own Router rules
//   - request.body.{model,messages,system,tools} hold the Anthropic Messages API request
//
// Wire it in ~/.claude-code-router/config.json:
//   { "CUSTOM_ROUTER_PATH": "~/.claude-code-router/custom-router.js", ... }
// (keep score.js next to this file — it is require()'d below.)

const { classify } = require("./score.js");

// ---- Which provider + model each tier maps to. Edit to taste. ----
// PROVIDER must match a `name` in your config.json "Providers". MODELS must be in its "models".
const PROVIDER = "anthropic";
const MODELS = {
  low:      "claude-haiku-4-5-20251001", // ⚡ simple / mechanical / short
  mid:      "claude-sonnet-4-6",         // ⚙️ standard dev
  high:     "claude-opus-4-8",           // 🧠 architecture / hard debug
  creative: "claude-fable-5",            // ✨ writing / design / copy / brand
};

// Optional per-tier threshold / keyword overrides (mirrors router.py config.json).
const CFG = {
  thresholds: { high: 3, mid: 1 },
  extra: {}, // e.g. { high: ["\\bkubernetes\\b"], creative: ["\\bmoodboard\\b"] }
};

// Pull the latest user message text out of an Anthropic Messages request.
// content can be a plain string OR an array of blocks ({type:"text", text}).
function latestUserText(body) {
  const messages = Array.isArray(body && body.messages) ? body.messages : [];
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (!m || m.role !== "user") continue;
    if (typeof m.content === "string") return m.content;
    if (Array.isArray(m.content)) {
      const text = m.content
        .filter((b) => b && b.type === "text" && typeof b.text === "string")
        .map((b) => b.text)
        .join("\n")
        .trim();
      if (text) return text;
    }
  }
  return "";
}

module.exports = async function router(request, config, ctx) {
  try {
    const body = (request && request.body) || {};
    const prompt = latestUserText(body);

    // No real user turn (tool result, internal summary, empty) -> let CCR decide.
    if (!prompt || prompt.trim().startsWith("/")) return undefined;

    const { tier } = classify(prompt, CFG);
    const model = MODELS[tier];
    if (!model) return undefined;

    // "provider,model" -> CCR normalizes to provider/model and routes there, live.
    return `${PROVIDER},${model}`;
  } catch (_e) {
    return undefined; // never break the request; fall back to Router rules.
  }
};

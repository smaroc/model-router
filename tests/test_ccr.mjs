// Assertions for the CCR live custom router. Run: node tests/test_ccr.mjs
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const router = require("../ccr/custom-router.js");

const CASES = [
  ["renomme cette variable en userId", "claude-haiku-4-5-20251001"],
  ["git status", "claude-haiku-4-5-20251001"],
  ["écris une fonction qui valide un email", "claude-sonnet-4-6"],
  ["add an endpoint to create a user", "claude-sonnet-4-6"],
  ["design a multi-tenant architecture with cache and security", "claude-opus-4-8"],
  ["why does this deadlock happen intermittently under load", "claude-opus-4-8"],
  ["écris la landing page et le copy de mon site", "claude-fable-5"],
  ["trouve un nom de marque pour mon app", "claude-fable-5"],
  ["/model opus", undefined], // slash-command -> defer to CCR
];

const req = (text) => ({ body: { messages: [{ role: "user", content: text }] } });

let fails = 0;
for (const [text, expectModel] of CASES) {
  const out = await router(req(text), {}, {});
  const ok = expectModel === undefined ? out === undefined : out === `anthropic,${expectModel}`;
  if (!ok) fails++;
  console.log((ok ? "PASS" : "FAIL"), String(out).padEnd(34), "::", text.slice(0, 50));
}
// array content block form
const arr = await router({ body: { messages: [{ role: "user", content: [{ type: "text", text: "conçois le système de paiement" }] }] } }, {}, {});
const okArr = arr === "anthropic,claude-opus-4-8";
if (!okArr) fails++;
console.log((okArr ? "PASS" : "FAIL"), arr, ":: [array-content]");

console.log(`\n${CASES.length + 1 - fails}/${CASES.length + 1} passed`);
process.exit(fails ? 1 : 0);

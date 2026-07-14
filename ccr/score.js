// model-router — scoring engine (JS port of router.py), shared by the CCR live router.
// Pure logic, no I/O: takes a prompt string, returns { tier, score }.
// tier ∈ "low" | "mid" | "high" | "creative". Bilingual FR/EN. Mirrors router.py exactly.

const HIGH = [ // +3 : needs reasoning / whole-system view
  /architect/, /concev/, /conception/, /design (system|d'|de|the|a )/, /syst[eè]me/,
  /refactor.*(global|ensemble|tout|archi|entire|whole|across)/, /multi[- ]?file/, /multi[- ]?fichier/,
  /plusieurs fichiers/, /several files/, /optimi[sz]/, /performance/, /s[eé]curit/, /security/,
  /vuln[eé]rab/, /algorithm/, /complexit/, /race condition/, /concurren/, /deadlock/, /\bthread/,
  /root cause/, /pourquoi (ça|ca|cela|ce)/, /why (is|does|do|are|would)/, /trade[- ]?off/, /compromis/,
  /strat[eé]g/, /strategy/, /planifie/, /\bplan\b/, /migration/, /migrer/, /migrate/,
  /cryptograph/, /chiffrement/, /encrypt/, /debug.*(complex|difficile|bizarre|intermittent|weird|hard)/,
  /refonte/, /repense/, /rethink/, /scalab/, /passe à l'échelle/, /distribu/, /cache invalidation/,
  /data model/, /mod[eè]le de donn[eé]es/, /state machine/, /consistency/, /idempoten/,
];
const MID = [ // +1 : standard dev
  /impl[eé]mente/, /implement/, /ajoute.*(fonctionnalit|feature|écran|page|endpoint|route|composant)/,
  /add (a |an |the )?(feature|screen|page|endpoint|route|component|button)/, /build (a|an|the)/,
  /[eé]cris.*(fonction|composant|classe|module|test)/, /write (a|an|the)?(function|component|class|module|test)/,
  /corrige.*(bug|erreur)/, /fix (the |a )?(bug|error|issue)/, /\bdebug\b/, /d[eé]bogue/,
  /refactor/, /\bapi\b/, /endpoint/, /middleware/, /int[eè]gre/, /integrate/,
  /connecte/, /connect/, /\bparse\b/, /g[eé]n[eè]re.*(script|composant|component)/, /validate/, /valider/,
];
const LOW = [ // -2 : mechanical / read-only / short question
  /renomme/, /rename/, /formate/, /format\b/, /indente/, /indent/, /typo/, /faute/,
  /commente/, /add a comment/, /ajoute un commentaire/, /traduis/, /translate/, /liste/, /\blist\b/,
  /affiche/, /montre[- ]moi/, /show me/, /quel(le)?s?\b/, /o[uù] (est|se trouve|sont)/,
  /where (is|are)/, /what (is|are|does) the/, /combien/, /how many/, /git (status|log|diff|add|commit|push)/,
  /\bls\b/, /petit(e)?\b/, /\bsimple\b/, /rapide/, /\bquick\b/, /\bjuste\b/, /\bjust\b/,
  /console\.log/, /\bprint\b/, /bump/, /\bversion\b/, /\blint\b/, /readme/, /rephrase/, /reformule/,
];
const CODEFILE = /[\w\-/]+\.(py|ts|tsx|js|jsx|go|rs|java|rb|php|c|cpp|h|hpp|sql|kt|swift|scala|clj|ex|css|html|vue|svelte)/g;

// Creative lane (routes to Fable / Mythos) : writing / design / copy / brand
const CREATIVE = [
  /landing page/, /page de vente/, /copywrit/, /\bcopy for\b/, /ad copy/, /ux writing/, /microcopy/,
  /onboarding copy/, /ui copy/, /marketing (copy|email|campaign)/, /campagne/, /newsletter/,
  /blog post/, /article de blog/, /\bstorytelling\b/, /narrati/, /\bslogan\b/, /tagline/, /headline/,
  /accroche/, /tone of voice/, /ton de voix/, /branding/, /\bbrand\b/, /charte/, /\blogo\b/,
  /naming/, /nom de (marque|produit|domaine|projet)/, /name (ideas|for (my|the|a))/, /moodboard/,
  /r[eé]dige.{0,20}(texte|post|article|email|newsletter|caption|l[eé]gende|bio|description|pitch|annonce)/,
  /write.{0,20}(the |a |some )?(copy|post|article|email|newsletter|caption|bio|slogan|tagline|headline|description|ad|pitch|story)/,
  /[eé]cris.{0,20}(un|le|la|des)?.{0,6}(texte|post|article|email|slogan|accroche|pitch|caption|l[eé]gende|scénario|histoire)/,
  /script (de|du|vidéo|reel|pub)/, /scénario/, /pitch deck/, /value proposition/, /proposition de valeur/,
];
// If the prompt is clearly technical, do NOT hijack it into the creative lane.
const TECH_OVERRIDE = [
  /architect/, /\bsyst[eè]me\b/, /\bsystem\b/, /algorithm/, /database/, /base de donn/, /\bapi\b/,
  /endpoint/, /deadlock/, /concurren/, /migration/, /refactor/, /s[eé]curit/, /security/,
  /performance/, /optimi[sz]/, /\bschema\b/, /kubernetes/, /terraform/, /\bsql\b/, /backend/,
];

function isCreative(low, extra) {
  if (TECH_OVERRIDE.some((rx) => rx.test(low))) return false;
  const extraCreative = (extra.creative || []).map((s) => new RegExp(s));
  return CREATIVE.concat(extraCreative).some((rx) => rx.test(low));
}

function scorePrompt(p, extra) {
  const low = p.toLowerCase();
  let s = 0;
  for (const rx of HIGH.concat((extra.high || []).map((x) => new RegExp(x)))) if (rx.test(low)) s += 3;
  for (const rx of MID.concat((extra.mid || []).map((x) => new RegExp(x)))) if (rx.test(low)) s += 1;
  for (const rx of LOW.concat((extra.low || []).map((x) => new RegExp(x)))) if (rx.test(low)) s -= 2;
  const words = (low.match(/\w+/g) || []).length;
  if (words <= 4) s -= 2;            // very short order = usually trivial
  if (words >= 100) s += 2;          // long brief / spec = complex
  const files = (low.match(CODEFILE) || []).length;
  if (files >= 2) s += 2;            // touches several files
  if (/```/.test(p)) s += 1;         // pasted code / stack trace
  if ((low.match(/\b(then|puis|ensuite|after that|également|aussi|and also)\b/g) || []).length >= 2) s += 1;
  return s;
}

/**
 * Classify a prompt into a tier.
 * @param {string} prompt
 * @param {{thresholds?:{high:number,mid:number}, extra?:object}} [cfg]
 * @returns {{tier:"low"|"mid"|"high"|"creative", score:number}}
 */
function classify(prompt, cfg = {}) {
  const thresholds = cfg.thresholds || { high: 3, mid: 1 };
  const extra = cfg.extra || {};
  const low = (prompt || "").toLowerCase();
  if (isCreative(low, extra)) return { tier: "creative", score: null };
  const score = scorePrompt(prompt || "", extra);
  if (score >= thresholds.high) return { tier: "high", score };
  if (score >= thresholds.mid) return { tier: "mid", score };
  return { tier: "low", score };
}

module.exports = { classify, scorePrompt, isCreative };

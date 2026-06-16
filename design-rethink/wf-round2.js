export const meta = {
  name: 'design-council-round2',
  description: 'Round 2: fold all council feedback into system v2, rebuild all 16 mocks, re-critique on calibrated 0-100',
  phases: [
    { title: 'Direct', detail: 'one director writes design-system-v2.md folding Claude+codex+visual fixes' },
    { title: 'Rebuild', detail: 'per-page agents rewrite all 16 mocks to obey v2 (batched x4 to dodge rate limits)' },
    { title: 'Critique', detail: 'per-page jurors re-score on calibrated 0-100' },
  ],
}

// ---- page roster ----
const MARKETING = ['landing', 'about', 'product', 'auth']
const APP = ['personas-list', 'personas-new', 'persona-detail', 'capability-detail',
  'crawl-setup', 'feature-pack', 'simulations-list', 'simulations-new',
  'simulation-results', 'agent-transcript', 'agent-detail', 'app-shell']
const PAGES = [
  ...MARKETING.map(id => ({ id, kind: 'marketing' })),
  ...APP.map(id => ({ id, kind: 'app' })),
]

// ---- schemas ----
const DIRECTOR_SCHEMA = {
  type: 'object',
  properties: {
    version: { type: 'string' },
    changelog: { type: 'array', items: { type: 'string' } },
    keyDecisions: { type: 'string' },
  },
  required: ['changelog', 'keyDecisions'],
  additionalProperties: false,
}
const MOCK_SCHEMA = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    changed: { type: 'boolean' },
    summary: { type: 'string' },
  },
  required: ['id', 'changed', 'summary'],
  additionalProperties: false,
}
const CRITIQUE_SCHEMA = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    score: { type: 'number' },
    verdict: { type: 'string' },
    topIssues: { type: 'array', items: { type: 'string' } },
  },
  required: ['id', 'score', 'verdict', 'topIssues'],
  additionalProperties: false,
}

// ---- batched fan-out (cap concurrent heavy agents to dodge R1 rate limits) ----
async function inBatches(items, size, fn) {
  const out = []
  for (let i = 0; i < items.length; i += size) {
    const batch = items.slice(i, i + size)
    const res = await parallel(batch.map((it, j) => () => fn(it, i + j)))
    out.push(...res)
  }
  return out
}

// ===== PHASE A: director =====
phase('Direct')
const directorPrompt = `You are the design director for Sidira's clean-sheet design system "THE READING CONSOLE". You are in repo root /Users/ram/Projects/sidira-simulator.

Produce design-rethink/system/design-system-v2.md — a REVISION of v1 that folds in ALL Round-1 council feedback and pushes the system to top-0.1%. Write the file with the Write tool.

READ FIRST (all of these):
- design-rethink/system/design-system-v1.md  (the current spec — keep its bones)
- design-rethink/system/PRINCIPLES.md
- design-rethink/council/claude-visual-r1.md  (my visual verdict)
- design-rethink/council/codex-r2-system.md   (codex system juror, scored 82)
- design-rethink/council/codex-r2-app.md       (codex app juror, scored 78)
- design-rethink/council/codex-r2-marketing.md (codex marketing juror)

THE CORE TENSION TO RESOLVE: the user wants "no holds barred" graphics/effects. BUT both codex jurors say v1 is over-theatrical, over-lawyered, names too many signature gimmicks (Population Field, Spread Stamp, Channel Legend, Provenance Spine, Living Manifest, Dim-Unlocked Trace...) and reads like "a concept deck performing intelligence." The mature resolution — encode it as system law: MAXIMAL IMPACT WHERE IT COUNTS, BRUTAL QUIET EVERYWHERE ELSE. Heroes/showpieces (landing hero, simulation results, persona-build evaluate, new-sim manifest) may go full no-holds-barred WebGL/canvas/glow/depth — tastefully. The other 80% of every screen breathes and is quiet so the showpiece lands. Keep the Console/Sheet ontology + candor primitives + ONE signature visualization (the Population Field); demote or retire the rest to optional motifs.

MUST encode these as explicit, testable v2 laws (with exact values):
1. CANDOR, SCOPED: ± / spread-stamp on INFERRED readings only (score, lift, sentiment, confidence, conversion, weakness-frequency, n-derived estimates). EXEMPT and must NOT carry ±: identifiers, timestamps, seeds, model names, raw counts/n. State the exempt list.
2. CONTRAST AA (fix v1's failing values): Sheet signal-green as TEXT = #00785F (was #0FA882, ~2.75:1 fail); spread text = #6F5E33 (was #857449); --text-faint reserved for disabled only, never labels/tooltips on console-700. Give every text/bg pair a passing ratio.
3. SIGNAL BUDGET: exactly ONE accent carrier per viewport region. Signal color MEANS "live reading" — never "positive/ship/up". Sentiment & direction render in plain ink + glyph + provenance, never valence color.
4. NO VALENCE COLOR + reconsider treatment hue: v1 assigns treatment #F0796B which reads as danger. Shift treatment toward a calmer magenta/coral ~oklch(0.72 0.10 345). State the new treatment + baseline hues.
5. DRIFT, FINITE & ACCESSIBLE: uncalibrated readings drift max 2px, opacity ~0.45, cycle 12-18s, PAUSE after 20s idle, FREEZE on focus/hover/prefers-reduced-motion. The glyph + copy carry the truth; motion must not punish attention. Calibrated readings are stable.
6. SIGNATURE EFFECT DISCIPLINE: the Population Field is the ONE signature viz, allowed only where it IS the computation. Specify exactly which page archetypes earn it vs. get a quiet motif/static poster. Forbid numbered section scaffolds (01/02) except true ordered flows. Cap Channel Legend to one per live reading region (~40% reduction).
7. COMPONENT STATE MATRIX: add explicit default/hover/focus/active/disabled/loading/error specs for buttons, inputs, tables, charts in BOTH Console and Sheet modes. Top systems are boringly complete here.
8. BREATHING ROOM: define a spacing scale and a max-panels-per-viewport guideline; the hero reading must dominate.

Keep it implementable (concrete tokens, hex/oklch, px, ms). Then return {version, changelog (list of the biggest changes from v1), keyDecisions}.`
const director = await agent(directorPrompt, { label: 'director:v2', schema: DIRECTOR_SCHEMA })
log(`v2 system written. ${director?.changelog?.length || 0} major changes. ${(director?.keyDecisions || '').slice(0, 140)}`)

// ===== PHASE B: rebuild all mocks (batches of 4) =====
phase('Rebuild')
function mockPrompt(p) {
  const codexFile = p.kind === 'marketing' ? 'codex-r2-marketing.md' : 'codex-r2-app.md'
  const tier = p.kind === 'marketing' ? 'marketing page (stripe.com / linear.app launch tier)' : 'app screen (Linear/Raycast tier)'
  return `You are a top-0.1% product designer implementing Round 2 of Sidira's "Reading Console" system. Repo root: /Users/ram/Projects/sidira-simulator.

REWRITE design-rethink/mocks/${p.id}.html IN PLACE to fully obey design-system-v2 and reach top-0.1% for a ${tier}. Write the file with the Write tool (single self-contained HTML: inline <style>, inline <script> for any canvas/WebGL, realistic Sidira content, optional CDN fonts only).

READ FIRST:
- design-rethink/system/design-system-v2.md  (AUTHORITATIVE — obey tokens, contrast, laws exactly)
- design-rethink/system/PRINCIPLES.md
- design-rethink/mocks/${p.id}.html  (current R1 mock — keep what works, fix what doesn't)
- design-rethink/council/${codexFile}  (apply EVERY fix named for "${p.id}")
- design-rethink/council/codex-r2-system.md  (system laws + contrast values)
- design-rethink/council/claude-visual-r1.md

ENFORCE THESE v2 LAWS (testable):
- CANDOR scoped: ± / spread-stamp on INFERRED readings only; NO ± on identifiers, timestamps, seeds, model names, raw n.
- CONTRAST AA: Sheet signal-green TEXT = #00785F; spread text = #6F5E33; never faint text on dark labels.
- SIGNAL BUDGET: ONE accent carrier per viewport region; signal = "live reading" only, never "positive/ship/up". Direction/sentiment in plain ink + glyph + provenance, NO valence color. Treatment hue calm magenta/coral, not danger-red.
- DRIFT: uncalibrated readings drift ≤2px / opacity ~0.45 / 12-18s, pause on idle, freeze on hover/focus/reduced-motion; never settle false-precise. Calibrated readings are stable.
- RESTRAINT (codex's #1 complaint — v1 reads as a "demo reel"): Population Field / canvas showpiece ONLY where it IS the computation. ${p.id === 'landing' || p.id === 'simulation-results' || p.id === 'personas-new' || p.id === 'simulations-new' || p.id === 'app-shell' ? 'THIS page EARNS a full no-holds-barred hero showpiece (maximal, tasteful WebGL/canvas/glow/depth) — make a designer stop scrolling.' : 'THIS page does NOT earn the full field — quiet it to a small motif or static poster; let the content breathe.'} Remove numbered section scaffolds (01/02) unless a true ordered flow. Cut Channel Legend volume ~40% (one per live reading region).
- BREATHING ROOM: more whitespace, fewer simultaneous panels per viewport, hero reading dominates.

Goal: 80% of the screen brutally quiet so the one showpiece lands. Apply every ${p.id}-specific codex fix. Return {id:"${p.id}", changed, summary}.`
}
const rebuilt = await inBatches(PAGES, 4, (p) =>
  agent(mockPrompt(p), { label: `mock:${p.id}`, phase: 'Rebuild', schema: MOCK_SCHEMA })
)
log(`rebuilt ${rebuilt.filter(Boolean).length}/${PAGES.length} mocks`)

// ===== PHASE C: re-critique (batches of 6) =====
phase('Critique')
function critiquePrompt(p) {
  const tier = p.kind === 'marketing' ? 'marketing page on earth (stripe.com / linear.app tier)' : 'app screen on earth (Linear/Stripe/Vercel/Raycast tier)'
  return `You are an independent top-0.1% design juror. Be rigorous, specific, hard to impress; do NOT flatter. Repo root: /Users/ram/Projects/sidira-simulator.

Read design-rethink/mocks/${p.id}.html and design-rethink/system/design-system-v2.md. Score this page on a CALIBRATED 0-100 scale where 100 = indistinguishable from the single best ${tier}, 90 = clearly top-0.1%, 75 = strong/shippable but not elite, 50 = competent, 25 = generic.

Check law compliance: candor SCOPE (± on inferred only, not on ids/timestamps/n), AA contrast (#00785F sheet-green text etc.), signal budget (one carrier/region, signal=live-reading not positive), no valence color, finite drift, RESTRAINT (no demo-reel over-use of the signature effect; quiet 80% so the showpiece lands), breathing room. A page that breaks a law cannot score above 85.

Return {id:"${p.id}", score, verdict (one line), topIssues (<=3 specific, concrete fixes)}.`
}
const critiques = (await inBatches(PAGES, 6, (p) =>
  agent(critiquePrompt(p), { label: `judge:${p.id}`, phase: 'Critique', schema: CRITIQUE_SCHEMA })
)).filter(Boolean)

const scores = critiques.map(c => c.score)
const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
const topCount = scores.filter(s => s >= 90).length
const sorted = [...critiques].sort((a, b) => a.score - b.score)
log(`ROUND 2 critique: avg=${avg}, top-0.1%(>=90)=${topCount}/${critiques.length}, weakest=${sorted.slice(0,3).map(c=>c.id+':'+c.score).join(' ')}`)

return {
  round: 2,
  avg,
  topCount,
  total: critiques.length,
  director: director ? { changelog: director.changelog, keyDecisions: director.keyDecisions } : null,
  rebuilt: rebuilt.filter(Boolean).map(r => ({ id: r.id, changed: r.changed, summary: r.summary })),
  pages: sorted.map(c => ({ id: c.id, score: c.score, verdict: c.verdict, topIssues: c.topIssues })),
}

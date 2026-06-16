export const meta = {
  name: 'design-council-round4',
  description: 'Round 4 (final polish): edit-down leaders toward 90, rescue laggards, global P7 contrast sweep; re-critique 0-100',
  phases: [
    { title: 'Polish', detail: 'per-page band-tailored polish (leaders edit-down, laggards rescued) reading r3-critique.json' },
    { title: 'Critique', detail: 'per-page jurors re-score on calibrated 0-100' },
  ],
}

const META = {
  'simulation-results': { kind: 'app', cls: 'SHOWPIECE', score: 87 },
  'persona-detail': { kind: 'app', cls: 'RECORD', score: 88 },
  'app-shell': { kind: 'app', cls: 'WORKING', score: 86 },
  'feature-pack': { kind: 'app', cls: 'WORKING', score: 84 },
  'capability-detail': { kind: 'app', cls: 'RECORD', score: 83 },
  'simulations-list': { kind: 'app', cls: 'WORKING', score: 83 },
  'personas-new': { kind: 'app', cls: 'SHOWPIECE', score: 82 },
  'personas-list': { kind: 'app', cls: 'WORKING', score: 82 },
  'agent-detail': { kind: 'app', cls: 'WORKING', score: 82 },
  'agent-transcript': { kind: 'app', cls: 'WORKING', score: 80 },
  'simulations-new': { kind: 'app', cls: 'SHOWPIECE', score: 80 },
  'landing': { kind: 'marketing', cls: 'SHOWPIECE', score: 80 },
  'about': { kind: 'marketing', cls: 'RECORD', score: 79 },
  'crawl-setup': { kind: 'app', cls: 'WORKING', score: 77 },
  'auth': { kind: 'marketing', cls: 'RECORD', score: 74 },
  'product': { kind: 'marketing', cls: 'WORKING', score: 73 },
}
const PAGES = Object.keys(META).map(id => ({ id, ...META[id] }))

const MOCK_SCHEMA = { type: 'object', properties: { id: { type: 'string' }, changed: { type: 'boolean' } }, required: ['id', 'changed'], additionalProperties: false }
const CRITIQUE_SCHEMA = { type: 'object', properties: { id: { type: 'string' }, score: { type: 'number' }, verdict: { type: 'string' }, topIssues: { type: 'array', items: { type: 'string' } } }, required: ['id', 'score', 'verdict', 'topIssues'], additionalProperties: false }

async function inBatches(items, size, fn) {
  const out = []
  for (let i = 0; i < items.length; i += size) {
    const res = await parallel(items.slice(i, i + size).map((it, j) => () => fn(it, i + j)))
    out.push(...res)
  }
  return out
}

phase('Polish')
function band(p) {
  if (p.score >= 85) return `BAND: LEADER (R3 ${p.score}). You are within reach of a genuine 90+ (top-0.1%). BOTH councils say the path past 90 is EDITING DOWN, not adding: cut repeated provenance/candor micro-scaffolding by ~35%, strengthen the EDITORIAL hierarchy so one reading clearly dominates, remove anything that "explains its own honesty" more than once, and add ONE memorable, product-specific comparative figure/table that only Sidira could show (a real Sidira-grounded artifact, not generic chrome). Restraint and confidence — make it feel inevitable, not instrumented. Obey the codex_note in your r3-critique entry exactly.`
  if (p.score >= 80) return `BAND: STRONG (R3 ${p.score}). Polish to break 88+: fix every r3_issue, tighten hierarchy, ensure the marquee reading dominates, and add a single moment of genuine craft finesse (typographic detail, a better-composed showpiece, or a sharper comparative figure). No new law-breaks.`
  return `BAND: LAGGARD (R3 ${p.score}) — needs a real craft upgrade, not a tweak. This page reads competent-but-generic; give it a distinct, arresting, on-thesis identity while staying 100% within the system + v2.1 patch. ${p.id === 'product' ? 'Give the hero one arresting focal climax; replace the three near-identical mono key:value proof blocks with varied textures (one prose, one diagram/artifact, one figure).' : ''}${p.id === 'auth' ? 'Break out of the templated split-screen auth skeleton — make the left stage a genuinely distinctive Sidira moment; drop the manufactured live-comparison reading that "performs intelligence"; keep one honest uncalibrated atmosphere reading.' : ''}${p.id === 'about' ? 'Lift it from a tasteful wireframe to a real printed RECORD with editorial richness and one memorable specimen; calm lab-notebook prose, no manifesto.' : ''}${p.id === 'crawl-setup' ? 'Make it a genuinely satisfying high-efficiency config surface with real density discipline and one quiet moment of polish.' : ''}`
}
function polishPrompt(p) {
  const tier = p.kind === 'marketing' ? 'marketing page (stripe.com / linear.app tier)' : 'app screen (Linear/Raycast tier)'
  return `You are a top-0.1% product designer on the FINAL polish round (R4) of Sidira's "Reading Console" system. Repo root: /Users/ram/Projects/sidira-simulator. This is a ${p.cls}-class ${tier}.

EDIT design-rethink/mocks/${p.id}.html IN PLACE. Keep everything that works; do NOT regress any passing law.

READ FIRST:
- design-rethink/council/r3-critique.json  (find the "${p.id}" entry: r3_score, r3_verdict, r3_issues[], and codex_note if present — these are your exact targets)
- design-rethink/system/design-system-v2.md and design-rethink/system/design-system-v2.1-patch.md (laws P1..P10 are mechanical pass/fail — obey ALL)
- design-rethink/mocks/${p.id}.html

${band(p)}

GLOBAL FIX (every page): P7 sub-AA contrast keeps recurring — audit EVERY uncalibrated word/label/provenance/separator. Running WORDS (e.g. "UNCALIBRATED", "UNCAL", "EST") and labels must be --text-mut (#929BAE) or brighter; reserve --spread-dim / #90815F STRICTLY for the ◇ glyph and the ± numeric value, never running words. --text-faint (#646E84) is disabled-only.

Fix every r3_issue for ${p.id}, apply the band directive, sweep P1..P10. Self-contained HTML (inline style + inline canvas/SVG, optional CDN fonts). Write with the Write tool. Return ONLY {id:"${p.id}", changed:true}. (No prose summary — keep the return minimal.)`
}
const fixed = await inBatches(PAGES, 4, (p) => agent(polishPrompt(p), { label: `polish:${p.id}`, phase: 'Polish', schema: MOCK_SCHEMA }))
log(`polished ${fixed.filter(Boolean).length}/${PAGES.length}`)

phase('Critique')
function critiquePrompt(p) {
  const tier = p.kind === 'marketing' ? 'marketing page on earth (stripe.com / linear.app tier)' : 'app screen on earth (Linear/Stripe/Vercel/Raycast tier)'
  return `You are an independent top-0.1% design juror. Rigorous, specific, hard to impress; do NOT flatter, do NOT inflate. Repo root: /Users/ram/Projects/sidira-simulator.

Read design-rethink/mocks/${p.id}.html, design-rethink/system/design-system-v2.md, design-rethink/system/design-system-v2.1-patch.md. Score 0-100 CALIBRATED: 100 = indistinguishable from the single best ${tier}; 90 = clearly top-0.1% (a genuine elite designer would ship it as-is and be proud); 80 = strong/premium but not elite; 50 = competent. A 90 must be EARNED — most premium work is 80-88.

MECHANICAL LAW CHECK (any one break caps at 85): P1 resting logo ink not lime · P2 one signal carrier/region (signal=live reading only) · P3 only status dot loops forever · P4 drift ≤2px · P5 static posters use --signal-dim · P6 verdict gated on calibration (no SHIP/lime on ◇) · P7 --text-faint disabled-only + provenance clears AA · P8 candor scope both ways · P9 live field showpiece-only & never twice · P10 marquee reading is legible focal point. Also judge craft, editorial hierarchy, whether it edits-down vs over-instruments, and whether it would stop a top designer scrolling.

Return {id:"${p.id}", score, verdict (one line), topIssues (<=3 concrete fixes; [] only if genuinely 90+)}.`
}
const critiques = (await inBatches(PAGES, 6, (p) => agent(critiquePrompt(p), { label: `judge:${p.id}`, phase: 'Critique', schema: CRITIQUE_SCHEMA }))).filter(Boolean)

const scores = critiques.map(c => c.score)
const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
const topCount = scores.filter(s => s >= 90).length
const near = scores.filter(s => s >= 87).length
const sorted = [...critiques].sort((a, b) => a.score - b.score)
log(`ROUND 4: avg=${avg}, >=90=${topCount}, >=87=${near}, range=${sorted[0].score}-${sorted[sorted.length-1].score}`)

return { round: 4, avg, topCount, near, total: critiques.length,
  pages: sorted.map(c => ({ id: c.id, score: c.score, verdict: c.verdict, topIssues: c.topIssues })) }

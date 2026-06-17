export const meta = {
  name: 'design-council-round5',
  description: 'Round 5 (terminal): fix surviving concrete bugs/law-breaks first, then push the 84-89 cluster for the singular crafted moment that cracks 90; re-critique 0-100',
  phases: [
    { title: 'Refine', detail: 'per-page: fix r4 concrete bugs/law-breaks, then one highest-leverage craft move toward 90' },
    { title: 'Critique', detail: 'per-page jurors re-score on calibrated 0-100' },
  ],
}

// R4 scores (all 84-89 now) + class/kind
const META = {
  'persona-detail': { kind: 'app', cls: 'RECORD', score: 89 },
  'simulation-results': { kind: 'app', cls: 'SHOWPIECE', score: 87 },
  'agent-transcript': { kind: 'app', cls: 'WORKING', score: 87 },
  'landing': { kind: 'marketing', cls: 'SHOWPIECE', score: 87 },
  'capability-detail': { kind: 'app', cls: 'RECORD', score: 86 },
  'simulations-list': { kind: 'app', cls: 'WORKING', score: 86 },
  'personas-list': { kind: 'app', cls: 'WORKING', score: 86 },
  'feature-pack': { kind: 'app', cls: 'WORKING', score: 85 },
  'simulations-new': { kind: 'app', cls: 'SHOWPIECE', score: 85 },
  'crawl-setup': { kind: 'app', cls: 'WORKING', score: 85 },
  'app-shell': { kind: 'app', cls: 'WORKING', score: 84 },
  'personas-new': { kind: 'app', cls: 'SHOWPIECE', score: 84 },
  'agent-detail': { kind: 'app', cls: 'WORKING', score: 84 },
  'about': { kind: 'marketing', cls: 'RECORD', score: 84 },
  'auth': { kind: 'marketing', cls: 'RECORD', score: 84 },
  'product': { kind: 'marketing', cls: 'WORKING', score: 84 },
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

phase('Refine')
function refinePrompt(p) {
  const tier = p.kind === 'marketing' ? 'marketing page (stripe.com / linear.app tier)' : 'app screen (Linear/Raycast tier)'
  const push = p.score >= 87
    ? `You are at R4 ${p.score} — within ONE move of a genuine 90 (top-0.1%). After fixing your r4 bugs, make the SINGLE highest-leverage craft move the jury named to cross 90: a sharper editorial hierarchy, a more crafted/singular signature moment, or a more memorable Sidira-only figure. Confidence and restraint — make it feel inevitable.`
    : `You are at R4 ${p.score}. Your r4 issues include REAL bugs/law-breaks (not just taste) — fix those FIRST and completely, then make one craft move toward 88+.`
  return `You are a top-0.1% product designer on the TERMINAL refinement round (R5) of Sidira's "Reading Console" system. Repo root: /Users/ram/Projects/sidira-simulator. This is a ${p.cls}-class ${tier}.

EDIT design-rethink/mocks/${p.id}.html IN PLACE. Keep what works; regress NO passing law.

READ FIRST:
- design-rethink/council/r4-critique.json  (your "${p.id}" entry: score, verdict, issues[] — these are your exact targets; several are concrete bugs/law-breaks, treat them as must-fix)
- design-rethink/system/design-system-v2.md and design-rethink/system/design-system-v2.1-patch.md (P1..P10 mechanical pass/fail — obey ALL; a break caps the page at 85)
- design-rethink/mocks/${p.id}.html

${push}

HARD MUST-FIXES (if any apply to your page, they are law-breaks or category errors — fix completely):
- P2/§1.9: a primary CTA (Sign in, New X, Create) must NOT carry lime/--signal unless it initiates a LIVE reading. Lime = live reading only.
- No A/B "control/treatment" arm semantics or "reaction" behavior on a CLUSTERING/persona-build step (no experiment exists yet there) — recolor by perceptual ramp, describe real cluster traits.
- No fictional placeholder names that borrow real-person authority (e.g. a "Kohavi" co-founder) — use a plainly fictional or generic role, never a name a buyer would recognize as borrowed.
- Decorative "distribution" posters must be REAL binned histograms (one mark per agent / stepped density), never smooth hand-drawn bezier blobs — the viz must be genuinely interrogable.
- Signature figures must be LEGIBLE at their rendered size (size up, add an arm/color key, or annotate the gap) — an illegible signature is not a signature.
- Replace mock-grade inline style= overrides with classes; fix any undefined CSS var(--token) fallback.

Also run the global P7 sweep (uncalibrated WORDS/labels → --text-mut #929BAE; reserve --spread-dim/#90815F for the ◇ glyph + ± value only; --text-faint disabled-only).

Self-contained HTML (inline style + inline canvas/SVG, optional CDN fonts). Write with the Write tool. Return ONLY {id:"${p.id}", changed:true}.`
}
const fixed = await inBatches(PAGES, 4, (p) => agent(refinePrompt(p), { label: `refine:${p.id}`, phase: 'Refine', schema: MOCK_SCHEMA }))
log(`refined ${fixed.filter(Boolean).length}/${PAGES.length}`)

phase('Critique')
function critiquePrompt(p) {
  const tier = p.kind === 'marketing' ? 'marketing page on earth (stripe.com / linear.app tier)' : 'app screen on earth (Linear/Stripe/Vercel/Raycast tier)'
  return `You are an independent top-0.1% design juror. Rigorous, specific, hard to impress; do NOT flatter or inflate. Repo root: /Users/ram/Projects/sidira-simulator.

Read design-rethink/mocks/${p.id}.html, design-rethink/system/design-system-v2.md, design-rethink/system/design-system-v2.1-patch.md. Score 0-100 CALIBRATED: 100 = indistinguishable from the single best ${tier}; 90 = clearly top-0.1% (an elite designer ships it as-is, proud); 80 = strong/premium but not elite; 50 = competent. A 90 is EARNED — most premium work is 82-88; award 90+ ONLY if you genuinely cannot name a craft or law deficiency that a Linear/Stripe designer would fix before shipping.

MECHANICAL LAW CHECK (any break caps at 85): P1 logo ink · P2 one signal carrier/region, signal=live-reading only (CTAs that don't start a reading are ink) · P3 only status dot loops · P4 drift ≤2px · P5 static posters --signal-dim · P6 verdict gated on calibration · P7 --text-faint disabled-only + AA provenance · P8 candor scope both ways · P9 live field showpiece-only & never twice · P10 marquee reading legible focal point. Also: real binned viz (not bezier blobs), no borrowed-authority fake names, legible signature figures, edited-down not over-instrumented, system-grade markup.

Return {id:"${p.id}", score, verdict (one line), topIssues (<=3 concrete fixes; [] only if genuinely 90+ with no nameable deficiency)}.`
}
const critiques = (await inBatches(PAGES, 6, (p) => agent(critiquePrompt(p), { label: `judge:${p.id}`, phase: 'Critique', schema: CRITIQUE_SCHEMA }))).filter(Boolean)

const scores = critiques.map(c => c.score)
const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
const topCount = scores.filter(s => s >= 90).length
const near = scores.filter(s => s >= 87).length
const sorted = [...critiques].sort((a, b) => b.score - a.score)
log(`ROUND 5: avg=${avg}, >=90=${topCount}, >=87=${near}, range=${sorted[sorted.length-1].score}-${sorted[0].score}`)

return { round: 5, avg, topCount, near, total: critiques.length,
  pages: sorted.map(c => ({ id: c.id, score: c.score, verdict: c.verdict, topIssues: c.topIssues })) }

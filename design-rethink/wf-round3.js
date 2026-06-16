export const meta = {
  name: 'design-council-round3',
  description: 'Round 3: per-page law-enforcement + targeted fixes (each page fixes its own R2 juror issues + v2.1 patch), full rebuild of simulation-results, re-critique 0-100',
  phases: [
    { title: 'Fix', detail: 'per-page agents fix their cited R2 issues + universal v2.1 law patch (batched x4)' },
    { title: 'Critique', detail: 'per-page jurors re-score on calibrated 0-100' },
  ],
}

// page -> {kind, cls, rebuild, issues[]}  (issues = the page's own R2 juror topIssues, condensed)
const P = {
  'simulation-results': { kind: 'app', cls: 'SHOWPIECE', rebuild: true, issues: [
    'This file is STILL the R1 version (its R2 rebuild failed). Rebuild it fully to v2 + v2.1 as the simulation-results SHOWPIECE.',
    'P6 verdict gate: the reading is uncalibrated (◇, LEDGER EMPTY) yet shows "HIGH SIM AGREEMENT · SHIP CANDIDATE" in 3 places. Replace with hedged "DIRECTIONAL +X ±Y ◇" / "TEST FIRST ◇"; gate SHIP wording on graded ◆ state only.',
    'P2/P5 signal budget: .verdict-tag/.vchip use --signal + lime dot + lime border to mean good/ship (the deleted --verdict-ship leak) and add a 2nd lime carrier competing with the field mean. Render verdict ink+glyph; one carrier per region.',
    'P7 contrast: persona ids (.pid), "/" separators, axis end-labels (0/384), "TERMINATED 31%" use #646E84 (disabled-only, <AA). Use --text-mut #929BAE. Replace hardcoded v1 #8A93A6 with #929BAE.',
  ] },
  'crawl-setup': { kind: 'app', cls: 'WORKING', issues: [
    'P2 signal budget: the audit rail carries THREE resting signal sources — the full lime .btn.live border+text, the run-pulse .dot, and the --signal-dim progress fill. Make the running dot the SOLE carrier: in-flight button → ink/disabled chrome (no lime border), progress fill → --text-mut.',
    'P8 candor scope: ◇ trails identifiers with no inferred reading — "cr-924718…699c21 ◇ UNCAL" in topbar, "2026-W26 ◇" in rail-head. Drop ◇ from id chips; carry uncalibrated state ONCE via the provbar region marker.',
    'Provenance redundancy: topbar RUNNING dot + UNCAL duplicates the rail run pulse/progress/CI-link in one viewport. Make the topbar a quiet global pointer (id, no second pulsing dot); let the rail own the live pulse.',
  ] },
  'app-shell': { kind: 'app', cls: 'WORKING', issues: [
    'P9 impact budget (the cap): the full-bleed 30fps WebGL Population Field runs on the app-shell/dashboard, which v2 classes WORKING ("Everywhere else — NO Population Field"). REPLACE the live field with a static Tier-3 SVG distribution poster (or a single isolated-particle motif). Reserve the live field for results/evaluate/manifest. Let the +6.2pp reading + bets list dominate.',
    'P2 signal budget: the topbar carries TWO lime carriers — the running .dot (legit) AND the lime .ch "CH5" text in .run-ref. Keep the dot; demote CH5 to --text/--text-mut.',
    'P3 motion: the count-up + drift→wavefront→re-sort→settle→dissolve loop runs perpetually behind a working bets list. Run the bet ONCE on entry then hold the settled poster — nothing loops except the status dot.',
  ] },
  'persona-detail': { kind: 'app', cls: 'RECORD', issues: [
    'P8 candor scope: the Behavioral-snapshot dl renders INFERRED per-segment rates/means (skip 0.09, ad tolerance 0.21, offline downloads 0.74, avg session 41.8) bare, captioned "RECORDED FACTS". A k-means centroid/mean is inferred, not a fact. Attach a compact Spread Stamp (value + ◇ + within-segment ±) to the snapshot metrics; keep tenure/plan-tier/n bare.',
    'Disambiguate the share chips (31%/38%): headcount share (769/2480) is a defensible count, but an order-weighted share is a weighted estimate — mark the weighted share with the spread treatment, or drop the blanket "recorded facts" claim.',
    'P10 focal reading: with no signal carrier (correct for RECORD) and 3 near-identical cards the first viewport reads monotone. Give the masthead figure (cluster stability 0.81 ±0.06) more typographic weight so the one inferred number is the page focal reading.',
  ] },
  'product': { kind: 'marketing', cls: 'WORKING', issues: [
    'Hero has no focal climax: the artifact browser reads as a docs widget and its one living visual (the distribution poster) is hidden behind the non-default "Cohort reaction" tab. Surface the poster in the default view, or give the hero one quiet but arresting focal reading.',
    'Repetitive proof texture: hero PRD/Figma tabs + symmetry two-column compare + specs grid are ALL mono key:value blocks reading as one YAML dump scrolled 3x. Vary the texture (one prose/diagram treatment).',
    'P8 candor smudge: "240 ◇ ±18 grounded" juxtaposes the bare raw count n=240 against a ± and ◇ so it parses as a ± on n (exempt). Move n into the bare provenance bar; lead the figure with the inferred reaction score (e.g. "0.xx ±0.0x ◇").',
  ] },
  'simulations-new': { kind: 'app', cls: 'SHOWPIECE', issues: [
    'P3 motion: the signal wavefront sweeps on a continuous loop (time*0.13 % 1.7) — perpetual decorative lime. Make it a ONE-SHOT firing on field re-seed/focus/chip-change, then rest to pure curl-drift. Idle = drift only.',
    'P4 drift: driftAmp = 16px is 8× the 2px ceiling. Halve repeatedly to ≤2px so the field reads as breathing, not churning, and the freeze-on-gaze cue lands against a quiet baseline.',
    'P2 texture: uppercase-mono designators used as ambient texture (region-label tails "FALSIFIABLE PROSE"/"CAPABILITY + STIMULUS", all-caps ctrl-foot, all-caps .est block). Demote editorializing tails to sentence-case ink; reserve mono-UPPER for true machine ids (slice, seed, n).',
  ] },
  'landing': { kind: 'marketing', cls: 'SHOWPIECE', issues: [
    'P2 signal budget (hero + closer): the lime field is the region carrier, yet the same viewport adds a lime-bordered/lime-text/lime-pulsing-dot .btn-live CTA (and the closer adds a lime eyebrow .dot). Render hero/closer CTA as ink (.btn-primary) or spread-outlined; drop the lime closer .dot. Field is the sole lime in those regions.',
    'P9 one showpiece: two full-bleed infinitely-looping Population Fields (hero #field + closer #field2) put the signature on the page twice. Make the closer a quiet ink/hairline CTA band (or at most a frozen static poster); the live field is the hero alone.',
    'P3 motion: verdict count-up runs 600ms where §5.3 specs verdict commit at 300ms. Tighten to 300ms --ease-mech.',
  ] },
  'auth': { kind: 'marketing', cls: 'RECORD', issues: [
    'P7 contrast: provenance/spread text (±0.06, ◇ UNCALIBRATED, ◇ UNCAL) renders in --spread-dim #90815F at ~3.4:1 on console bg — below AA for 11px. Bump the UNCALIBRATED word/label to --text-mut (5.4:1); reserve #90815F strictly for the ◇ glyph + ±value, not running words.',
    'P1/P2 two lime in stage-top region (logo mark stroke #48EFCA + breathing status dot). Desaturate the resting logo mark (--text-hi/arm tints); only the live dot carries lime.',
    'The left "Resting agreement 0.58 est" + control/treatment swatches manufactures a live comparison reading on an auth surface (the "performs intelligence" tell). Keep the drift atmosphere but drop the arm swatches + comparison framing; a single uncalibrated cohort-size/temperature reading is honest without implying a bet already ran.',
  ] },
  'personas-list': { kind: 'app', cls: 'WORKING', issues: [
    'P5 static poster: the poster trace is drawn in full --signal (#48EFCA) on a figure stamped "STATIC FIGURE · NO READING RUNNING". Demote #distline2 stroke to --signal-dim #39B894 — lime is never on a non-live surface.',
    'P2 signal budget: thead .sortarrow uses --signal-dim as a pure sort affordance (decorative). Recolor to --text-mut/--text-hi so the logbook region carries no false carrier.',
    'P2 one carrier in poster: the bright trace AND the drifting +0.16 mean both court the eye. Let the drifting ◇ mean be the inferred focus; render the curve quiet dim ink.',
  ] },
  'personas-new': { kind: 'app', cls: 'SHOWPIECE', issues: [
    'P2 signal budget: inside the field-frame the lime mean/wavefront IS the carrier, yet the legend renders "CH1" in --signal (.field-legend .ch) too. Recolor the CH1 legend label + μ-context chrome to --text-mut/--spread; lime reserved for wavefront + settled mean.',
    'P8 candor scope (build log): "STABILITY 0.68 · k=6" and "0.71 · k=7" are inferred readings printed bare while the hero correctly wears "±0.04 ◇". Stamp the log stability values with ± and ◇ (or drop the value, keep only k).',
    'P10 showpiece under-earns: it is a Canvas-2D 1-D scatter with a faint grid + thin mean line — reads as particle-settle, not the depth/wavefront/phosphor "stop scrolling" moment the SHOWPIECE budget reserves. Add genuine binned depth + a stronger settle/wavefront beat (≤18% bloom) so the one earned spectacle lands.',
  ] },
  'feature-pack': { kind: 'app', cls: 'WORKING', issues: [
    'P1 (the cap): the rail logo mark renders in #48EFCA (stroke + filled inner circle) — a resting signal carrier in a non-reading region. Recolor the mark to --text-mut/--console-line; signal exclusively on the hero coverage figure.',
    'P2 logbook discipline: every graded row uses --signal-dim twice (covbar .fill.graded AND the ◆ glyph) with 4+ rows visible. Drop signal-dim from the covbar fill (use --text-mut for the bar; let the ◆ glyph alone carry "graded").',
    'P10 hero dominance: the coverage well competes with a dense 147-row logbook + 3 stacked footer blocks. Collapse the stale-snapshot note to one inline caution line; let the coverage well claim more vertical dominance in the first viewport.',
  ] },
  'simulations-list': { kind: 'app', cls: 'WORKING', issues: [
    'P1 (the cap): the rail logo mark rests in lime (#48EFCA ring+core) in the persistent nav — forbidden; DESIGN.md reserves dual/lime brand for brand-mode surfaces only. Recolor to --text-hi/--signal-dim ink.',
    'P2 semantic leak on .btn-run: "New hypothesis" wears the signal border+text, but the lime button is scoped to one that initiates a LIVE reading. Make it .btn-secondary (ink); reserve lime for a Run/Read-now control.',
    'P3 motion: two infinite breath loops in one viewport (topbar .live-dot + table .chip .rdot, both 2s). Collapse the row live signal to a single carrier; let the global topbar dot be the one pulse.',
  ] },
  'agent-detail': { kind: 'app', cls: 'WORKING', issues: [
    'P3 motion (the cap): the .composing 4-bar cwave equalizer is a decorative infinite loop beyond the ONE sanctioned status-dot breath. Replace with the single 2s breathing dot + a static "… COMPOSING" label.',
    'P8 candor scope: "vs cohort mean ↑ +0.33 above" is an inferred difference of two estimates printed with no ± and no ◇ while siblings carry stamps. Render "+0.33 ±0.NN ◇" (or drop the bare directional claim).',
    'P1 cumulative signal: lime appears as the rail brand mark (#48EFCA), active-tab bar, LIVE pill, motif hero dot, poster mark, composing bars. De-lime the rail logo to ink/spread; let only the LIVE pill + single motif dot carry signal above the fold.',
  ] },
  'about': { kind: 'marketing', cls: 'RECORD', issues: [
    'Over-narrates its thesis: candor is stated 3× (well-note, law §◇, ledger-foot). Cut to ONE assertion (the ledger-foot); let the bare-vs-± rows demonstrate it silently.',
    '§7.4 prose: pitch lines ("an honest band than a confident lie", "spectacle second"), heavy em-dashes, drop-cap + italic lede + serif law-list read as editorial theater. Rewrite to calm lab-notebook register; cut em-dash density.',
    'Invented glyphs ✦ and ◈ are not in the vocabulary (only ◇/◆ defined). Drop the ornamental glyphs (plain hairline grouping); reserve ◇/◆ strictly for calibration state.',
  ] },
  'capability-detail': { kind: 'app', cls: 'RECORD', issues: [
    'P10 inverted hierarchy: the marquee figure 0.71 ±0.05 (the page reason-to-exist) renders at opacity:.45 and drifts at rest, so it is the FAINTEST element while exempt facts/prose sit at full ink. Lift the resting hero to ~0.7 (stamp/glyph full); keep only the ≤2px drift as the uncalibrated cue.',
    '§3.2 the dark well packs five sub-regions (provenance bar + hero fig + 3-stat strip + poster + legend) into the page ONE dark inset, fighting the 80%-quiet RECORD mandate. Demote the 3-stat strip to a single summary line or move it into the Sheet meta-grid; the well carries one reading.',
    'P10 poster readability: arms at 0.42α in a 148px box collapse into texture; legend is glyph-soup. Raise arm opacity ≥0.6, add a baseline + mean label (or an honest small-multiple) so the settled distribution is interrogable.',
  ] },
  'agent-transcript': { kind: 'app', cls: 'WORKING', issues: [
    'The iso-particle canvas is the page one lime carrier yet sits beside the dominant hero reading as a quasi-decorative flourish competing for the eye. Shrink it (≤72px, no phosphor trail, settle-once-then-static) or drop it.',
    'The reading-strip is four co-equal cells with no dominant figure. Lead with the consensus verdict (TEST FIRST ◇) or the lift as the primary figure; demote adopt/reject + sentiment to a secondary line so the region has a clear focal point.',
    'Grid deviates from the locked spec (§3.3 app shell max-width 1320px) to 1120px with no DESIGN.md note. Either restore 1320px or add a one-line documented-deviation comment in the file.',
  ] },
}

const PAGES = Object.keys(P).map(id => ({ id, ...P[id] }))

const MOCK_SCHEMA = { type: 'object', properties: { id: { type: 'string' }, changed: { type: 'boolean' }, summary: { type: 'string' } }, required: ['id', 'changed', 'summary'], additionalProperties: false }
const CRITIQUE_SCHEMA = { type: 'object', properties: { id: { type: 'string' }, score: { type: 'number' }, verdict: { type: 'string' }, topIssues: { type: 'array', items: { type: 'string' } } }, required: ['id', 'score', 'verdict', 'topIssues'], additionalProperties: false }

async function inBatches(items, size, fn) {
  const out = []
  for (let i = 0; i < items.length; i += size) {
    const res = await parallel(items.slice(i, i + size).map((it, j) => () => fn(it, i + j)))
    out.push(...res)
  }
  return out
}

// ===== PHASE A (inline, no agent): v2.1 patch already written by the director-of-record =====
// ===== PHASE B: per-page targeted fixes =====
phase('Fix')
function fixPrompt(p) {
  const issues = p.issues.map((s, i) => `${i + 1}. ${s}`).join('\n')
  const tier = p.kind === 'marketing' ? 'marketing page (stripe.com / linear.app tier)' : 'app screen (Linear/Raycast tier)'
  const action = p.rebuild
    ? `FULLY REBUILD design-rethink/mocks/${p.id}.html from scratch (its R2 rebuild failed; it is STILL the R1 file). Write a single self-contained HTML file.`
    : `EDIT design-rethink/mocks/${p.id}.html IN PLACE — keep everything that works, surgically fix the issues below. Do NOT regress passing laws.`
  return `You are a top-0.1% product designer doing Round 3 (law-enforcement + targeted polish) on Sidira's "Reading Console" system. Repo root: /Users/ram/Projects/sidira-simulator. This is a ${p.cls}-class ${tier}.

${action}

READ FIRST:
- design-rethink/system/design-system-v2.md  (the system)
- design-rethink/system/design-system-v2.1-patch.md  (the LAW-ENFORCEMENT PATCH — P1..P10 are mechanical pass/fail; obey ALL of them; where the page conflicts, the patch wins)
- design-rethink/mocks/${p.id}.html  (current mock)

FIX EXACTLY THESE R2-jury issues for ${p.id} (each cites the patch law it breaks):
${issues}

ALSO sweep the whole file against the v2.1 patch checklist P1..P10 and fix any other instance of the same class of defect (e.g. if P1 says the resting logo is ink, make EVERY resting brand mark ink; if P3 caps infinite loops to the status dot, kill every other looping animation). Realistic Sidira content, self-contained HTML (inline style + inline canvas/SVG script, optional CDN fonts). Write the file with the Write tool. Return {id:"${p.id}", changed, summary of exactly what you changed mapped to P-laws}.`
}
const fixed = await inBatches(PAGES, 4, (p) => agent(fixPrompt(p), { label: `fix:${p.id}`, phase: 'Fix', schema: MOCK_SCHEMA }))
log(`fixed ${fixed.filter(Boolean).length}/${PAGES.length} mocks`)

// ===== PHASE C: re-critique =====
phase('Critique')
function critiquePrompt(p) {
  const tier = p.kind === 'marketing' ? 'marketing page on earth (stripe.com / linear.app tier)' : 'app screen on earth (Linear/Stripe/Vercel/Raycast tier)'
  return `You are an independent top-0.1% design juror. Rigorous, specific, hard to impress; do NOT flatter. Repo root: /Users/ram/Projects/sidira-simulator.

Read design-rethink/mocks/${p.id}.html, design-rethink/system/design-system-v2.md, and design-rethink/system/design-system-v2.1-patch.md. Score 0-100 CALIBRATED: 100 = indistinguishable from the single best ${tier}, 90 = clearly top-0.1%, 75 = strong/shippable but not elite, 50 = competent, 25 = generic.

MECHANICAL LAW CHECK (any one break caps the score at 85): P1 resting logo is ink not lime · P2 exactly one signal carrier per region (signal=live reading only, never positive/ship/up/create) · P3 only the status dot loops forever · P4 drift ≤2px · P5 static posters use --signal-dim not bright --signal · P6 verdict vocab gated on calibration (no SHIP on ◇) · P7 --text-faint disabled-only / provenance clears AA · P8 candor scope both ways (± on inferred incl. logs/deltas; bare on ids/timestamps/seeds/n) · P9 live field is showpiece-only (4 pages) and never twice · P10 the marquee reading is the legible focal point. Also judge raw craft, hierarchy, breathing room, and whether it would stop a top designer scrolling.

Return {id:"${p.id}", score, verdict (one line), topIssues (<=3 specific concrete fixes; empty only if genuinely top-0.1%)}.`
}
const critiques = (await inBatches(PAGES, 6, (p) => agent(critiquePrompt(p), { label: `judge:${p.id}`, phase: 'Critique', schema: CRITIQUE_SCHEMA }))).filter(Boolean)

const scores = critiques.map(c => c.score)
const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
const topCount = scores.filter(s => s >= 90).length
const sorted = [...critiques].sort((a, b) => a.score - b.score)
log(`ROUND 3 critique: avg=${avg}, top-0.1%(>=90)=${topCount}/${critiques.length}, weakest=${sorted.slice(0,4).map(c=>c.id+':'+c.score).join(' ')}`)

return {
  round: 3,
  avg,
  topCount,
  total: critiques.length,
  fixed: fixed.filter(Boolean).map(r => ({ id: r.id, changed: r.changed, summary: r.summary })),
  pages: sorted.map(c => ({ id: c.id, score: c.score, verdict: c.verdict, topIssues: c.topIssues })),
}

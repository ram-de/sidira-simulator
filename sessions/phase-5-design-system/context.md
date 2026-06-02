---
type: session
domain: phase-5-design-system
status: active
started: 2026-06-02
owner: ram-de
---

# Session: phase-5-design-system — Sidira brand & design system consultation

## Goal
Lock a complete design system for Sidira (DESIGN.md as source of truth) covering aesthetic, typography, color, spacing, motion, the wordmark, and the logomark — before sidira.ai's public homepage and `app.sidira.ai` get any more visual layer added. Output: production-ready `DESIGN.md` at repo root + a polished preview HTML page.

## In Progress
- [ ] Iterate on the logomark concept — user verdict: "the sidira logo is not good". Current proposal (incomplete 6-blade aperture w/ 14° gap at top-right) needs rethinking. Likely candidates to explore next: (a) different mark direction entirely — wavefront-with-leading-dot (Codex's pick), abstract delphic tripod, plumb-line/sightline, sigma-as-signal; (b) keep aperture but reconstruct it (true diaphragm with overlapping triangular blades rather than spokes; or single-line iris ring with one gap; or aperture-as-eye-with-readout-tick).
- [ ] Iterate on the wordmark — user verdict: "average". Current proposal (lowercase `sidira` in Söhne Breit, −10 tracking, with 2px lime square replacing dot of second `i`). Needs distinctive typographic move beyond the lime-square dot trick. Options to explore: (a) custom letterform on one glyph (the `d`, or a ligatured `ir`); (b) bespoke geometric construction (every letter drawn on a 6-unit grid); (c) different base typeface — Berkeley Mono lowercase, GT America Mono, Söhne Mono, or a serif (GT Sectra Fine subagent's call); (d) typographic mark fusion — the logomark replaces a glyph entirely (e.g., the `o`-shape doesn't exist in sidira, but the aperture could replace one of the `i`s as a glyph).

## Completed
- [x] Drafted full design brief for /design-shotgun / /design-consultation seed (etymology = Pythia/oracle DNA, posture = JPL telescope not tarot deck, buyer = VPs of Product at $50M-$5B SaaS/consumer, lineup peers = Linear/Vercel/Statsig/Retool/Observable, anti-slop rules locked).
- [x] Memorable-thing locked: "This looks like an instrument, not software." Drives every subsequent design decision.
- [x] Ran /design-consultation skill end-to-end through Phase 5 preview.
- [x] Captured competitive references (browse screenshots saved to `/tmp/sidira-research/`: linear.png, vercel.png, observable.png, statsig.png).
- [x] Codex design voice consulted (proposed: Söhne Schmal display, signal cyan #3DD4D8, wavefront-with-leading-dot logomark, austere-instrument posture).
- [x] Claude subagent consulted (proposed bolder direction: GT Sectra Fine serif display, signal lime #D4FF3A, incomplete-aperture logomark with 14° gap, seismograph-trace motion bet, "no gradients anywhere ever").
- [x] Synthesized all three voices into a single coherent system proposal with explicit SAFE vs RISK breakdown.
- [x] User approved full system proposal — locked: signal lime #C8FF3D accent, ink #0E1A2B / paper #F4EFE6, Söhne for body + Berkeley Mono for data + GT Sectra Fine reserved for marketing hero only, 4/8/12/16/24/32/48/64 spacing scale, 4px max radius, 800ms settle-trace motion bet for confidence-score numerics.
- [x] OpenAI mockup path blocked (no API key configured); fell back to Path B HTML preview.
- [x] Built `/tmp/sidira-design-preview.html` — full design-system showcase: wordmark at multiple scales, 4 mark variations (96/48/16/inverted), type specimens, color palette swatches, UI components (buttons/inputs/chips), full result-page product mockup (hypothesis header + settled lime trace at 73 + paired-lift stats + 3 weaknesses w/ Wilson CIs + 6 personas w/ sentiment waveforms), motion bet demo, spacing scale, dark mode toggle. Used Geist + JetBrains Mono + Instrument Serif as free stand-ins for Söhne / Berkeley Mono / GT Sectra Fine.
- [x] User feedback received: page fonts + backgrounds GOOD. Logo NOT GOOD. Wordmark AVERAGE. Iterate before writing DESIGN.md.

## Next Steps
1. Explore 4–6 alternative logomark directions (rendering them as inline SVG in a comparison-grid HTML, like `/design-shotgun` would). Candidates: (a) wavefront-with-leading-dot (Codex's original pick), (b) reconstructed aperture (proper overlapping triangular diaphragm), (c) single-line iris ring with one gap, (d) abstract delphic tripod (3 thin lines converging on a point), (e) plumb-line/sightline (vertical hairline + crosshair), (f) sigma-as-signal-waveform.
2. Explore 4–6 wordmark treatments alongside: (a) Söhne Breit with different custom move (custom `d` terminal, ligatured `ir`, glyph swap), (b) Berkeley Mono lowercase (instrument-panel typography), (c) GT Sectra Fine lowercase italic (editorial gravitas), (d) custom geometric construction, (e) mark+glyph fusion (logomark becomes one of the `i`s), (f) all-caps narrow display cut (Söhne Schmal Halbfett SIDIRA).
3. Render all variations in a single comparison-grid HTML at `/tmp/sidira-logo-shotgun.html`, open in browser, collect user verdict.
4. Once user picks a direction (or remixes across variants), refine to final + bake into the design preview page.
5. Then write `DESIGN.md` to repo root with locked spec + production font sources (Söhne, Berkeley Mono, GT Sectra Fine) + the logomark as inline SVG + wordmark construction notes.
6. Update `CLAUDE.md` with the "Always read DESIGN.md before visual/UI decisions" routing block.
7. Commit DESIGN.md + CLAUDE.md update on a feature branch, open PR via `mcp__github_ramde__create_pull_request`, /codex review, /ship.

## Key Files
- `/tmp/sidira-design-preview.html` — current full design-system preview (fonts + colors APPROVED; logo + wordmark REJECTED, to be iterated)
- `/tmp/sidira-research/` — competitive reference screenshots from Linear / Vercel / Observable / Statsig
- `~/.gstack/projects/ram-de-pythia-simulator/designs/design-system-20260602/` — design artifacts directory (currently empty since the OpenAI mockup path failed)
- `DESIGN.md` — TO BE CREATED at repo root once logo/wordmark lock
- `CLAUDE.md` — TO BE UPDATED with DESIGN.md routing block

## Key Context

### Locked design decisions (do not re-litigate without explicit reopen)
- **Memorable-thing:** "This looks like an instrument, not software." North star for every subsequent choice.
- **Aesthetic:** Industrial/Utilitarian × Editorial. 1960s research instrument rebuilt in software. Archival-paper surfaces under tungsten light.
- **Palette:** ink `#0E1A2B` / paper `#F4EFE6` / paper-elevated `#FAF6EE` / paper-recessed `#EBE5D8` / rule `#D6CFC0` / **signal `#C8FF3D` (lime)** / alert `#E84A2C` / warn `#D9A300`. Lime ≤8% of any rendered surface, never as fill, never as background, never as hover. Used only on live traces, the active state of one control, and the wordmark detail.
- **Typography production stack:** Söhne (display + body + labels), Berkeley Mono (data + numerals + timestamps + cohort IDs), GT Sectra Fine (marketing hero ONLY — never in the app). Preview substitutes Geist / JetBrains Mono / Instrument Serif since the production fonts are commercial.
- **Spacing scale:** 2/4/8/12/16/24/32/48/64. The 12-step is load-bearing. Tighter than the SaaS default — gives Sidira its instrument-panel density.
- **Radius:** 2px inputs, 4px cards, 6px modals max. No pills. No `border-radius: 9999px` anywhere.
- **Motion bet:** Numbers are traces, not spans. Confidence score and paired-lift settle as 800ms lime traces with `cubic-bezier(.34, 1.1, .64, 1)` easing. Every other numeric stays static + tabular.
- **Layout posture:** Dense, left-aligned, instrument-panel composition. Three persistent zones on every result page: hypothesis header / cohort + score / persona inspector.

### Open decisions (currently iterating)
- **Logomark direction.** Aperture-with-gap was the proposal. User rejected. Need 4–6 alternatives rendered side-by-side.
- **Wordmark treatment.** Lowercase Söhne Breit + lime-square dot-of-`i` was the proposal. User: "average." Need typographic distinctiveness beyond the dot trick.

### Why the logo + wordmark probably read weak in the preview
- The aperture as drawn was rendered as **spokes from center**, not a true camera diaphragm. Without overlapping triangular blades it reads as a half-finished pinwheel, not an instrument iris.
- The wordmark uses Geist (preview stand-in) which is too soft/Vercel-y for the "instrument panel" thesis. Söhne Breit in production would be tighter, but even with the right font the lime-square-on-`i` move is a one-trick and isn't enough to carry the mark on its own.
- The pairing of "geometric sans wordmark + abstract geometric mark" is the exact convergence trap of every B2B SaaS in 2024–2026 (every Y Combinator company has this lockup). Sidira needs at least one move that breaks from this template.

### Outside-voice raw outputs (reference for next iteration)
- **Codex** ([codex stderr log archived in conversation]): preferred wavefront-with-leading-dot mark, signal cyan #3DD4D8 accent, austere instrument-panel restraint, called out aperture as "over-indexed on cameras and observatories" and Delphic tripod as "drags into mythology."
- **Subagent** (full transcript in conversation, agent ID aa71953a8f1dff00b): proposed the seismograph trace motion bet (adopted), GT Sectra Fine for display (rejected in favor of sans-only app + serif-on-marketing), signal lime accent (adopted at #C8FF3D), incomplete-aperture-with-14°-gap mark (proposed, drawn weakly, now being re-explored), and a "every numeric is a live trace" big bet.

### Process gotchas hit
- `$D variants` (OpenAI-powered AI mockup gen) requires `OPENAI_API_KEY` or `~/.gstack/openai.json`. Not configured. Path B (HTML preview) works fine and is arguably better for a brand system anyway since AI image gen can't hit exact wordmark metrics.

## For my cofounder
Working through Phase 5 design-system consultation. Locked the system (aesthetic, palette, type, spacing, motion — see Key Context). User likes the page fonts + colors + product-mockup approach but rejected the logo (incomplete aperture w/ 14° gap) as "not good" and the wordmark (lowercase Söhne Breit + lime-square dot-of-`i`) as "average." Next: explore 4–6 alternative logomark + wordmark directions side-by-side via a shotgun-style comparison HTML, get a verdict, then write DESIGN.md. Preview page lives at `/tmp/sidira-design-preview.html` if you want to see what got rejected. Competitive reference screenshots in `/tmp/sidira-research/`. Do NOT re-litigate the lime accent, the paper/ink palette, the Söhne/Berkeley/Sectra type stack, the 4-12-16-24 spacing scale, or the 800ms settle-trace motion bet — all locked.

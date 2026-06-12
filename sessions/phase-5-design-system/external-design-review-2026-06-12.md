# External design review of DESIGN.md — 2026-06-12

Source: founder ran DESIGN.md (v0.2, post-R2) through Claude design review and pasted
the feedback into the session. Verbatim text in the second half of this file; triage
against current main first.

## Triage (2026-06-12, against DESIGN.md v0.2 on main)

Overall verdict from the reviewer: "top 5% of design docs I see" — the thesis, honest-numbers
rules (§8.3), verdict-without-policy primitive (§8.1), calibration-gated lexicon (§8.2), and
per-entry reduced-motion end states all called out as unusually strong. The critique is about
gaps and internal inconsistencies, not direction.

### Confirms a known internal finding (promote into the doc)

- **warn `#D9A300` fails as text on paper (~2–2.5:1).** Codex caught this during PR #174
  (R2.14); the fix — *warn is accent-only forever (bands/markers/borders), mid-range score
  text falls back to inkMuted* — was applied in code with comments at use sites but never
  promoted into DESIGN.md. The external reviewer independently hit the same wall. Action:
  encode the accent-only rule in §4.3 and the planned accessibility section.

### Real gaps — DESIGN.md v0.3 candidates (spec-only; no new product surfaces, so
### compatible with the R2.4 scope lock)

1. **Button spec** — doc bans what a button can't be but never says what the primary action
   IS (ink fill on paper? outlined?), nor links, disabled states, form validation errors.
   Every wizard form needs this.
2. **Accessibility section** — no focus-visible spec, no keyboard treatment, no contrast
   floor beyond lime-needs-ink-companion. State whether semantic colors are text colors or
   chip colors. Reviewer suggestion that fits the language: ink hairline offset focus ring.
3. **Verdict → token mapping** — §8.2 lexicon and §4.3 semantic tokens are never connected
   (UNDERPOWERED → warn? SHIP CANDIDATE → success or ink?). Most important component in
   the product; shouldn't be inferred per-PR.
4. **Table/register spec** — no row height, no alignment rule (numerals right-aligned
   tabular?), no density spec; telemetry key/value grid and provenance grid named but
   not drawn.
5. **Iconography** — no section at all; first place visual drift will appear.
6. **Breakpoints** — the threshold where the inspector rail becomes a stacked section is
   unspecified (§7.3 gives columns, §7.5 gives mobile posture, nothing in between).
7. **Type scale contradiction** — §5.2 tops at 64, but the same section calls for the
   84–96px reading numeral and §5.1 specs marketing display 64–96. Add 96 + the reading
   size to the scale, or mark hero sizes explicitly off-scale.
8. **sid-blue token gap** — §4.4 says not-a-token, but §9.2 aperture keyframes need the hex.
   Without scoped tokens (e.g. `--duo-sid` / `--duo-avira`) it gets hardcoded into animation
   CSS — exactly the drift §4.3 exists to prevent.
9. **0.75pt rules** — print unit; rounds to ~1px in CSS anyway. Spec as 1px with a hi-DPI
   note if true sub-pixel hairlines are wanted. (Appears 3× in v0.2: §4.3 rule token, §7.3,
   §7.x dividers.)
10. **Dark mode is half-specified** — a token table plus "saturation drops 15%" with no
    computed values invites premature implementation. Either compute the values or cut to
    one line ("inverts paper/ink; spec lands when scheduled").
11. **Lime ≤8% rule unenforceable as written** — restate as countable rules (max N elements
    per screen, never two adjacent, never as fill).
12. **§7.6 PRD-document typography referenced but undefined** — serif was dropped; what does
    a "record" document look like? Records are half the brand thesis.
13. **Spacing scale tops at 64** — marketing at 1280px needs 96/128 section rhythm or
    marketing pages will invent their own.

### Nits (cheap one-liners)

- Favicon duo-color vs §4.4 "no avira at first impression": add one acknowledgment line
  ("the favicon is a sanctioned exception because it's brand-mode, not product UI") to stop
  re-litigation.
- §8.4's 10px axis numerals sit exactly at the §5.2 floor — add "this is the floor,
  deliberately."

### Not reproducible / stale

- "README describes nav-by-feature (simulations route) while §7 mandates Hypotheses ·
  Library" — current root README has no nav/route description and there is no
  frontend/README.md; TopNav already merged (PR #174). No action.

### Open offer from the reviewer

Reviewer offered to (a) draft the missing sections (buttons + focus states, verdict→token
mapping, register/table spec) in the doc's own voice, or (b) build a visual artifact
(token sheet, type specimens, verdict chip family) to pressure-test the rules against
rendered reality. Founder's call whether to take that up or draft in-house as a
DESIGN.md v0.3 PR.

---

## Verbatim feedback

I read both files closely. This is a genuinely strong design doc — top 5% of what I see.
The "paper bench, glass display" thesis is doing real work: it's a single governing metaphor
that resolves ambiguous cases ("is this a reading or a record?"), which is what most design
systems lack. The honest-numbers rules (§8.3), the verdict-without-policy-never-renders
primitive (§8.1), and the calibration-gated lexicon (§8.2) are unusually mature — they encode
product integrity into the visual system. The refuse list is concrete and enforceable, and
declaring a prefers-reduced-motion end state per motion entry is rigor I almost never see.

Here's the critique, prioritized:

**Real gaps (things implementers will invent badly without you)**

- No button spec. The doc bans things a button can't be (avira fill, gradients, pills) but
  never says what the primary action is. Ink fill on paper? Outlined? What does the one
  signal-active control (§4.1) actually look like? Every form in the wizard needs this on
  day one. Same for links, disabled states, and form validation errors.
- No accessibility section. There's no focus-visible spec, no keyboard treatment, and no
  contrast floor beyond the lime-needs-an-ink-companion rule. Notably, warn #D9A300 on paper
  is roughly 2.5:1 — fails for text. State whether semantic colors are text colors or chip
  colors, and spec a focus ring (an ink hairline offset ring would fit the instrument
  language).
- No verdict → color mapping. §8.2 defines the lexicon, §4.3 defines semantic tokens, but
  nothing connects them. Is UNDERPOWERED → warn? Is SHIP CANDIDATE → success or ink? For the
  single most important component in the product, this shouldn't be inferred.
- No table/register spec. This is a data-dense product and the register is a core zone, yet
  there's no row height, alignment rule (numerals right-aligned tabular?), or density spec.
  The telemetry key/value grid and provenance grid are named but not drawn.
- No iconography section. Stroke icons matching the mark's weight? A specific set — most
  likely to produce visual drift first.
- No breakpoints. §7.3 gives columns and §7.5 gives mobile posture, but the threshold where
  the inspector rail becomes a section is unspecified.

**Internal inconsistencies**

- The type scale contradicts itself. §5.2 tops out at 64, but the same section calls for an
  84–96px reading numeral, and §5.1 specs marketing display at 64–96px. Add 96 (and the
  reading size) to the scale or note hero sizes as explicitly off-scale.
- sid-blue isn't a token but is required by CSS. §4.4 says it's not a system-wide token, but
  the §9.2 aperture animation needs it in keyframes. Without scoped tokens
  (e.g. --duo-sid / --duo-avira), the hex gets hardcoded into animation CSS — exactly the
  drift §4.3 exists to prevent.
- 0.75pt rules. pt is a print unit; in CSS it rounds to ~1px anyway. Spec it as 1px (with a
  hi-DPI note if you want true sub-pixel hairlines) so nobody ships 0.75pt literally.

**Judgment calls worth a second look**

- Dark mode is half-specified. It's declared a follow-on, but a token table plus a
  hand-wavy "saturation drops 15%" rule with no computed values. Half-specs invite premature
  implementation. Either compute the values or cut the table to one line: "inverts
  paper/ink; spec lands when it's scheduled."
- "≤ 8% of any rendered surface" for lime is unenforceable as written. Consider restating as
  countable rules: lime appears on at most N elements per screen, never on two adjacent
  elements, never as fill — which you mostly already have.
- PRD-document typography is referenced but undefined (§7.6). The serif was dropped, so what
  does a "record" document look like? Records are half the brand thesis; they deserve their
  own short section.
- Spacing scale tops at 64. Marketing at 1280px will need 96/128 section rhythm; without it,
  marketing pages will invent their own.

**Nits**

- The favicon being dual-color while §4.4 forbids avira "anywhere a buyer's first impression
  is being formed" is a tension you've resolved by enumeration, but a one-line
  acknowledgment ("the favicon is a sanctioned exception because it's brand-mode, not
  product UI") would stop the question from being re-litigated.
- §8.4's 10px axis numerals sit exactly at the §5.2 floor — fine, but worth saying "this is
  the floor, deliberately."
- The README and DESIGN.md agree well; the only mismatch is the README describes
  nav-by-feature (simulations route) while §7 mandates Hypotheses · Library — you've flagged
  the TopNav PR, so just make sure the README gets updated in that same PR.

If you want, I can draft the missing sections (buttons + focus states, verdict→token
mapping, register/table spec) in the doc's own voice, or build a visual artifact of the
system — token sheet, type specimens, the verdict chip family — so you can pressure-test
the rules against rendered reality.

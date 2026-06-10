---
type: session
domain: brand-goodies
status: active
started: 2026-06-10
owner: ram-de
---

# Session: brand-goodies — design Sidira merchandise (stickers, t-shirts, hoodies)

## Goal
Design a print-ready Sidira merch line (stickers, tees, hoodies) that extends DESIGN.md v0.2 "paper bench, glass display" onto physical goods, plus a lookbook for review.

## In Progress
- [ ] PR review + founder sign-off on the three open decisions (D-01 duo sanction, D-02 specimen numbers, D-03 vendor/Pantone)

## Completed
- [x] Merch design language locked (translation table: paper→natural cotton, glass→blackout navy, lime dark-goods-only, hex die-cut, traces-as-records)
- [x] 5 print-ready stickers: aperture hex (ink), aperture hex (duo, pending D-01), reading (lime trace on glass), verdict-with-policy, lockup strip
- [x] 2 apparel prints: decision-rule back print (single color via currentColor), settle-trace reading print (signal + paper, dark goods only)
- [x] Lookbook `lookbook.html` — tech pack with garment flats, in-place artwork, spec grids, production notes, open decisions; visually QA'd via headless Chrome (fixed: print overflow on glass garments, invisible construction lines on dark fills)
- [x] DESIGN.md §11 file-reference table updated with 8 merch rows

## Next Steps
1. Open PR (gh as ram-de), run codex review
2. Founder: resolve D-01/D-02/D-03 in the lookbook's Open Decisions section; if D-01 = yes, add merch to DESIGN.md §1.3 brand-mode list in a follow-up

## Key Files
- `DESIGN.md` — source of truth (v0.2, R2 "paper bench, glass display"); §11 table extended this session
- `frontend/public/brand/sidira-mark.svg`, `sidira-mark-duo.svg`, `sidira-lockup.svg` — canonical assets to reuse, never recreate
- `frontend/public/brand/merch/` — all new artwork + `lookbook.html` (open in a browser)

## Key Context
- Mark color law (§1.3): monochrome ink default; duo (Sid-blue + Avira-rose) only on brand-mode surfaces. **Open founder decision: is merch a brand-mode surface?** Working assumption: swag is public/brand-facing (like press kit / social avatar), so ONE duo item is sanctioned; everything else rests monochrome.
- Lime (§4.1): lives on glass (`#0A1421`); on paper it needs an ink companion ≥3:1. Translation to merch: lime ink only on dark garments/vinyl.
- Refuse list transfers: no gradients, no pills/fully-rounded die-cuts (hexagon die-cut is the brand shape), no drop shadows/bevels on the mark, wordmark uppercase always.
- "Decorative instrument marks" ban: any printed trace must read as a *record* of a plausible reading — axis-labeled, with provenance line — never a decorative waveform.

## For my cofounder
Merch line is designed and in the PR. Open `frontend/public/brand/merch/lookbook.html` in a browser — it's the whole tech pack: 5 stickers, 2 tees, 2 hoodies, production notes. Three decisions need your sign-off (bottom of the lookbook): duo sticker sanction, the specimen numbers (0.78 / 240 readings / 48 personas / 5 seeds), and blanks/vendor. Everything reuses the canonical mark geometry; nothing violates the §10 refuse list.

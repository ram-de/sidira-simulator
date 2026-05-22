# Continue Watching

## User goal
Let a returning subscriber resume the title they were last watching — at the exact playback position — in two taps or fewer from the home screen.

## Roles
- **guest** — Not signed in. Rail is hidden; surface degrades to a sign-in CTA.
- **trial** — Signed-in trialist (days 1-14). Same surface as `standard`, but eligible for an upsell chip on the rail header on day ≥ 7.
- **standard** — Paid subscriber, ad-free standard tier.
- **premium** — Paid subscriber on the higher tier (4K + multi-stream). Identical Continue Watching surface as standard — premium-only behavior lives in other capabilities.

## Flow per role

### guest
1. Lands on `/home`. Continue Watching rail is hidden.
2. A single placeholder card reads *"Sign in to pick up where you left off."*
3. Tap → routes to `/auth/login`. After successful auth, returned to `/home` and the relevant tier flow takes over.

### trial / standard / premium
1. Lands on `/home`. Continue Watching rail is the first rail below the hero, showing up to 10 titles sorted by most-recent-progress.
2. Each tile shows: title art, episode label (for series) or movie title, a thin progress bar, and remaining-time text.
3. Tap a tile → routes to `/player/<title_id>?t=<resume_seconds>` and playback starts immediately at the saved position.
4. Long-press a tile (TV) / tap the ⋯ (mobile) → opens a sheet with `Remove from row`, `Mark as watched`, `Start from beginning`.
5. For series tiles where the user finished an episode within the last 60 minutes, the tile auto-advances to the *next* episode and the label reads *"Next: S2 E4 — <episode title>"*.

## Success criteria
- Tap on a Continue Watching tile → `/player` reached and the first second of decoded video frames is rendered within 2.0s P75.
- Resume position is within ±3s of the last persisted position.

## Edge cases & failure modes
- **No titles in progress (trial / standard / premium)** — rail is replaced by a "Start something new" rail of editorial picks.
- **Title removed from catalog** — tile renders with a greyed thumbnail and copy *"No longer available"*; tap shows a brief toast and does not navigate.
- **Stale resume position (next-episode auto-advance misfires)** — the playback start position falls back to 0 and a small toast reads *"Starting from the beginning."*
- **Network failure on tile tap** — full-screen retry state with `Try again` and `Cancel`.

## Dependencies
- Upstream: `watch_progress` service (read), `catalog` (availability + episode metadata).
- Downstream: `player` capability — every successful resume enters `/player` and continues there.

## Implicit metric
Most likely optimized for **resume-to-play rate** (fraction of home-screen visits that result in a Continue Watching tap → playback) segmented by tier. Secondary attention to **next-episode handoff latency** for the auto-advance pathway, which heavy serial viewers experience constantly.

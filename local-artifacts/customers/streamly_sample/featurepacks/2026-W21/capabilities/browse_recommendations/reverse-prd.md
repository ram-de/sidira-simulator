# Browse Recommendations

## User goal
Help a signed-in subscriber discover a title worth watching tonight when they don't already know what they want.

## Roles
- **guest** — Home is replaced by an editorial landing page; personalized rows are hidden.
- **trial / standard / premium** — Identical recommendation surface; row composition is personalized to viewing history. Premium users additionally see a row of "Premium picks" (4K-only catalog) above the fold.

## Flow per role

### guest
1. Lands on `/home`. Hero is editorial, not personalized. Below the hero are two rows: `Trending now` and `Popular movies`.
2. Tap any title → `/title/<id>` detail screen, which prompts sign-in before playback.

### trial / standard / premium
1. Lands on `/home`. Below the Continue Watching rail, browse rows are arranged in this order:
   - `Because you watched <last completed title>` (only renders if a title was completed in the last 14 days)
   - `Top picks for you`
   - `Trending now`
   - `New releases`
   - One genre row keyed to the user's top genre over the last 90 days
2. Each tile shows title art, a small genre tag, and (for series) a season badge.
3. Tap a tile → `/title/<id>` detail screen.
4. From detail, `Play` button → `/player/<id>?t=0`. `+ My List` toggles list membership.
5. The hero rotates 3-5 personalized titles every 6 seconds; pausing on a card surfaces a preview trailer after 1.2s.

### premium (additive)
- A "Premium picks" row is inserted above `Top picks for you`. Tiles in this row carry a small `4K` badge.

## Success criteria
- Tap on a recommendation tile → `/title/<id>` reached.
- From detail, `Play` tap → `/player` and first decoded frame within 2.0s P75.
- Across a session, at least one personalized row produces a tile that ends in a play (row-level click-through to play).

## Edge cases & failure modes
- **Cold-start user (no completed titles)** — `Because you watched` row is suppressed; `Top picks for you` falls back to popularity-weighted defaults; one editorial row is added.
- **Trailer preview fails to load** — hero card holds on still art; no error UI.
- **Network failure on detail navigation** — inline error on the home rail rather than a screen-blocking modal.

## Dependencies
- Upstream: `recsys` service (row composition + ranking), `catalog` (title metadata), `watch_progress` (for personalization signals).
- Downstream: `title_detail` capability and ultimately the `player` capability.

## Implicit metric
Most likely optimized for **browse-session-to-play conversion** — the fraction of home visits without an obvious resume that end with a play. Secondary attention to **personalized-row CTR** (signal that the model is actually earning its keep over editorial fallbacks).

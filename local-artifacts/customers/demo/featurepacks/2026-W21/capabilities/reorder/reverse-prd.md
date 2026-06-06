# Reorder

## User goal
Let a returning user re-place a recent order — same items, same restaurant — in a single tap from the home screen or order history, without rebuilding the cart manually.

## Roles
- **guest** — Not signed in. Reorder rail is hidden; surface degrades to a sign-in CTA.
- **member** — Signed-in user without a subscription. Reorder available; standard delivery fees apply.
- **premium_member** — DashPass subscriber. Reorder available; zero delivery fee auto-applied at checkout.

## Flow per role

### guest
1. Lands on `/home`. Recent orders rail is hidden.
2. A placeholder card reads *"Sign in to reorder your favorites."*
3. Tap → routes to `/auth/login`. After successful auth, returned to `/home` and the relevant tier flow takes over.

### member
1. Lands on `/home`. "Order again" rail shows up to 5 most recent orders, sorted by recency.
2. Each tile shows: restaurant logo, order summary (e.g., "Pad Thai + Spring Rolls"), total, and days since order.
3. Tap **Reorder** → cart is pre-filled with the same items at current prices. A toast shows if any item is unavailable: *"2 items unavailable — removed from cart."*
4. Cart screen opens pre-filled. User can adjust quantities or remove items.
5. Tap **Place order** → standard checkout flow; delivery fee shown prominently.

### premium_member
1. Same flow as `member`, but the cart screen shows $0 delivery fee chip inline.
2. Reorder tile on home rail shows a "Free delivery" badge if the restaurant qualifies under DashPass.

## Success criteria
- Tap **Reorder** → cart pre-filled within 1.5s P75.
- Item availability check runs before cart opens; unavailable items removed with clear toast.
- Price accuracy: cart reflects current restaurant prices, not historical order prices.

## Edge cases & failure modes
- **Restaurant closed** — Reorder tile renders with greyed state and copy *"Closed now."* Tap shows ETA for next opening.
- **Restaurant no longer on platform** — tile hidden from rail; not surfaced even in order history reorder CTA.
- **All items unavailable** — toast reads *"This order can't be reordered right now — items unavailable."* Cart does not open.
- **Price change > 20% on any item** — a warning banner appears in cart: *"Prices have changed since your last order."*
- **Network failure on reorder tap** — inline error state with retry button on the tile.

## Dependencies
- Upstream: `order_history` service, `restaurant_catalog` (current availability + prices).
- Downstream: `checkout` capability — every successful reorder enters the cart/checkout flow.

## Implicit metric
Optimized for **reorder conversion rate** (fraction of home-screen sessions where a reorder tile is tapped and results in a completed order). Secondary metric: **cart modification rate** after reorder pre-fill (high modification = pre-fill quality issue).

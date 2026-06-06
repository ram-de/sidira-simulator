# Checkout

## User goal
Complete a food order with minimal friction — confirm address, apply promo, review total, and place order in under 60 seconds from cart.

## Roles
- **guest** — Not signed in. Checkout requires sign-in or guest checkout (email only). Promo codes not available for guest checkout.
- **member** — Signed-in user. Full checkout; standard delivery fees; promo codes accepted.
- **premium_member** — DashPass subscriber. Zero delivery fee auto-applied; promo codes stackable with DashPass benefit.

## Flow per role

### guest
1. Taps **Go to checkout** from cart.
2. Prompted: *"Sign in for faster checkout"* with email field below for guest checkout.
3. Guest path: enter delivery address → confirm payment (credit card only, no saved methods) → review total → **Place order**.
4. No promo code field on guest checkout.
5. Order confirmation screen shows order ID and estimated delivery time.

### member
1. Taps **Go to checkout** from cart.
2. Delivery address auto-populated from saved default; editable.
3. Payment method auto-selected from saved card; editable.
4. Promo code field visible (collapsed by default, expandable).
5. Fee breakdown: subtotal, delivery fee, service fee, taxes, tip.
6. Tap **Place order** → confirmation screen.

### premium_member
1. Same as `member` flow.
2. Delivery fee row shows $0 with a DashPass badge inline.
3. If a promo reduces another fee (e.g., service fee), the discount is itemized on the fee breakdown.
4. **Place order** → confirmation screen with DashPass savings summary.

## Success criteria
- Cart → confirmation in under 60 seconds for a returning member (saved address + payment).
- Fee breakdown visible before **Place order** tap — no surprises at confirmation.
- Promo code validation response within 1.0s after code entry.

## Edge cases & failure modes
- **Payment decline** — inline error: *"Your payment didn't go through. Please check your card details."* Order not placed.
- **Restaurant stops accepting orders mid-checkout** — error modal: *"This restaurant is no longer accepting orders. Your cart has been saved."*
- **Promo code invalid/expired** — inline error below code field: *"Code not valid or already used."* Does not block checkout.
- **Address outside delivery zone** — error before payment step: *"We don't deliver to this address from [Restaurant]. Change address or choose a different restaurant."*
- **Cart price changed since open** — banner at top of checkout: *"Prices updated since you opened your cart. Review the updated total."*

## Dependencies
- Upstream: `cart` service, `restaurant_catalog` (price + availability), `promo` service, `payment` service.
- Downstream: `order_tracking` capability — every successful checkout transitions to order tracking.

## Implicit metric
Optimized for **checkout completion rate** (fraction of checkout sessions reaching confirmation). Secondary: **abandonment step** — which step loses the most users (address / payment / total reveal / final tap).

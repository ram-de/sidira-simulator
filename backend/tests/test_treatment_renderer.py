"""Tests for services.treatment_renderer (agent-behavior-spec §1).

The renderer is pure and deterministic, so these are plain fixture-diff tests:
construct a current `Capability` and a proposed `Hypothesis`, assert the typed
changelog, the NOT-changing guard, the modality/reliability tags, and the two
output views (blinded standalone vs unblinded state+diff).
"""

from __future__ import annotations

from sidira_simulator.schemas.feature_pack import (
    Capability,
    Component,
    ReverseFigma,
    Screen,
    Transition,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.treatment_renderer import (
    _DEFAULT_FALLBACK_CHOICES,
    extract_choice_set,
    render_state_diff,
    summarize_reverse_figma,
)

# ── fixtures ────────────────────────────────────────────────────────────────


def _cart_screen(cta_text: str = "Buy now") -> Screen:
    return Screen(
        id="cart",
        name="Cart",
        components=[
            Component(id="checkout_cta", role="button", text=cta_text),
            Component(id="promo_code", role="input", text="Promo code"),
        ],
    )


def _account_screen() -> Screen:
    return Screen(
        id="account",
        name="Account",
        components=[Component(id="email", role="text", text="you@example.com")],
    )


def _capability(figma: ReverseFigma | None = None) -> Capability:
    return Capability(
        name="checkout",
        surfaces=["mobile"],
        roles=["guest", "member"],
        entry_points=["cart"],
        reverse_prd="The cart screen lets users confirm and pay.",
        reverse_figma=(
            figma
            if figma is not None
            else ReverseFigma(screens=[_cart_screen(), _account_screen()])
        ),
    )


def _by_kind_target(rc, kind, target_id):
    return [c for c in rc.changes if c.kind == kind and c.target_id == target_id]


# ── prose-only fallback ─────────────────────────────────────────────────────


def test_prose_only_when_no_proposed_figma() -> None:
    rc = render_state_diff(
        _capability(),
        Hypothesis(capability_name="checkout", prose="Make the tip selector bigger."),
    )
    assert rc.prose_only is True
    assert rc.changes == []
    assert rc.has_standalone_view is False
    assert rc.standalone_state_view() is None
    # Even with no figma, the diff view still labels the change AND emits the
    # mandatory NOT-changing guard.
    view = rc.state_plus_diff_view()
    assert "Make the tip selector bigger." in view
    assert "described in prose only" in view
    assert "Explicitly NOT changing" in view


def test_prose_only_with_prd_is_mechanics_regime() -> None:
    rc = render_state_diff(
        _capability(),
        Hypothesis(
            capability_name="checkout",
            prose="Charge a $2 service fee.",
            proposed_prd="Add a flat $2 fee at the payment step.",
        ),
    )
    assert rc.touched_modalities == ["mechanics"]
    assert rc.reliability_regime == "mixed"
    assert "Add a flat $2 fee" in rc.state_plus_diff_view()


# ── copy change (strong regime) ─────────────────────────────────────────────


def test_copy_change_is_strong_regime() -> None:
    proposed = ReverseFigma(
        screens=[_cart_screen(cta_text="Buy now · free returns"), _account_screen()]
    )
    rc = render_state_diff(
        _capability(),
        Hypothesis(
            capability_name="checkout",
            prose="Add a free-returns note to the CTA.",
            proposed_figma=proposed,
        ),
    )
    assert rc.prose_only is False
    changed = _by_kind_target(rc, "CHANGED", "checkout_cta")
    assert len(changed) == 1
    assert changed[0].modality == "copy"
    assert '"Buy now"' in changed[0].detail
    assert '"Buy now · free returns"' in changed[0].detail
    assert rc.touched_modalities == ["copy"]
    assert rc.reliability_regime == "strong"


# ── structural add/remove (weak regime) ─────────────────────────────────────


def test_added_and_removed_components() -> None:
    proposed_cart = Screen(
        id="cart",
        name="Cart",
        components=[
            Component(id="checkout_cta", role="button", text="Buy now"),
            # promo_code removed; trust_strip added
            Component(
                id="trust_strip",
                role="banner",
                text="10,000 5-star reviews",
                visible_to_roles=["guest", "member"],
            ),
        ],
    )
    rc = render_state_diff(
        _capability(),
        Hypothesis(
            capability_name="checkout",
            prose="Drop the promo field, add a trust strip.",
            proposed_figma=ReverseFigma(screens=[proposed_cart, _account_screen()]),
        ),
    )
    assert _by_kind_target(rc, "ADDED", "trust_strip")
    assert _by_kind_target(rc, "REMOVED", "promo_code")
    # Pure structural change → weak reading regime (the UI-modality cliff).
    assert rc.reliability_regime == "weak"
    assert "ui_structure" in rc.touched_modalities


def test_added_and_removed_screens() -> None:
    proposed = ReverseFigma(screens=[_cart_screen()])  # account screen removed
    proposed.screens.append(Screen(id="upsell", name="Upsell", components=[]))
    rc = render_state_diff(
        _capability(),
        Hypothesis(
            capability_name="checkout",
            prose="Remove account screen, add an upsell.",
            proposed_figma=proposed,
        ),
    )
    assert _by_kind_target(rc, "ADDED", "upsell")
    assert _by_kind_target(rc, "REMOVED", "account")


# ── mechanics: gating change ────────────────────────────────────────────────


def test_visible_to_roles_change_is_mechanics() -> None:
    proposed_cart = Screen(
        id="cart",
        name="Cart",
        components=[
            Component(id="checkout_cta", role="button", text="Buy now"),
            Component(
                id="promo_code",
                role="input",
                text="Promo code",
                visible_to_roles=["member"],  # now gated to members only
            ),
        ],
    )
    rc = render_state_diff(
        _capability(),
        Hypothesis(
            capability_name="checkout",
            prose="Gate the promo field to members.",
            proposed_figma=ReverseFigma(screens=[proposed_cart, _account_screen()]),
        ),
    )
    changed = _by_kind_target(rc, "CHANGED", "promo_code")
    assert len(changed) == 1
    assert changed[0].modality == "mechanics"
    assert rc.reliability_regime == "mixed"


# ── transitions ─────────────────────────────────────────────────────────────


def test_transition_add_and_remove() -> None:
    current = ReverseFigma(
        screens=[_cart_screen()],
        transitions=[Transition(trigger="tap_checkout", from_screen="cart", to_screen="pay")],
    )
    proposed = ReverseFigma(
        screens=[_cart_screen()],
        transitions=[Transition(trigger="tap_checkout", from_screen="cart", to_screen="review")],
    )
    rc = render_state_diff(
        _capability(current),
        Hypothesis(
            capability_name="checkout",
            prose="Route checkout through a review step.",
            proposed_figma=proposed,
        ),
    )
    # Re-route surfaces as REMOVED old + ADDED new in v1 (MOVED deferred).
    assert any(c.target_type == "transition" and c.kind == "ADDED" for c in rc.changes)
    assert any(c.target_type == "transition" and c.kind == "REMOVED" for c in rc.changes)


def test_transition_role_gating_change_is_mechanics() -> None:
    current = ReverseFigma(
        screens=[_cart_screen()],
        transitions=[Transition(trigger="tap_checkout", from_screen="cart", to_screen="pay")],
    )
    proposed = ReverseFigma(
        screens=[_cart_screen()],
        transitions=[
            Transition(
                trigger="tap_checkout",
                from_screen="cart",
                to_screen="pay",
                role_gated=["member"],
            )
        ],
    )
    rc = render_state_diff(
        _capability(current),
        Hypothesis(
            capability_name="checkout",
            prose="Gate checkout to members.",
            proposed_figma=proposed,
        ),
    )
    gating = [c for c in rc.changes if c.kind == "CHANGED" and c.target_type == "transition"]
    assert len(gating) == 1
    assert gating[0].modality == "mechanics"


# ── NOT-changing guard ──────────────────────────────────────────────────────


def test_not_changing_lists_untouched_screens() -> None:
    proposed = ReverseFigma(screens=[_cart_screen(cta_text="Buy now today"), _account_screen()])
    rc = render_state_diff(
        _capability(),
        Hypothesis(
            capability_name="checkout",
            prose="Tweak the CTA copy.",
            proposed_figma=proposed,
        ),
    )
    # account is untouched and must be named; cart is touched and must not be.
    assert "screen `account`" in rc.not_changing
    assert "screen `cart`" not in rc.not_changing
    assert "everything else not listed above" in rc.not_changing
    view = rc.state_plus_diff_view()
    assert "Explicitly NOT changing" in view
    assert "screen `account`" in view


# ── two output views (§5b blinding contract) ────────────────────────────────


def test_standalone_view_has_no_change_framing() -> None:
    proposed = ReverseFigma(
        screens=[_cart_screen(cta_text="Buy now · free returns"), _account_screen()]
    )
    rc = render_state_diff(
        _capability(),
        Hypothesis(
            capability_name="checkout",
            prose="Add free-returns note.",
            proposed_prd="Add a free-returns note to the buy CTA.",
            proposed_figma=proposed,
        ),
    )
    standalone = rc.standalone_state_view()
    assert standalone is not None
    # Blinded: the proposed product appears, but NO "what's changing" framing
    # and NOT the prose describing the change.
    assert "Buy now · free returns" in standalone
    assert "What's changing" not in standalone
    assert "Add free-returns note." not in standalone
    assert "Explicitly NOT changing" not in standalone
    # codex P2: the change PRD is intervention-framed prose and MUST NOT leak
    # into the blinded view that feeds metric elicitation.
    assert "Add a free-returns note to the buy CTA." not in standalone
    assert "PRD" not in standalone
    # The unblinded view, by contrast, carries the framing.
    diff_view = rc.state_plus_diff_view()
    assert "What's changing" in diff_view
    assert "Add free-returns note." in diff_view


def test_summarize_reverse_figma_matches_prompt_composer_shape() -> None:
    """The standalone view reuses the same vocabulary as prompt_composer's
    `_summarize_figma`, so 'product today' and 'proposed product' read identically
    (the symmetry that makes the #90 paired comparison clean)."""
    from sidira_simulator.services.prompt_composer import _summarize_figma

    figma = ReverseFigma(
        screens=[_cart_screen()],
        transitions=[Transition(trigger="tap_checkout", from_screen="cart", to_screen="pay")],
    )
    cap = _capability(figma)
    assert summarize_reverse_figma(figma) == _summarize_figma(cap)


# ── truncation (open Q2: never silently drop) ───────────────────────────────


def test_large_diff_is_capped_and_counted() -> None:
    many = [Component(id=f"c{i}", role="button", text=f"t{i}") for i in range(60)]
    current = ReverseFigma(screens=[Screen(id="s", name="S", components=many)])
    # Remove every component → 60 REMOVED changes, over the _MAX_CHANGES cap.
    proposed = ReverseFigma(screens=[Screen(id="s", name="S", components=[])])
    rc = render_state_diff(
        _capability(current),
        Hypothesis(
            capability_name="checkout",
            prose="Strip the screen.",
            proposed_figma=proposed,
        ),
    )
    assert len(rc.changes) == 40
    assert rc.truncated_count == 20
    assert "20 more minor changes" in rc.state_plus_diff_view()


def test_metadata_is_derived_from_full_diff_not_truncated_changelog() -> None:
    """Codex P2: NOT-changing guard + reliability regime must come from the FULL
    diff, before the changelog is capped. Otherwise a screen whose only change
    falls past the cap is wrongly listed as unchanged, and a weaker modality
    past the cutoff overstates the regime — defeating the safety purpose."""
    # Screen A: 45 copy-only changes (all strong) — fills past the 40-cap.
    a_current = [Component(id=f"a{i}", role="label", text=f"old{i}") for i in range(45)]
    a_proposed = [Component(id=f"a{i}", role="label", text=f"new{i}") for i in range(45)]
    # Screen B: exactly one structural change (weak), guaranteed past the cutoff
    # because screen A's 45 changes are emitted first.
    b_current = [Component(id="b0", role="button", text="x")]
    b_proposed: list[Component] = []  # b0 removed → ui_structure (weak)

    current = ReverseFigma(
        screens=[
            Screen(id="A", name="A", components=a_current),
            Screen(id="B", name="B", components=b_current),
        ]
    )
    proposed = ReverseFigma(
        screens=[
            Screen(id="A", name="A", components=a_proposed),
            Screen(id="B", name="B", components=b_proposed),
        ]
    )
    rc = render_state_diff(
        _capability(current),
        Hypothesis(
            capability_name="checkout",
            prose="Reword screen A and drop a button on B.",
            proposed_figma=proposed,
        ),
    )
    assert len(rc.changes) == 40  # changelog capped
    assert rc.truncated_count == 6  # 45 + 1 = 46 total, 6 over the cap
    # Screen B changed — it must NOT appear under NOT-changing even though its
    # change was truncated out of the rendered changelog.
    assert "screen `B`" not in rc.not_changing
    # The weak structural modality on B must still set the regime, despite being
    # past the cutoff (the changelog shows only screen A's copy changes).
    assert "ui_structure" in rc.touched_modalities
    assert rc.reliability_regime == "weak"


# ── degenerate: identical figmas ────────────────────────────────────────────


def test_identical_figmas_yield_no_structural_delta() -> None:
    same = ReverseFigma(screens=[_cart_screen(), _account_screen()])
    rc = render_state_diff(
        _capability(same),
        Hypothesis(
            capability_name="checkout",
            prose="Described in prose, no structural change.",
            proposed_figma=ReverseFigma(screens=[_cart_screen(), _account_screen()]),
        ),
    )
    assert rc.prose_only is False
    assert rc.changes == []
    assert "No structural delta detected" in rc.state_plus_diff_view()
    # codex P2: a figma with no structural delta cannot back a faithful blinded
    # view — it would show an unchanged product. Fall back to unblinded + flag.
    assert rc.has_standalone_view is False
    assert rc.standalone_state_view() is None


def test_prd_only_change_with_figma_has_no_blinded_view() -> None:
    """codex P2: when the change lives entirely in proposed_prd (a pricing/fee
    rule ReverseFigma can't encode) and the figma is unchanged, the blinded view
    must be withheld so metric elicitation doesn't evaluate the wrong state."""
    same_screens = [_cart_screen(), _account_screen()]
    rc = render_state_diff(
        _capability(ReverseFigma(screens=same_screens)),
        Hypothesis(
            capability_name="checkout",
            prose="Charge a $2 service fee.",
            proposed_prd="Add a flat $2 service fee at the payment step.",
            proposed_figma=ReverseFigma(screens=same_screens),
        ),
    )
    assert rc.changes == []
    # The PRD-carried mechanics is flagged via the regime, never faked into a view.
    assert "mechanics" in rc.touched_modalities
    assert rc.has_standalone_view is False
    assert rc.standalone_state_view() is None
    # The unblinded view still carries the change (PRD + NOT-changing guard).
    diff_view = rc.state_plus_diff_view()
    assert "$2 service fee" in diff_view
    assert "Explicitly NOT changing" in diff_view


# ── choice-set extraction (§3a Q3 / §1.6 step 4) ────────────────────────────


def _flow_capability() -> Capability:
    """A capability whose proposed state has transitions out of the cart screen,
    so the choice set can be grounded in the crawl."""
    figma = ReverseFigma(
        screens=[_cart_screen(), _account_screen()],
        transitions=[
            Transition(trigger="checkout", from_screen="cart", to_screen="payment"),
            Transition(trigger="continue_shopping", from_screen="cart", to_screen="catalog"),
            Transition(
                trigger="apply_promo",
                from_screen="cart",
                to_screen="cart",
                role_gated=["member"],
            ),
            # A transition that does NOT leave the decision point — must be ignored.
            Transition(trigger="confirm", from_screen="payment", to_screen="receipt"),
        ],
    )
    return _capability(figma)


def _flow_rendered(prose: str = "Streamline checkout."):
    cap = _flow_capability()
    # proposed_figma mirrors the capability's flow so transitions are reachable.
    return render_state_diff(
        cap,
        Hypothesis(
            capability_name="checkout",
            prose=prose,
            proposed_figma=cap.reverse_figma,
        ),
    )


def test_choice_set_grounded_in_reachable_transitions() -> None:
    cs = _flow_rendered().choice_set("cart")
    assert cs.grounded is True
    assert cs.fallback_used is False
    actions = {c.action for c in cs.choices}
    # The three transitions leaving `cart` are present...
    assert {"checkout", "continue_shopping", "apply_promo"} <= actions
    # ...the transition leaving `payment` is NOT (it doesn't leave the decision point).
    assert "confirm" not in actions
    # The synthetic always-available leave sink is appended.
    assert "leave" in actions
    leave = next(c for c in cs.choices if c.action == "leave")
    assert leave.synthetic is True and leave.leads_to is None


def test_choice_set_carries_leads_to_and_role_gating() -> None:
    cs = _flow_rendered().choice_set("cart")
    checkout = next(c for c in cs.choices if c.action == "checkout")
    assert checkout.leads_to == "payment"
    assert checkout.synthetic is False
    promo = next(c for c in cs.choices if c.action == "apply_promo")
    assert promo.role_gated == ["member"]


def test_choice_set_does_not_double_append_leave() -> None:
    figma = ReverseFigma(
        screens=[_cart_screen()],
        transitions=[
            Transition(trigger="exit_to_home", from_screen="cart", to_screen="home"),
        ],
    )
    cap = _capability(figma)
    rc = render_state_diff(
        cap,
        Hypothesis(capability_name="checkout", prose="x", proposed_figma=cap.reverse_figma),
    )
    cs = rc.choice_set("cart")
    # `exit_to_home` already reads as a leave action, so no synthetic "leave"
    # sink is appended.
    assert [c.action for c in cs.choices] == ["exit_to_home"]
    assert all(not c.synthetic for c in cs.choices)


def test_choice_set_falls_back_when_no_transition_leaves_decision_point() -> None:
    # Leaf decision point: no transition leaves `account` → curated fallback.
    cs = _flow_rendered().choice_set("account")
    assert cs.grounded is False
    assert cs.fallback_used is True
    assert [c.action for c in cs.choices] == list(_DEFAULT_FALLBACK_CHOICES)
    assert all(c.synthetic for c in cs.choices)


def test_choice_set_falls_back_for_prose_only_change() -> None:
    rc = render_state_diff(
        _capability(),
        Hypothesis(capability_name="checkout", prose="No figma here."),
    )
    cs = rc.choice_set("cart")
    assert cs.grounded is False
    assert cs.fallback_used is True


def test_choice_set_accepts_custom_fallback() -> None:
    rc = render_state_diff(
        _capability(),
        Hypothesis(capability_name="checkout", prose="No figma here."),
    )
    cs = extract_choice_set(rc, "cart", fallback=["click", "ignore"])
    assert [c.action for c in cs.choices] == ["click", "ignore"]
    assert cs.fallback_used is True


def test_choice_set_method_matches_module_function() -> None:
    rc = _flow_rendered()
    assert rc.choice_set("cart") == extract_choice_set(rc, "cart")


def test_back_navigation_does_not_suppress_leave_sink() -> None:
    """codex P2: a `back_to_cart`-style in-flow navigation is NOT an abandon
    action, so the synthetic always-available leave sink must still be appended."""
    figma = ReverseFigma(
        screens=[_cart_screen()],
        transitions=[
            Transition(trigger="back_to_cart", from_screen="cart", to_screen="cart"),
            Transition(trigger="checkout", from_screen="cart", to_screen="payment"),
        ],
    )
    cap = _capability(figma)
    rc = render_state_diff(
        cap,
        Hypothesis(capability_name="checkout", prose="x", proposed_figma=cap.reverse_figma),
    )
    actions = [c.action for c in rc.choice_set("cart").choices]
    assert "back_to_cart" in actions
    assert "leave" in actions  # not suppressed by the "back" substring


# ── screen-level field changes (codex P2) ───────────────────────────────────


def test_screen_name_change_is_a_copy_change_and_not_unchanged() -> None:
    """codex P2: a screen `name` change is prompt-visible (summarize renders it),
    so it must surface as CHANGED and the screen must NOT read as NOT-changing."""
    current = ReverseFigma(screens=[_cart_screen(), _account_screen()])
    proposed = ReverseFigma(
        screens=[
            Screen(id="cart", name="Your Basket", components=_cart_screen().components),
            _account_screen(),
        ]
    )
    rc = render_state_diff(
        _capability(current),
        Hypothesis(capability_name="checkout", prose="Rename Cart→Basket", proposed_figma=proposed),
    )
    changed = _by_kind_target(rc, "CHANGED", "cart")
    assert len(changed) == 1
    assert changed[0].modality == "copy"
    assert changed[0].target_type == "screen"
    assert "Cart" in changed[0].detail and "Your Basket" in changed[0].detail
    assert "screen `cart`" not in rc.not_changing


def test_screen_role_change_is_a_mechanics_change() -> None:
    current = ReverseFigma(screens=[Screen(id="cart", name="Cart", role="guest")])
    proposed = ReverseFigma(screens=[Screen(id="cart", name="Cart", role="member")])
    rc = render_state_diff(
        _capability(current),
        Hypothesis(
            capability_name="checkout",
            prose="Gate the cart to members",
            proposed_figma=proposed,
        ),
    )
    changed = _by_kind_target(rc, "CHANGED", "cart")
    assert len(changed) == 1
    assert changed[0].modality == "mechanics"
    assert "guest" in changed[0].detail and "member" in changed[0].detail


def test_transition_reroute_endpoints_not_listed_as_unchanged() -> None:
    """codex P2: a reroute (cart->pay becomes cart->review) renders the
    transition as changed, so its endpoint screens must NOT appear under
    'Explicitly NOT changing' — otherwise the guard contradicts the changelog."""
    screens = [
        Screen(id="cart", name="Cart"),
        Screen(id="pay", name="Pay"),
        Screen(id="review", name="Review"),
    ]
    current = ReverseFigma(
        screens=screens,
        transitions=[Transition(trigger="checkout", from_screen="cart", to_screen="pay")],
    )
    proposed = ReverseFigma(
        screens=screens,
        transitions=[Transition(trigger="checkout", from_screen="cart", to_screen="review")],
    )
    rc = render_state_diff(
        _capability(current),
        Hypothesis(
            capability_name="checkout",
            prose="Route checkout through a review step.",
            proposed_figma=proposed,
        ),
    )
    # The reroute surfaces as REMOVED + ADDED transitions (MOVED deferred, §7 Q1).
    assert any(c.target_type == "transition" for c in rc.changes)
    # Neither endpoint screen may be claimed unchanged.
    assert "screen `cart`" not in rc.not_changing
    assert "screen `pay`" not in rc.not_changing
    assert "screen `review`" not in rc.not_changing

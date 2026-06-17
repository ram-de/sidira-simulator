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

# #221/#222: stimulus-type keywords the affordance gating MUST NOT consult and
# MUST NOT emit into the clause. The whole honesty contract is that the rule is
# structural (a transition out of a screen), not stimulus-type matching.
_FORBIDDEN_AFFORDANCE_KEYWORDS = ("promo", "ad", "advert", "email", "marketing")

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


# ── #221/#222 stimulus-affordance rendering (gated, structural, neutral) ──────
#
# The certified "advertising-as-harm" bug: the blinded outcome view renders an
# interactive stimulus (an email, a button, a re-engagement push, a sale banner)
# as a STATIC structural component while listing the transition that pulls the
# user into the product SEPARATELY, so the model reads the stimulus as clutter →
# lower propensity. The fix (Option A) appends a neutral, transition-graph-derived
# affordance clause naming the destination screen, behind a default-OFF gate.
#
# The honesty contract these tests pin down:
#   1. neutral/factual MECHANIC ("opens: X"), not intent or valence;
#   2. derived from the structural transition graph, never stimulus-type keywords;
#   3. symmetric across arms (same rule on the current and proposed figmas);
#   4. gated default-OFF and byte-identical when OFF (and when ON but nothing has
#      an outbound cross-screen transition).


def _email_stimulus_figma() -> ReverseFigma:
    """A stimulus surface modelled exactly like the Hillstrom certified bug: an
    interactive component on a `promo_email` screen whose ONLY structural signal
    that it pulls the user into the product is an outbound cross-screen transition
    (`click_email: promo_email → inbox`). The renderer must surface the destination
    without consulting the screen id / component text / trigger label."""
    return ReverseFigma(
        screens=[
            Screen(id="inbox", name="Inbox", components=[]),
            Screen(
                id="promo_email",
                name="Promotional e-mail",
                components=[Component(id="email_body", role="body", text="Big sale inside")],
            ),
        ],
        transitions=[
            Transition(trigger="click_email", from_screen="promo_email", to_screen="inbox")
        ],
    )


def _button_stimulus_figma() -> ReverseFigma:
    """The SAME structural shape with a plain button and no stimulus vocabulary —
    proves the rule fires on structure (an outbound cross-screen transition), not
    on 'promo'/'email' keywords."""
    return ReverseFigma(
        screens=[
            Screen(id="site", name="Site", components=[]),
            Screen(
                id="home",
                name="Home",
                components=[Component(id="cta", role="button", text="Continue")],
            ),
        ],
        transitions=[Transition(trigger="tap_cta", from_screen="home", to_screen="site")],
    )


def test_affordance_gate_off_is_byte_identical(monkeypatch) -> None:
    """Gate OFF (the default) → the render is byte-for-byte the historical output
    for a stimulus figma: NO affordance clause is emitted."""
    monkeypatch.delenv("SIDIRA_STIMULUS_AFFORDANCE", raising=False)
    monkeypatch.delenv("PYTHIA_STIMULUS_AFFORDANCE", raising=False)
    figma = _email_stimulus_figma()
    rendered = summarize_reverse_figma(figma)
    assert "leads to" not in rendered
    assert "↳" not in rendered
    # Reconstruct the exact pre-fix output to lock byte-identity.
    expected = "\n".join(
        [
            "- **Screen `inbox`** — Inbox",
            "- **Screen `promo_email`** — Promotional e-mail",
            "    - body `email_body` — `Big sale inside`",
            "",
            "Transitions:",
            "- click_email: `promo_email` → `inbox`",
        ]
    )
    assert rendered == expected


def test_affordance_gate_on_appends_neutral_destination_clause(monkeypatch) -> None:
    """Gate ON → a screen with an outbound cross-screen transition gets ONE neutral
    clause naming the destination screen, derived from the transition graph."""
    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")
    rendered = summarize_reverse_figma(_email_stimulus_figma())
    # The clause names the DESTINATION screen (target screen `name`), stating only
    # the navigation mechanic.
    assert "    - ↳ opens: Inbox" in rendered
    # It is attached to the source screen `promo_email`, not the leaf `inbox`.
    promo_block = rendered.split("- **Screen `promo_email`**")[1].split("Transitions:")[0]
    assert "↳ opens: Inbox" in promo_block
    inbox_block = rendered.split("- **Screen `inbox`**")[1].split("- **Screen `promo_email`**")[0]
    assert "leads to" not in inbox_block


def test_affordance_clause_is_keyword_free_and_carries_destination(monkeypatch) -> None:
    """Honesty constraint 1+2: the clause contains the destination screen name and
    NONE of the stimulus-type keywords as hardcoded content — for BOTH a 'promo
    email' figma and a plain 'button' figma the only difference is the destination
    name, never the rule."""
    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")

    email_rendered = summarize_reverse_figma(_email_stimulus_figma())
    clause = next(line for line in email_rendered.splitlines() if "↳ opens:" in line)
    assert "Inbox" in clause  # destination screen name present
    low = clause.lower()
    for kw in _FORBIDDEN_AFFORDANCE_KEYWORDS:
        assert kw not in low, f"stimulus keyword {kw!r} leaked into affordance clause: {clause!r}"
    # No valence words either — mechanic, not intent.
    for valence in ("good", "better", "positive", "engaging", "want", "back"):
        assert valence not in low, f"valence word {valence!r} in affordance clause: {clause!r}"

    # The plain-button figma fires the SAME rule with a different destination name.
    button_rendered = summarize_reverse_figma(_button_stimulus_figma())
    button_clause = next(line for line in button_rendered.splitlines() if "↳ opens:" in line)
    assert "Site" in button_clause


def test_affordance_gating_logic_has_no_stimulus_keywords() -> None:
    """Honesty constraint 2 (structural source-of-truth): the gating helpers that
    decide WHEN to emit the clause must not match on stimulus-type keywords. Assert
    directly against the source of the two helpers."""
    import inspect

    from sidira_simulator.services import treatment_renderer as tr

    source = (
        inspect.getsource(tr._screen_affordance_destinations)
        + inspect.getsource(tr._affordance_clause)
        + inspect.getsource(tr.summarize_reverse_figma)
    )
    low = source.lower()
    # The helpers reference destinations/transitions structurally; a stimulus
    # keyword appearing as a string literal here would be keyword-gating.
    for kw in _FORBIDDEN_AFFORDANCE_KEYWORDS:
        assert (
            f'"{kw}' not in low and f"'{kw}" not in low
        ), f"keyword literal {kw!r} in gating logic"


def test_affordance_clause_is_symmetric_across_arms(monkeypatch) -> None:
    """Honesty constraint 3 (paired symmetry): the IDENTICAL affordance clause
    appears in both the current- and the proposed-figma renderings — so it cancels
    in the paired treatment−control delta and never biases the lift."""
    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")
    # Current and proposed both carry the stimulus surface; the proposed only
    # changes the component copy (the real intervention), not the affordance.
    current = _email_stimulus_figma()
    proposed = ReverseFigma(
        screens=[
            Screen(id="inbox", name="Inbox", components=[]),
            Screen(
                id="promo_email",
                name="Promotional e-mail",
                components=[Component(id="email_body", role="body", text="Even bigger sale")],
            ),
        ],
        transitions=list(current.transitions),
    )
    current_clause = [line for line in summarize_reverse_figma(current).splitlines() if "↳" in line]
    proposed_clause = [
        line for line in summarize_reverse_figma(proposed).splitlines() if "↳" in line
    ]
    assert current_clause == proposed_clause == ["    - ↳ opens: Inbox"]


def test_affordance_gate_on_byte_identical_when_no_cross_screen_transition(monkeypatch) -> None:
    """Gate ON but the figma has NO component on a screen with an outbound
    cross-screen transition → byte-identical to OFF (no clause). A self-loop
    (`apply_promo: cart → cart`) is NOT an affordance out of the screen."""
    figma = ReverseFigma(
        screens=[_cart_screen(), _account_screen()],
        transitions=[
            # self-loop only; not a cross-screen affordance
            Transition(trigger="apply_promo", from_screen="cart", to_screen="cart"),
        ],
    )
    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")
    on = summarize_reverse_figma(figma)
    monkeypatch.delenv("SIDIRA_STIMULUS_AFFORDANCE", raising=False)
    monkeypatch.delenv("PYTHIA_STIMULUS_AFFORDANCE", raising=False)
    off = summarize_reverse_figma(figma)
    assert on == off
    assert "leads to" not in on


def test_affordance_dedups_and_orders_multiple_destinations(monkeypatch) -> None:
    """A source screen with several distinct outbound destinations lists them once
    each, in first-seen transition order — deterministic and graph-derived."""
    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")
    figma = ReverseFigma(
        screens=[
            Screen(id="home", name="Home", components=[Component(id="b", role="button")]),
            Screen(id="feed", name="Feed", components=[]),
            Screen(id="search", name="Search", components=[]),
        ],
        transitions=[
            Transition(trigger="open_feed", from_screen="home", to_screen="feed"),
            Transition(trigger="open_search", from_screen="home", to_screen="search"),
            # duplicate destination via a second trigger → listed once
            Transition(trigger="refresh_feed", from_screen="home", to_screen="feed"),
        ],
    )
    rendered = summarize_reverse_figma(figma)
    assert "    - ↳ opens: Feed, Search" in rendered


def test_affordance_clause_carries_role_gating(monkeypatch) -> None:
    """codex P2: a role-gated outbound transition must NOT read as generally
    available. The clause carries the SAME `[role-gated: …]` suffix the transition
    line uses, so the affordance is not overstated for personas outside the role —
    a structural fact already in the transition, never an inferred signal."""
    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")
    figma = ReverseFigma(
        screens=[
            Screen(id="home", name="Home", components=[Component(id="b", role="button")]),
            Screen(id="vault", name="Vault", components=[]),
        ],
        transitions=[
            Transition(
                trigger="open_vault",
                from_screen="home",
                to_screen="vault",
                role_gated=["member"],
            ),
        ],
    )
    rendered = summarize_reverse_figma(figma)
    assert "    - ↳ opens: Vault [role-gated: member]" in rendered


def test_summarize_matches_prompt_composer_shape_with_gate_on(monkeypatch) -> None:
    """Honesty constraint 4 / format-consistency: with the gate ON, the unblinded
    reaction view (`prompt_composer._summarize_figma`) and the blinded/standalone
    renderer stay byte-identical — they share the one renderer, so the affordance
    clause appears in both or neither."""
    from sidira_simulator.services.prompt_composer import _summarize_figma

    monkeypatch.setenv("SIDIRA_STIMULUS_AFFORDANCE", "1")
    cap = _capability(_email_stimulus_figma())
    assert summarize_reverse_figma(cap.reverse_figma) == _summarize_figma(cap)
    assert "↳ opens: Inbox" in _summarize_figma(cap)

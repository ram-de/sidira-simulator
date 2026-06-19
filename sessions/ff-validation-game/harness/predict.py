"""F&F validation harness — STEP 1: BLINDED engine prediction + SEAL (ticket #444).

ROLE: the *engine runner*. This script runs the FULL engine (``SimulationRunner``)
conditioned on the committed friends_family persona pack and, for EACH of the 5
micro-A/Bs, predicts which arm wins on that item's binary outcome metric. It then
writes the sealed pre-registration file ``PREREG_FF.json`` and (engine-runner)
git-commits it BEFORE any outcome is computed.

KEY DISCIPLINE — this script NEVER reads ``player_outcomes`` (Table B, the SEALED
answer key). It reads ONLY:
  * the committed persona pack (``friends_family_panel_v1.json``) via the loader, and
  * the AUDITED ``obvious_priors.json`` (#442) for the placebo + counter-intuitive
    flags — a LOCAL copy lives in this harness dir, so the harness is self-contained
    and references nothing under the (now-extracted) game app.
A static guard (``_assert_no_outcome_access``) re-asserts at runtime that no Table-B
path is opened. The whole point of the role split is that the person who runs the
engine cannot see (and is structurally prevented from reading) the outcomes.

WHY THE FULL ENGINE (not a population-level forecaster): the experiment asks
"given a pack built from THESE players, does the engine predict THESE players'
A/B behavior." So each item is run as a real ``SimulationRunner.run`` on the F&F
pack with a per-item ``Hypothesis`` (capability_name + control/treatment prose +
the binary conversion metric). The engine's predicted winner = sign of the paired
``conversion_lift_pp`` (treatment − control; a positive lift means the TREATMENT
arm wins on the metric). Mirrors
``sessions/agent-behavior-spec/streamly-metric-validation/streamly_plumbing_run.py``.

    set -a && . backend/.env && set +a
    PYTHONPATH=backend backend/.venv/bin/python sessions/ff-validation-game/harness/predict.py [--population 12] [--model claude-sonnet-4-6] [--seal]

``--seal`` writes PREREG_FF.json. Without it, predictions are printed/written to a
scratch file for a dry run. The harness's own ``run_synthetic.py`` always seals.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sidira_simulator.adapters.friends_family_panel_loader import (
    friends_family_panel_registration,
    load_friends_family_panel,
)
from sidira_simulator.adapters.llm import get_chat_client
from sidira_simulator.schemas.feature_pack import Capability, ReverseFigma, Screen
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.simulation_runner import SimulationRunner

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACK_PATH = (
    REPO / "backend/sidira_simulator/adapters/friends_family_panel_v1.json"
)
# The AUDITED obvious priors live in a LOCAL copy alongside this harness (so the
# harness is self-contained and depends on nothing under the extracted game app).
OBVIOUS_PRIORS_PATH = HERE / "obvious_priors.json"
PREREG_PATH = HERE / "PREREG_FF.json"
CUSTOMER_ID = "friends_family"

# ── The hard firewall: the prediction role must NEVER read the sealed outcomes ──
# Table B lives in the game's DB / a player_outcomes export. There is no code path
# here that opens it; this guard makes that auditable (and trips loudly if a future
# edit tried to import or open an outcomes file).
_FORBIDDEN_OUTCOME_TOKENS = ("player_outcomes", "outcome")


def _assert_no_outcome_access(open_paths: list[str]) -> None:
    """Re-assert that the prediction role opened no Table-B (outcomes) artifact.

    ``open_paths`` is the list of files this run actually read. None may name an
    outcomes table. This is a belt-and-suspenders check on the role separation:
    predict.py is BLIND to outcomes by construction (it reads only the pack + the
    obvious priors), and this trips if that ever stops being true.
    """
    for p in open_paths:
        low = p.lower()
        if "player_outcomes" in low or low.endswith("_outcomes.csv") or low.endswith("_outcomes.json"):
            raise RuntimeError(
                f"BLIND-PREDICTION VIOLATION: predict.py attempted to read an outcomes "
                f"artifact ({p!r}). The engine-runner role MUST NOT see Table B."
            )


# ── The 5 micro-A/Bs, transcribed from the AUDITED game components (#440/#441) ──
# For each item the engine is shown a CONTROL arm and a TREATMENT arm + the binary
# outcome metric. The engine's predicted winner is read off the sign of the paired
# conversion lift (treatment − control). We fix CONTROL = the arm the obvious prior
# backs and TREATMENT = the other arm, so a positive lift = "engine predicts the
# NON-obvious arm wins". (This labeling is purely an internal convention for reading
# the lift sign; the engine is never told which is "obvious". The mapping back to
# the game's arm labels is recorded per item so scoring is unambiguous.)
MICRO_ABS = [
    {
        "task_id": "choice_overload",
        "capability_name": "claim_a_bonus_reward",
        "metric": "claim a bonus reward (vs skipping it)",
        "metric_label": "Claim a reward",
        "decision_point": "you've earned a bonus reward and are deciding whether to claim one or skip",
        # control = obvious-prior arm (opts:24), treatment = the other (opts:3)
        "control_arm": "opts:24",
        "treatment_arm": "opts:3",
        "control": (
            "A 'Claim a bonus' screen offering 24 reward options to pick from "
            "(a long, scrollable grid of choices), plus a 'None for now' skip button."
        ),
        "treatment": (
            "The SAME 'Claim a bonus' screen but offering only 3 reward options to "
            "pick from, plus a 'None for now' skip button."
        ),
    },
    {
        "task_id": "countdown_urgency",
        "capability_name": "lock_in_loot_pool",
        "metric": "lock in the loot-pool deal (vs passing for now)",
        "metric_label": "Lock it in",
        "decision_point": "you can add your coins to a shared loot pool for a shot at a 20x payout",
        # control = obvious-prior arm (framing:scarce), treatment = framing:calm
        "control_arm": "framing:scarce",
        "treatment_arm": "framing:calm",
        "control": (
            "A 'Lock in the loot pool' screen with aggressive scarcity framing: a red "
            "'Only 3 spots left!' badge and a visible countdown timer ('Offer expires in Ns'), "
            "then 'Lock it in' / 'Pass for now' buttons. Audience knows they are being sold to "
            "(a friends-&-family game)."
        ),
        "treatment": (
            "The SAME 'Lock in the loot pool' screen but with calm framing: 'No rush — take your "
            "time', no countdown, no scarcity badge, then the same 'Lock it in' / 'Pass for now' buttons."
        ),
    },
    {
        "task_id": "default_stickiness",
        "capability_name": "keep_coins_locked",
        "metric": "stay locked in / keep the safe choice (vs opting out)",
        "metric_label": "Keep it locked in",
        "decision_point": "you're deciding whether to keep your coins locked in the safe option or take them back out",
        # control = obvious-prior arm (stickiness:default) — note this item is OBVIOUS
        # (not counter-intuitive per the #442 audit), so it carries no counter-intuitive weight.
        "control_arm": "stickiness:default",
        "treatment_arm": "stickiness:framing",
        "control": (
            "A 'Lock your coins in?' screen with a pre-checked 'Keep my coins safely locked in' box "
            "and a social-proof line 'Most players lock in and keep this on', then 'Keep it locked in' "
            "/ 'Take them back out' buttons."
        ),
        "treatment": (
            "The SAME 'Lock your coins in?' screen but with NO pre-checked box and NO social proof — "
            "instead a gain-framed prospect-theory pitch: 'Lock in now and you secure a guaranteed gain "
            "— leave them out and you risk losing the ground you've made', then the same two buttons."
        ),
    },
    {
        "task_id": "prosocial_backfire",
        "capability_name": "split_your_bonus",
        "metric": "allocate at least half your bonus to the shared pool (vs keeping more than half)",
        "metric_label": "Give >= half to the pool",
        "decision_point": "you have a 10-coin bonus and are choosing how many coins to share into a shared pool",
        # control = obvious-prior arm (prosocial:polished), treatment = prosocial:sparse
        "control_arm": "prosocial:polished",
        "treatment_arm": "prosocial:sparse",
        "control": (
            "A 'Split your bonus' screen with a polished, vivid impact story: 'Every coin you share into "
            "the pool compounds — it's matched, pooled, and pays forward to every player. Your impact grows "
            "far beyond what you give', then a 0/2/5/8/10-coin give selector. Audience knows they are being "
            "sold to (a friends-&-family game)."
        ),
        "treatment": (
            "The SAME 'Split your bonus' screen but sparse, with no persuasion: 'You have a 10-coin bonus. "
            "Keep it, or share some into the pool', then the same give selector."
        ),
    },
    {
        "task_id": "effort_justification",
        "capability_name": "join_next_round",
        "metric": "commit to joining the next round (vs declining)",
        "metric_label": "Count me in",
        "decision_point": "you're deciding whether to commit to joining the next round of the game",
        # control = obvious-prior arm (effort:one_tap), treatment = effort:effort
        "control_arm": "effort:one_tap",
        "treatment_arm": "effort:effort",
        "control": (
            "A 'Join the next round?' screen that is one frictionless tap: 'One tap to join the next round', "
            "then 'Count me in' / 'Not this time' buttons."
        ),
        "treatment": (
            "The SAME 'Join the next round?' screen but gated behind a tiny earned step: first 'Build your "
            "player badge to unlock the next round' (tap 3 times), then 'Your badge is ready. Lock in for the "
            "next round?' with the same 'Count me in' / 'Not this time' buttons."
        ),
    },
]


def _capability_for(item: dict) -> Capability:
    """Build a minimal valid Capability describing the micro-A/B surface.

    The F&F game has no crawled feature pack, so we synthesize a one-screen
    Capability per item (the same shape ``FeaturePackLoader.load_capability``
    would yield). The control/treatment prose lives on the Hypothesis; this just
    gives the engine a surface to anchor the decision moment.
    """
    screen = Screen(id=f"{item['task_id']}_screen", name=item["capability_name"], role=None)
    return Capability(
        name=item["capability_name"],
        surfaces=[screen.id],
        roles=[],
        entry_points=[],
        reverse_prd=(
            f"# {item['capability_name']}\n\n"
            f"A single decision screen in a short friends-&-family economic game. "
            f"At this moment {item['decision_point']}. "
            f"The screen is being A/B tested between two presentations (described in the hypothesis). "
            f"The binary outcome is whether the player chooses to {item['metric']}."
        ),
        reverse_figma=ReverseFigma(screens=[screen], transitions=[]),
        implicit_metric="conversion",
    )


def _hypothesis_for(item: dict) -> Hypothesis:
    """Build the per-item conversion Hypothesis (CONTROL vs TREATMENT prose).

    The engine compares the two arms on the binary conversion metric. We phrase
    the change as "replace CONTROL with TREATMENT" so the paired lift sign reads
    as treatment − control.
    """
    return Hypothesis.model_validate(
        {
            "capability_name": item["capability_name"],
            "prose": (
                f"CONTROL (current): {item['control']}\n\n"
                f"TREATMENT (proposed change): {item['treatment']}\n\n"
                f"The treatment replaces the control presentation of the same decision. "
                f"We are measuring which presentation makes a real friends-&-family player more "
                f"likely to {item['metric']}."
            ),
            "metric_name": "conversion",
            "conversion_action": item["metric"],
            "conversion_action_label": item["metric_label"],
            "decision_point": item["decision_point"],
        }
    )


def _engine_predict(
    new_runner, item: dict, population: int, seed: int, retries: int = 2
) -> dict:
    """Run the FULL engine on the F&F pack for one micro-A/B → predicted winner.

    ``new_runner`` is a zero-arg factory that returns a FRESH ``SimulationRunner``.
    Each item (and each retry) gets its own runner instance — a runner accumulates
    per-run state (agent memory / run-state store) that, when shared across items,
    corrupts the conversion elicitation of later items (it silently zeroed 4/5 item
    lifts to None in testing). A fresh runner per run keeps every item independent.

    Returns the predicted winning ARM LABEL (the game's arm string) + a confidence
    in [0,1] + the raw paired conversion lift. A positive ``metric_lift_pp``
    (treatment − control) means the TREATMENT arm is predicted to win the binary
    metric; a negative lift means CONTROL wins. A near-zero lift (or a CI straddling
    zero) maps to low confidence.

    The conversion elicitation is also an LLM parse that can occasionally fail for a
    whole arm (lift → None) as a run-to-run flake; we retry with a fresh seed up to
    ``retries`` times when the lift comes back None.
    """
    pack = load_friends_family_panel()
    cap = _capability_for(item)
    hyp = _hypothesis_for(item)
    res = None
    lift = ci = None
    attempts = 0
    for attempt in range(retries + 1):
        attempts = attempt + 1
        runner = new_runner()  # FRESH runner per run — no cross-item state bleed
        sim = asyncio.run(
            runner.run(
                customer_id=CUSTOMER_ID,
                persona_pack=pack,
                capability=cap,
                feature_pack_version=pack.version,
                hypothesis=hyp,
                population_size=population,
                run_seed=seed + attempt * 1000,
                treatment_fraction=0.5,
            )
        )
        res = sim.result
        # Current builds expose the metric lift as `metric_lift_pp`; older builds
        # used `conversion_lift_pp`. Read whichever is present.
        lift = getattr(res, "metric_lift_pp", None)
        if lift is None:
            lift = getattr(res, "conversion_lift_pp", None)
        ci = getattr(res, "metric_lift_ci_pp", None)
        if ci is None:
            ci = getattr(res, "conversion_lift_ci_pp", None)
        if lift is not None:
            break
    # Predicted winner from the lift sign (treatment − control).
    if lift is None:
        predicted_arm = None
        confidence = 0.0
    elif lift > 0:
        predicted_arm = item["treatment_arm"]
        confidence = min(1.0, abs(lift) / 100.0)
    elif lift < 0:
        predicted_arm = item["control_arm"]
        confidence = min(1.0, abs(lift) / 100.0)
    else:
        predicted_arm = None
        confidence = 0.0
    # A CI straddling zero halves the confidence (engine is unsure of direction).
    if ci is not None and predicted_arm is not None and ci[0] <= 0.0 <= ci[1]:
        confidence *= 0.5
    return {
        "task_id": item["task_id"],
        "capability_name": item["capability_name"],
        "control_arm": item["control_arm"],
        "treatment_arm": item["treatment_arm"],
        "engine_predicted_arm": predicted_arm,
        "engine_confidence": round(confidence, 4),
        "metric_lift_pp": lift,
        "metric_lift_ci_pp": list(ci) if ci is not None else None,
        "metric_regime": getattr(res, "metric_regime", None) or getattr(res, "conversion_regime", None),
        "metric_lift_underpowered": getattr(res, "metric_lift_underpowered", None),
        "metric_lift_unblinded_fallback": getattr(res, "metric_lift_unblinded_fallback", None),
        "engine_confidence_score": getattr(res, "confidence_score", None),
        "engine_run_attempts": attempts,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_obvious_priors() -> dict:
    return json.loads(OBVIOUS_PRIORS_PATH.read_text())


def _pack_is_synthetic(pack_path: Path) -> bool:
    """True iff the committed pack is labeled SYNTHETIC at its top level.

    Read off the RAW pack JSON (not the parsed PersonaPack, which drops the
    additive marker fields under Pydantic ``extra='ignore'``). Honors either the
    boolean ``synthetic`` flag or ``data_source == 'synthetic'``. A real Table-A
    rebuild carries neither, so the seal-guard lets it through.
    """
    try:
        raw = json.loads(pack_path.read_text())
    except (OSError, ValueError):
        return False
    if not isinstance(raw, dict):
        return False
    if raw.get("synthetic") is True:
        return True
    return str(raw.get("data_source", "")).strip().lower() == "synthetic"


def _placebo_predictions(priors: dict) -> list[dict]:
    """The 'always-pick-obvious' PLACEBO: predict the obvious_prior_arm for each item.

    Straight from the AUDITED obvious_priors.json — no engine involved. This is the
    baseline the engine must STRICTLY beat for a GO.
    """
    out = []
    for it in priors["items"]:
        out.append(
            {
                "task_id": it["task_id"],
                "placebo_predicted_arm": it["obvious_prior_arm"],
                "counter_intuitive": it["counter_intuitive"],
            }
        )
    return out


WIN_RULE = {
    "description": (
        "GO iff ALL of: (1) the engine direction-hit-rate across the K>=5 micro-A/Bs "
        "clears the binomial chance bar (a clean or one-miss sweep at K>=5; 5/5 -> p~0.03, "
        "4/4 -> p~0.06 = proof-of-life); AND (2) the engine STRICTLY beats the "
        "'always-pick-obvious' placebo hit-rate; AND (3) the engine is right on >=1 item "
        "where the obvious prior is wrong (a GENUINELY counter-intuitive item — NOT "
        "default_stickiness, which the #442 audit found to be OBVIOUS)."
    ),
    "K_min": 5,
    "binomial": {"clean_sweep_p": 0.03, "one_miss_p": 0.06, "alpha": 0.10},
    "must_strictly_beat_placebo": True,
    "must_hit_ge_1_counter_intuitive": True,
    "counter_intuitive_excludes": ["default_stickiness"],
    "tie_handling": "two-sided ties on an item's real winner are dropped symmetrically for engine AND placebo before scoring",
    "source": "sessions/agent-behavior-spec/ff-app-design/FF_GAME_DESIGN.md - 'Sealed win rule'",
}

STOPPING_RULE = {
    "description": (
        "Unit of evidence is the direction hit-rate across K>=5 items, never a single A/B "
        "(each underpowered at N=30-100). Field to a pre-set N, compute outcomes ONCE, score ONCE. "
        "Any post-seal edit to the pack, predictions, metrics, priors, or win rule BURNS the run."
    ),
    "score_once": True,
    "no_post_seal_edits": True,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="BLINDED F&F engine prediction + seal (#444).")
    ap.add_argument("--population", type=int, default=12, help="agents per micro-A/B run")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--seed", type=int, default=444)
    ap.add_argument("--seal", action="store_true", help="write PREREG_FF.json (the sealed pre-reg)")
    ap.add_argument(
        "--allow-synthetic",
        action="store_true",
        help=(
            "test-mode: permit sealing against a SYNTHETIC-labeled pack (machinery "
            "test only). Without this, sealing on a synthetic pack is REFUSED."
        ),
    )
    ap.add_argument(
        "--out", default=str(PREREG_PATH), help="path for the sealed pre-reg JSON"
    )
    args = ap.parse_args()

    opened: list[str] = [str(PACK_PATH), str(OBVIOUS_PRIORS_PATH)]
    _assert_no_outcome_access(opened)  # belt-and-suspenders: this role is BLIND to Table B.

    # ── SYNTHETIC-PACK SEAL-GUARD ───────────────────────────────────────────────
    # Machine-enforce "no real validation run against synthetic data". If the
    # committed pack is labeled synthetic, refuse to SEAL a real PREREG_FF.json
    # unless the caller explicitly opts into machinery-test mode. We check this
    # BEFORE spending any engine/LLM time so a misconfigured real run fails fast.
    if args.seal and _pack_is_synthetic(PACK_PATH) and not args.allow_synthetic:
        print(
            "\nREFUSING TO SEAL: the committed pack is labeled SYNTHETIC "
            f"({PACK_PATH.relative_to(REPO)}).\n"
            "  Refusing to seal a real validation against a SYNTHETIC pack. "
            "Rebuild the pack\n"
            "  from the real Table A (player_features) export, or pass "
            "--allow-synthetic for a\n"
            "  machinery test (the verdict is then NOT a real validation result).",
            file=sys.stderr,
        )
        return 2

    reg = friends_family_panel_registration()
    priors = _load_obvious_priors()
    if priors.get("_status", "").startswith("AUDITED") is False and "AUDITED" not in priors.get("_status", ""):
        print("WARNING: obvious_priors.json is not marked AUDITED; sealing against an unaudited prior is unsafe.")

    # A FRESH SimulationRunner per item (see _engine_predict): a runner accumulates
    # per-run state that bleeds across items if shared. We pass a factory.
    def new_runner() -> SimulationRunner:
        return SimulationRunner(chat_client=get_chat_client(args.model))

    print(f"=== BLINDED engine prediction on pack '{reg.panel_id}' "
          f"({reg.persona_count} personas, indiv_row={reg.is_individual_row_capable}, "
          f"behavioral_seeds={reg.is_behavioral_seeds_complete}) ===")
    print(f"    model={args.model} population={args.population} seed={args.seed}")
    print("    (predict.py NEVER reads player_outcomes / Table B)\n")

    engine_preds = []
    for i, item in enumerate(MICRO_ABS):
        pred = _engine_predict(new_runner, item, args.population, args.seed + i)
        engine_preds.append(pred)
        print(f"  {item['task_id']:20s} lift(t-c)={str(pred['metric_lift_pp']):>8} "
              f"-> predicts arm={pred['engine_predicted_arm']!s:18s} conf={pred['engine_confidence']}")

    placebo = _placebo_predictions(priors)

    prereg = {
        "_README": (
            "SEALED pre-registration for the F&F engine-validation game (ticket #444). "
            "Written by the ENGINE-RUNNER role and git-committed BEFORE any outcome is computed. "
            "A different person runs score.py, verifies pack_sha256 matches, then scores against the "
            "sealed Table B (player_outcomes). The named failure mode to guard against is WANTING IT TO PASS."
        ),
        "ticket": "#444",
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "engine-runner (BLIND to player_outcomes)",
        "customer_id": CUSTOMER_ID,
        "pack_path": str(PACK_PATH.relative_to(REPO)),
        "pack_sha256": _sha256(PACK_PATH),
        "panel_registration": {
            "panel_id": reg.panel_id,
            "version": reg.version,
            "persona_count": reg.persona_count,
            "weight_scheme": reg.weight_scheme,
            "schema_version": reg.schema_version,
            "is_individual_row_capable": reg.is_individual_row_capable,
            "is_behavioral_seeds_complete": reg.is_behavioral_seeds_complete,
        },
        "engine_run_config": {
            "model": args.model,
            "population_per_item": args.population,
            "seed_base": args.seed,
            "treatment_fraction": 0.5,
            "predicted_winner_rule": "sign of paired metric_lift_pp (treatment - control)",
            "engine": "sidira_simulator.services.simulation_runner.SimulationRunner (FULL engine on the pack)",
        },
        "engine_predictions": engine_preds,
        "obvious_priors_audited": priors,
        "placebo_predictions": placebo,
        "win_rule": WIN_RULE,
        "stopping_rule": STOPPING_RULE,
    }

    if args.seal:
        Path(args.out).write_text(json.dumps(prereg, indent=2, default=str))
        print(f"\nSEALED -> {args.out}")
        print("  Engine-runner: git add + commit this file NOW, before any outcome is computed.")
    else:
        scratch = HERE / "predict_scratch.json"
        scratch.write_text(json.dumps(prereg, indent=2, default=str))
        print(f"\n(dry run; not sealed) wrote {scratch} — pass --seal to write PREREG_FF.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""F&F validation harness — STEP 3: ROLE-SEPARATED scoring (ticket #444).

ROLE: the *scorer* — a DIFFERENT person than the engine-runner who wrote
PREREG_FF.json. This script:

  1. Loads the SEALED ``PREREG_FF.json`` (engine + placebo predictions, priors, rules).
  2. VERIFIES the committed pack SHA-256 still matches the sealed value — if the pack
     was edited after sealing, the run is BURNED and scoring refuses to proceed.
  3. Reads Table B ``player_outcomes`` (arm, task_id, binary outcome) — the SEALED
     answer key the engine-runner never saw.
  4. Per item: computes the REAL winning arm via a two-proportion z-test + 95% CI on
     the two arms' outcome rates. Items whose real winner is a statistical TIE (CI on
     the difference straddles 0) are DROPPED SYMMETRICALLY for BOTH the engine and the
     placebo (so neither is scored on a coin-flip).
  5. Computes the engine hit-rate and the placebo hit-rate over the scored items.
  6. Emits the GO/NO-GO verdict per the SEALED win rule.
  7. Where a player->persona assignments map is available (sidecar), ALSO scores at the
     PLAYER level. The committed privacy-clean pack carries NO assignments map, so this
     is reported as INFEASIBLE unless a sidecar is supplied (the synthetic test supplies one).

    PYTHONPATH=backend backend/.venv/bin/python sessions/ff-validation-game/harness/score.py \
        --outcomes <player_outcomes.json|.csv> [--prereg PREREG_FF.json] [--assignments <map.json>] [--synthetic]

The scorer prints AND writes a verdict object. ``--synthetic`` stamps the output as a
MACHINERY TEST on synthetic outcomes (NOT a real validation result).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_PREREG = HERE / "PREREG_FF.json"

# 95% normal critical value for the two-proportion CI.
Z_95 = 1.959963984540054


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_outcomes(path: Path) -> list[dict]:
    """Load Table B rows: each {player_id, arm, task_id, outcome}.

    Accepts JSON (list of dicts, or {"rows": [...]}) or CSV with those columns.
    """
    text = path.read_text()
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        rows = data["rows"] if isinstance(data, dict) and "rows" in data else data
    else:
        rows = list(csv.DictReader(text.splitlines()))
    out = []
    for r in rows:
        out.append(
            {
                "player_id": str(r.get("player_id", "")),
                "arm": str(r["arm"]),
                "task_id": str(r["task_id"]),
                "outcome": int(r["outcome"]),
            }
        )
    return out


def _two_proportion(succ_a: int, n_a: int, succ_b: int, n_b: int) -> dict:
    """Two-proportion z-test + 95% CI on (rate_a - rate_b).

    Returns rates, the difference, its 95% CI, the z stat and a two-sided p-value.
    A CI straddling 0 (or n==0 on either arm) is a statistical tie.
    """
    if n_a == 0 or n_b == 0:
        return {"rate_a": None, "rate_b": None, "diff": None, "ci": None,
                "z": None, "p": None, "tie": True, "reason": "empty arm"}
    pa, pb = succ_a / n_a, succ_b / n_b
    diff = pa - pb
    # Pooled SE for the z-test.
    p_pool = (succ_a + succ_b) / (n_a + n_b)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b)) if 0 < p_pool < 1 else 0.0
    z = diff / se_pool if se_pool > 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))  # two-sided
    # Unpooled SE for the CI on the difference.
    se_ci = math.sqrt(pa * (1 - pa) / n_a + pb * (1 - pb) / n_b)
    ci = (diff - Z_95 * se_ci, diff + Z_95 * se_ci)
    tie = se_ci == 0.0 or (ci[0] <= 0.0 <= ci[1])
    return {"rate_a": round(pa, 4), "rate_b": round(pb, 4), "diff": round(diff, 4),
            "ci": [round(ci[0], 4), round(ci[1], 4)], "z": round(z, 4),
            "p": round(p, 4), "tie": tie, "reason": None}


def _binomial_at_least(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Used for the chance-bar one-sided test."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _real_winner_per_item(outcomes: list[dict], item_pred: dict) -> dict:
    """Compute the real winning arm for one item from Table B.

    Arm A = the item's control_arm, Arm B = the treatment_arm (as sealed). The real
    winner is whichever arm has the higher outcome rate IF the two-proportion CI
    excludes 0; otherwise the item is a statistical TIE (dropped symmetrically).
    """
    task = item_pred["task_id"]
    arm_a, arm_b = item_pred["control_arm"], item_pred["treatment_arm"]
    succ = defaultdict(int)
    n = defaultdict(int)
    for r in outcomes:
        if r["task_id"] != task:
            continue
        if r["arm"] in (arm_a, arm_b):
            n[r["arm"]] += 1
            succ[r["arm"]] += r["outcome"]
    stat = _two_proportion(succ[arm_a], n[arm_a], succ[arm_b], n[arm_b])
    if stat["tie"]:
        winner = None
    else:
        winner = arm_a if stat["diff"] > 0 else arm_b
    return {
        "task_id": task,
        "arm_a": arm_a, "arm_b": arm_b,
        "n_a": n[arm_a], "n_b": n[arm_b],
        "succ_a": succ[arm_a], "succ_b": succ[arm_b],
        "real_winner": winner,
        "is_tie": stat["tie"],
        "stat": stat,
    }


def score(prereg: dict, outcomes: list[dict], assignments: dict | None, synthetic: bool) -> dict:
    """Run the full role-separated scoring and produce the GO/NO-GO verdict object."""
    engine_by_task = {e["task_id"]: e for e in prereg["engine_predictions"]}
    placebo_by_task = {p["task_id"]: p for p in prereg["placebo_predictions"]}
    priors_by_task = {it["task_id"]: it for it in prereg["obvious_priors_audited"]["items"]}
    win_rule = prereg["win_rule"]
    ci_excludes = set(win_rule.get("counter_intuitive_excludes", []))

    per_item = []
    engine_hits = engine_scored = 0
    placebo_hits = placebo_scored = 0
    dropped_ties = 0
    engine_counter_intuitive_hits = []

    for task, epred in engine_by_task.items():
        real = _real_winner_per_item(outcomes, epred)
        ppred = placebo_by_task.get(task, {})
        prior = priors_by_task.get(task, {})
        # genuinely counter-intuitive = counter_intuitive AND not in the exclude list
        genuinely_ci = bool(prior.get("counter_intuitive")) and task not in ci_excludes

        if real["is_tie"]:
            dropped_ties += 1
            per_item.append({
                **real,
                "engine_predicted_arm": epred["engine_predicted_arm"],
                "placebo_predicted_arm": ppred.get("placebo_predicted_arm"),
                "engine_hit": None, "placebo_hit": None,
                "scored": False, "drop_reason": "statistical tie (CI on diff straddles 0)",
                "genuinely_counter_intuitive": genuinely_ci,
            })
            continue

        eng_hit = epred["engine_predicted_arm"] == real["real_winner"]
        plc_hit = ppred.get("placebo_predicted_arm") == real["real_winner"]
        engine_scored += 1
        placebo_scored += 1
        engine_hits += int(eng_hit)
        placebo_hits += int(plc_hit)
        if eng_hit and genuinely_ci:
            engine_counter_intuitive_hits.append(task)
        per_item.append({
            **real,
            "engine_predicted_arm": epred["engine_predicted_arm"],
            "placebo_predicted_arm": ppred.get("placebo_predicted_arm"),
            "engine_hit": eng_hit, "placebo_hit": plc_hit,
            "scored": True, "genuinely_counter_intuitive": genuinely_ci,
        })

    K_fielded = len(engine_by_task)  # items pre-registered/fielded
    K = engine_scored  # items actually scored (after symmetric tie drops)
    engine_rate = engine_hits / K if K else 0.0
    placebo_rate = placebo_hits / placebo_scored if placebo_scored else 0.0
    # One-sided binomial: P(>= engine_hits successes in K flips) under chance (p=0.5).
    binom_p = _binomial_at_least(engine_hits, K, 0.5) if K else 1.0
    alpha = win_rule["binomial"].get("alpha", 0.10)

    # GO gates.
    # K_min gates the FIELDED count (the doc designs K=5-6 so a sweep can beat chance;
    # a 4/4 AFTER a tie drop from >=5 fielded is still a valid proof-of-life). The
    # binomial bar then runs on the SCORED count (post tie-drop).
    gate_K = K_fielded >= win_rule["K_min"]
    gate_binomial = K >= 1 and binom_p <= alpha
    gate_beats_placebo = engine_hits > placebo_hits  # STRICTLY beats
    gate_counter_intuitive = len(engine_counter_intuitive_hits) >= 1
    go = bool(gate_K and gate_binomial and gate_beats_placebo and gate_counter_intuitive)

    verdict = {
        "_README": (
            "ROLE-SEPARATED scoring verdict (ticket #444). The scorer is a DIFFERENT person than the "
            "engine-runner; the pack SHA was verified against the seal before scoring. "
            + ("THIS IS A MACHINERY TEST ON SYNTHETIC OUTCOMES — NOT A REAL VALIDATION RESULT. "
               if synthetic else "")
            + "Failure mode guarded against: WANTING IT TO PASS."
        ),
        "is_synthetic_machinery_test": synthetic,
        "pack_sha256_verified": True,  # set by caller before calling score()
        "K_fielded": K_fielded,
        "K_scored": K,
        "dropped_ties": dropped_ties,
        "engine_hits": engine_hits, "engine_hit_rate": round(engine_rate, 4),
        "placebo_hits": placebo_hits, "placebo_hit_rate": round(placebo_rate, 4),
        "binomial_p_one_sided": round(binom_p, 4), "binomial_alpha": alpha,
        "engine_counter_intuitive_hits": engine_counter_intuitive_hits,
        "gates": {
            "K_ge_min": gate_K,
            "binomial_beats_chance": gate_binomial,
            "engine_strictly_beats_placebo": gate_beats_placebo,
            "engine_right_on_ge1_genuine_counter_intuitive": gate_counter_intuitive,
        },
        "verdict": "GO" if go else "NO-GO",
        "verdict_basis": win_rule["description"],
        "per_item": per_item,
    }

    # ── Optional player-level scoring via the assignments map ──
    if assignments:
        verdict["player_level"] = _player_level(prereg, outcomes, assignments)
    else:
        verdict["player_level"] = {
            "feasible": False,
            "reason": (
                "The committed privacy-clean pack carries head_count weights + sample_rows "
                "statistics only, NOT a player_id->persona_id assignments map. Player-level "
                "scoring requires that map (supply --assignments). Population/per-item scoring "
                "above is the sealed primary analysis."
            ),
        }
    return verdict


def _player_level(prereg: dict, outcomes: list[dict], assignments: dict) -> dict:
    """Player-level scoring: for each player, did the engine's predicted item-winner
    match the player's own realized choice on that item?

    This counts, per (player, item), whether the player's outcome agrees with the
    arm the engine predicted to win. It is a finer-grained companion to the
    population-level hit-rate (the sealed primary unit of evidence). Reported as an
    agreement rate; not itself a GO gate.
    """
    engine_by_task = {e["task_id"]: e for e in prereg["engine_predictions"]}
    # For a player on arm X with outcome o: the player "converted on arm X" iff o==1.
    # The engine predicted arm P wins. We count agreement = player on the predicted
    # winning arm converted, OR player on the other arm did not convert.
    agree = total = 0
    by_persona = defaultdict(lambda: [0, 0])
    for r in outcomes:
        e = engine_by_task.get(r["task_id"])
        if not e or e["engine_predicted_arm"] is None:
            continue
        persona = assignments.get(r["player_id"])
        on_predicted = r["arm"] == e["engine_predicted_arm"]
        # agreement: engine says predicted arm drives the outcome up
        pred_says_convert = on_predicted
        actual_convert = r["outcome"] == 1
        agree += int(pred_says_convert == actual_convert)
        total += 1
        if persona is not None:
            by_persona[persona][0] += int(pred_says_convert == actual_convert)
            by_persona[persona][1] += 1
    return {
        "feasible": True,
        "agreement_rate": round(agree / total, 4) if total else None,
        "n_player_item": total,
        "by_persona": {k: {"agree": v[0], "n": v[1]} for k, v in by_persona.items()},
        "note": "companion metric; the sealed GO gate is the population per-item hit-rate",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="ROLE-SEPARATED F&F scoring (#444).")
    ap.add_argument("--outcomes", required=True, help="Table B player_outcomes (.json or .csv)")
    ap.add_argument("--prereg", default=str(DEFAULT_PREREG))
    ap.add_argument("--assignments", default=None, help="optional player_id->persona_id JSON map")
    ap.add_argument("--out", default=str(HERE / "verdict_FF.json"))
    ap.add_argument("--synthetic", action="store_true",
                    help="stamp output as a MACHINERY TEST on synthetic outcomes")
    args = ap.parse_args()

    prereg_path = Path(args.prereg)
    prereg = json.loads(prereg_path.read_text())

    # ── Hash gate: verify the committed pack still matches the sealed SHA ──
    pack_path = REPO / prereg["pack_path"]
    actual_sha = _sha256(pack_path)
    if actual_sha != prereg["pack_sha256"]:
        print("SEAL BROKEN: the pack SHA-256 does NOT match the sealed pre-registration.")
        print(f"  sealed: {prereg['pack_sha256']}")
        print(f"  actual: {actual_sha}")
        print("  The run is BURNED — the pack was edited after sealing. Refusing to score.")
        return 2
    print(f"Pack SHA-256 verified against seal: {actual_sha[:16]}... OK")

    outcomes = _load_outcomes(Path(args.outcomes))
    assignments = json.loads(Path(args.assignments).read_text()) if args.assignments else None

    verdict = score(prereg, outcomes, assignments, synthetic=args.synthetic)
    Path(args.out).write_text(json.dumps(verdict, indent=2, default=str))

    banner = ("  *** SYNTHETIC MACHINERY TEST — NOT A REAL VALIDATION RESULT ***"
              if args.synthetic else "")
    print(f"\n=== F&F SCORING VERDICT ==={banner}")
    print(f"  K fielded: {verdict['K_fielded']}  |  K scored: {verdict['K_scored']}  (dropped ties: {verdict['dropped_ties']})")
    print(f"  engine hit-rate:  {verdict['engine_hits']}/{verdict['K_scored']} = {verdict['engine_hit_rate']}")
    print(f"  placebo hit-rate: {verdict['placebo_hits']}/{verdict['K_scored']} = {verdict['placebo_hit_rate']}")
    print(f"  binomial p (one-sided, chance=0.5): {verdict['binomial_p_one_sided']} (alpha {verdict['binomial_alpha']})")
    print(f"  engine right on genuine counter-intuitive items: {verdict['engine_counter_intuitive_hits']}")
    for g, ok in verdict["gates"].items():
        print(f"    gate {g}: {'PASS' if ok else 'FAIL'}")
    print(f"  >>> VERDICT: {verdict['verdict']} <<<")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

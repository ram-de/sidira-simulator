#!/usr/bin/env python3
"""Gated accuracy + cost benchmark — Milkman gym megastudy (#39).

REAL stored data only, NO live engine call:
  - engine ranking (blind):  gym-engine-backtest/engine_ranking.txt   (rank -> nudge)
  - true effects:            milkman-gym-megastudy/forecasts/main_coef.csv (nudge -> coef)

Framing the founder asked for: treat each of the 54 interventions as one candidate
A/B EXPERIMENT that costs $C to actually run. You cannot run all of them. Sidira
ranks them; you run the top-B it prioritises and skip the rest. We measure (a) how
much of the achievable real effect that captures vs random selection, and (b) the $
saved by not running the whole slate.

HONEST SCOPE — read before quoting any number:
  * The gym domain is all-positive (every nudge beats control on attendance), so this
    is a RANKING/prioritisation problem, not a sign problem. Sign-accuracy gates are
    N/A here; we report rank metrics (Spearman / Kendall) + tail-winner recall.
  * The stored blind run is a pure ORDERING with NO per-case confidence, so it CANNOT
    demonstrate the calibrated callable-vs-too-tough ABSTENTION gate (the moat) — that
    needs a live engine run emitting confidence_score per case. This script therefore
    proves the COST METHODOLOGY on real data and gives an honest rank-skill read; the
    abstention proof is a separate live-run deliverable.
  * Prior measured skill on this set: Spearman rho ~ +0.13 (n.s.); lay crowd ~ +0.27.
    Expect modest savings, reported honestly.
"""
from __future__ import annotations

import csv
import datetime
import re
from pathlib import Path

from bench_store import record_run

HERE = Path(__file__).resolve().parent
# Canonical repo-relative location: sessions/agent-behavior-spec/datasets/...
# (HERE is sessions/agent-behavior-spec/gated-cost-benchmark, so parents[0] is
# sessions/agent-behavior-spec). The raw SSPP data is large and not committed on
# every branch, so we also probe a sibling worktree that has it — purely a
# local-dev convenience; the canonical path is the source of truth.
BASE = HERE.parents[0] / "datasets" / "sspp-dellavigna-vivalt"
_SIBLING = (
    "/Users/ram/Projects/sidira-simulator/.claude/worktrees/benchmark-gate-validation"
    "/sessions/agent-behavior-spec/datasets/sspp-dellavigna-vivalt"
)
CANDIDATES = [BASE, Path(_SIBLING)]


def _data_root() -> Path:
    for c in CANDIDATES:
        if (c / "milkman-gym-megastudy" / "forecasts" / "main_coef.csv").exists():
            return c
    raise SystemExit("gym data not found in any known location")


def _norm(name: str) -> str:
    """Loose key for matching nudge names across the two files."""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def load_truth(root: Path) -> dict[str, float]:
    rows = list(csv.DictReader(open(root / "milkman-gym-megastudy" / "forecasts" / "main_coef.csv")))
    return {_norm(r["factor"]): float(r["coef"]) for r in rows}


def load_engine_order(root: Path) -> list[str]:
    order: list[tuple[int, str]] = []
    for line in open(root / "gym-engine-backtest" / "engine_ranking.txt"):
        m = re.match(r"\s*(\d+)\s+(.*\S)\s*$", line)
        if m:
            order.append((int(m.group(1)), _norm(m.group(2))))
    order.sort()
    return [name for _, name in order]


def spearman(x: list[float], y: list[float]) -> float:
    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def main() -> None:
    root = _data_root()
    truth = load_truth(root)
    engine_order = load_engine_order(root)
    matched = [n for n in engine_order if n in truth]
    unmatched = [n for n in engine_order if n not in truth]
    N = len(matched)

    # engine rank position (1 = engine's best) vs true coef
    engine_rank = {name: i + 1 for i, name in enumerate(matched)}
    true_sorted = sorted(matched, key=lambda n: truth[n], reverse=True)  # best effect first
    true_rank = {name: i + 1 for i, name in enumerate(true_sorted)}

    rho = spearman([engine_rank[n] for n in matched], [true_rank[n] for n in matched])
    total_effect = sum(truth[n] for n in matched)

    # cumulative TRUE effect captured by testing the engine's top-B, vs the
    # expected random pick (B/N of total), vs the oracle (true top-B).
    def captured(order: list[str], B: int) -> float:
        return sum(truth[n] for n in order[:B])

    oracle_order = true_sorted
    print(f"data root: {root}")
    print(f"matched interventions: {N}  (unmatched engine names: {len(unmatched)})")
    print(f"engine rank vs true rank  Spearman rho = {rho:+.3f}")
    print(f"total achievable effect (sum coef) = {total_effect:.2f}\n")

    print("B   engine%  random%  oracle%   tail-recall@B")
    for B in (5, 10, 15, 20, 27):
        eng = captured(engine_order if False else [n for n in engine_order if n in truth], B)
        eng = captured(matched, B)
        ora = captured(oracle_order, B)
        rnd = total_effect * B / N
        true_topB = set(true_sorted[:B])
        recall = len(true_topB & set(matched[:B])) / B
        print(f"{B:<3} {100*eng/total_effect:6.1f}  {100*rnd/total_effect:6.1f}  "
              f"{100*ora/total_effect:7.1f}   {recall:0.2f}")

    # --- cost model -------------------------------------------------------
    # Each intervention = one real A/B test costing $C. To capture a TARGET share
    # of the achievable effect, how many tests does Sidira-ranked need vs random
    # (expected)? Savings = (random_B - sidira_B) * C.
    def tests_to_reach(order: list[str], target_frac: float) -> int:
        goal = target_frac * total_effect
        run = 0.0
        for i, n in enumerate(order, 1):
            run += truth[n]
            if run >= goal:
                return i
        return len(order)

    print("\n--- cost model (per-experiment cost C; report in units of C) ---")
    for target in (0.5, 0.7, 0.8):
        s = tests_to_reach(matched, target)
        # random expected: capturing target_frac of total needs ~target_frac*N draws
        r = round(target * N)
        print(f"capture {int(target*100)}% of achievable effect:  "
              f"Sidira-ranked {s} tests  vs  random ~{r} tests  ->  saves {r - s} tests "
              f"= {r - s}*C")
    for C in (10_000, 30_000, 100_000):
        s = tests_to_reach(matched, 0.7)
        r = round(0.7 * N)
        print(f"   at C=${C:,}/test, reaching 70% effect saves ~${(r - s) * C:,}")

    # --- record this run to the reusable ledger ---------------------------
    top5_cap = 100 * captured(matched, 5) / total_effect
    top5_rnd = 100 * (total_effect * 5 / N) / total_effect
    tail5 = len(set(true_sorted[:5]) & set(matched[:5])) / 5
    saved_70 = round(0.7 * N) - tests_to_reach(matched, 0.7)
    ledger = record_run(
        run_id="gym-rank-stored-blind",
        run_date=datetime.date.today().isoformat(),
        dataset="milkman-gym-megastudy",
        domain_type="rank",
        n_cases=N,
        engine_ref="stored blind ranking (gym-engine-backtest/engine_ranking.txt)",
        gated="no",  # stored run has no per-case confidence -> abstention gate N/A
        primary_metric=f"spearman_rho={rho:+.3f}",
        tail_recall_at5=f"{tail5:.2f}",
        top5_capture=f"{top5_cap:.1f}%",
        top5_random=f"{top5_rnd:.1f}%",
        callable_accuracy="",   # n/a — no confidence in stored run
        abstain_rate="",        # n/a
        cost_per_experiment="$30k",
        dollars_saved=f"${saved_70 * 30}k (to 70% effect)",
        verdict="rank-only (sign gate N/A: all-positive domain)",
        scope_caveat="weak overall rank skill; edge concentrated at small budgets; "
                     "no calibrated abstention (stored run lacks per-case confidence)",
        source_files="engine_ranking.txt + milkman-gym main_coef.csv",
    )
    print(f"\nrecorded run to ledger: {ledger}")


if __name__ == "__main__":
    main()

"""Re-score the committed Upworthy confirming run through the G0-G11 gate.

Reads confirm_result.json (60 Groq llama-3.3-70b predictions vs real CTR lift)
and runs the full directional_gate certification — the complete metric panel and
GO/CONDITIONAL/NO-GO verdict — alongside the original run's rank_rho + direction
accuracy + null-integrity certificate. Zero LLM spend.

Run:
    PYTHONPATH=backend <venv>/bin/python \
        sessions/agent-behavior-spec/upworthy-benchmark/rescore_through_gate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
from sidira_simulator.services.directional_gate import (  # noqa: E402
    ExperimentRecord, GateConfig, certify,
)


def load_records(path: Path) -> tuple[list[ExperimentRecord], dict]:
    d = json.loads(path.read_text())
    recs = []
    for c in d["case_results"]:
        if c.get("dropped"):
            continue
        recs.append(ExperimentRecord(
            case_id=c["case_id"],
            observed_lift=float(c["observed_lift"]),
            predicted_signal=float(c["prediction"]),
        ))
    return recs, d


def main() -> int:
    path = HERE / "confirm_result.json"
    recs, orig = load_records(path)
    n = len(recs)
    # δ=0 matches the original sign-based direction accuracy. budget = top ~25%.
    cfg = GateConfig(delta=0.0, budget=max(1, n // 4), bootstrap_trials=2000,
                     seed=int(orig.get("seed", 42)), conf=0.90)
    res = certify(recs, cfg, aa=None)  # no A/A arm in this artifact (G1 vacuous)
    m = res.metrics

    print("=" * 70)
    print("RE-SCORE: Upworthy confirming run (Groq llama-3.3-70b) through G0-G11")
    print("=" * 70)
    print(f"n_cases={n}  n_dir={m['n_dir']}  n_pos={m['n_pos']}  n_neg={m['n_neg']}")
    print()
    print("--- ORIGINAL run scoring (from confirm_result.json) ---")
    print(f"  rank_rho (Spearman, PRIMARY) = {orig['rank_rho']:+.3f}  "
          f"(p={orig['certificate']['rank_rho_p_value']:.3f})")
    print(f"  direction_accuracy           = {orig['direction_accuracy']:.3f}  "
          f"(p={orig['certificate']['direction_accuracy_p_value']:.3f})")
    print(f"  null-integrity certificate   = PASSED={orig['certificate']['passed']} "
          f"void={orig['void']}  (marginal chance acc={orig['certificate']['marginal_chance_accuracy']:.3f})")
    print()
    print("--- FULL G0-G11 gate (this re-score) ---")
    print(f"  G4 balanced SMR      = {m['balanced_smr']:.3f}  (Wilson 90% LB {m['smr_wilson_lo']:.3f})")
    print(f"  G6 Kendall tau_b     = {m['kendall_tau_b']:+.3f} (90% LB {m['kendall_tau_b_lo']:+.3f})  "
          f"[Spearman {m['spearman_rho']:+.3f}]")
    print(f"  G5 3-class MCC       = {m['mcc']:+.3f}  (minus baseline, 90% LB {m['mcc_lo']:+.3f})")
    print(f"  G7 ECE               = {m['ece']:.3f}   Brier {m['brier']:.3f} vs climatology "
          f"{m['brier_climatology']:.3f}  (skill {m['brier_skill']:+.3f})")
    print(f"  G8 decision utility  = {m['delta_u']:+.2f} (90% LB {m['delta_u_lo']:+.2f})  [PRIMARY]")
    print(f"  G9 tail-winner recall= {m['tail_winner_recall']:.2f}")
    print(f"  G3 perm-null SMR     = {m['perm_smr']:.3f}")
    print()
    print(res.summary())
    print()
    # machine-readable artifact for the live report / CI
    out = {
        "source_artifact": "confirm_result.json",
        "model": "groq/llama-3.3-70b-versatile",
        "n_cases": n,
        "original": {
            "rank_rho": orig["rank_rho"],
            "direction_accuracy": orig["direction_accuracy"],
            "null_integrity_passed": orig["certificate"]["passed"],
        },
        "gate": {"verdict": res.verdict, "gates": res.gates, "metrics": m,
                 "notes": res.notes},
        "config": {"delta": cfg.delta, "budget": cfg.budget, "seed": cfg.seed,
                   "bootstrap_trials": cfg.bootstrap_trials, "conf": cfg.conf},
    }
    (HERE / "gate_rescore_result.json").write_text(json.dumps(out, indent=2))
    print(f"wrote {HERE / 'gate_rescore_result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

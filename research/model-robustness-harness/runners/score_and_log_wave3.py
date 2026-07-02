"""Score wave-3 auto-discovery results vs sealed predictions; write SCORECARD_WAVE3.md; append runs; regen LEDGER."""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parent
RES = json.loads((HERE / "bakeoff_wave3_results.json").read_text())["results"]
SHA = (HERE / "PREREG_WAVE3.sha256").read_text().split()[0]
MNAME = {"m1": "X-learner CATE importance", "m2": "transformed-outcome honest tree", "m3": "BLP linear"}
METHODS = ["m1", "m2", "m3"]

hetero = [r for r in RES if r["role"] in ("hetero", "hetero_stress")]
spec = [r for r in RES if r["role"] in ("constant_specificity", "true_null")]

L = ["# Method Bake-Off Wave 3 — Scorecard: AUTO-DISCOVERY of the effect-modifier", "",
     f"Sealed predictions sha256 `{SHA[:16]}…` (frozen before any run; nothing tuned to match).", "",
     "Q: discover WHICH covariate the effect concentrates/flips on, WITHOUT being told — and stay silent on null.",
     "True modifier = USAGE axis {plays_28d, watch_minutes_28d, avg_session_min, completion_rate, titles_started_28d}; "
     "plan_tier = null axis. Floor rule: discovered iff stat>95th-pct(placebo) AND ratio≥1.5.", ""]

# ---- 1. Modifier-discovery scoreboard --------------------------------------- #
L += ["## 1. Modifier-discovery scoreboard", "",
      "Cell = top-ranked covariate · discovered?(floor) · ✓/✗ vs ground truth.", "",
      "| dataset | role | CATEvar-ratio | " + " | ".join(MNAME[m] for m in METHODS) + " |",
      "|---|---|---|---|---|---|"]
sens = {m: [0, 0] for m in METHODS}    # hits, total  (hetero only, role=='hetero')
specc = {m: [0, 0] for m in METHODS}   # correct-quiet, total
stress = {m: [0, 0] for m in METHODS}  # hetero_stress
for r in RES:
    cells = []
    for m in METHODS:
        mm = r["methods"][m]
        disc = mm["discovered"]; top = mm["top_covariate"]
        if r["role"] in ("hetero", "hetero_stress"):
            ok = disc and mm["top_is_usage"] and mm["top_above_plan"]
            mark = "✓" if ok else "✗"
            (sens if r["role"] == "hetero" else stress)[m][1] += 1
            (sens if r["role"] == "hetero" else stress)[m][0] += ok
            cells.append(f"{top} · {'DISC' if disc else 'none'} · {mark}")
        else:  # specificity: correct = NOT discovered
            ok = not disc
            mark = "✓none" if ok else f"✗invented({top})"
            specc[m][1] += 1; specc[m][0] += ok
            cells.append(f"{'DISC('+top+')' if disc else 'none'} · {mark}")
    L.append(f"| {r['tag']} | {r['role']} | {r['cate_var_ratio']} | " + " | ".join(cells) + " |")

L += ["", "**Sensitivity (clean hetero):** " + " · ".join(f"{MNAME[m]} {sens[m][0]}/{sens[m][1]}" for m in METHODS),
      "**Sensitivity under confounding stress:** " + " · ".join(f"{MNAME[m]} {stress[m][0]}/{stress[m][1]}" for m in METHODS),
      "**Specificity (no false discovery on null/constant):** " + " · ".join(f"{MNAME[m]} {specc[m][0]}/{specc[m][1]}" for m in METHODS), ""]

# ---- 2. Downstream sign recovery -------------------------------------------- #
L += ["## 2. Downstream sign recovery after AUTO-discovery", "",
      "After auto-picking the modifier, split at its median; low-usage should be + , high-usage − "
      "(matches the Wave-2 told-the-modifier result casual=+/power=−).", "",
      "| dataset | method | auto-modifier | low-usage CATE | high-usage CATE | both signs ✓? |",
      "|---|---|---|---|---|---|"]
down = {m: [0, 0] for m in METHODS}      # clean hetero only
down_st = {m: [0, 0] for m in METHODS}   # confounding stress
for r in hetero:
    for m in METHODS:
        d = r["downstream"][m]
        bucket = down if r["role"] == "hetero" else down_st
        bucket[m][1] += 1; bucket[m][0] += d["both_signs_recovered"]
        L.append(f"| {r['tag']} ({r['role']}) | {MNAME[m]} | {d['modifier']} | "
                 f"{d['low_usage_cate']:+.4f} ({d['low_sign'][:3]}) | "
                 f"{d['high_usage_cate']:+.4f} ({d['high_sign'][:3]}) | "
                 f"{'✓' if d['both_signs_recovered'] else '✗'} |")
L += ["", "**Downstream both-signs recovery (clean hetero):** "
      + " · ".join(f"{MNAME[m]} {down[m][0]}/{down[m][1]}" for m in METHODS),
      "**Downstream under confounding stress:** "
      + " · ".join(f"{MNAME[m]} {down_st[m][0]}/{down_st[m][1]}" for m in METHODS)
      + " — discovery survives but the high-usage NEGATIVE segment washes to ~0 under injected selection.",
      "Wave-2 baseline (handed the composite modifier): X-learner recovered both per-segment signs on both clean datasets — "
      "auto-discovery REPRODUCES that on clean data.", ""]

# ---- runstore: one run per method ------------------------------------------- #
sys.path.insert(0, str(HERE))
import runstore
ARTS = ["method-bakeoff/bakeoff_wave3.py", "method-bakeoff/bakeoff_wave3_results.json",
        "method-bakeoff/PREREG_WAVE3.md", "method-bakeoff/SCORECARD_WAVE3.md"]
N_TOTAL = sum(r["n"] for r in RES)
verdicts = {}
for m in METHODS:
    s = sens[m]; sp = specc[m]; st = stress[m]; dn = down[m]
    head = (f"sensitivity {s[0]}/{s[1]} (rank true USAGE modifier #1) · "
            f"specificity {sp[0]}/{sp[1]} (no false discovery on null/constant) · "
            f"stress {st[0]}/{st[1]} · downstream signs {dn[0]}/{dn[1]}")
    verdicts[f"bakeoff3-{m}"] = dict(
        title=f"bake-off W3: auto-discover modifier — {MNAME[m]}",
        dataset="synthetic_streamly_v2v3 + truenull", data_type="synthetic",
        verdict="MECH-ONLY", head=head, n=N_TOTAL)

for run_id, v in verdicts.items():
    runstore.append_run(dict(run_id=run_id, idea="bakeoff-wave3", title=v["title"],
        dataset=v["dataset"], data_type=v["data_type"], verdict=v["verdict"], prereg_sha=SHA,
        n=v["n"], baseline="true modifier = USAGE axis (by-construction); null = plan_tier / true-null",
        result={"headline": v["head"]}, replicated=None, adversarially_verified=None,
        artifacts=ARTS, notes="auto-discovery of effect-modifier; synthetic ⇒ MECH-ONLY"))
runstore.regenerate_ledger()
(HERE / "SCORECARD_WAVE3.md").write_text("\n".join(L))
print("wrote SCORECARD_WAVE3.md; logged", len(verdicts), "runs; regenerated LEDGER.md")
# console summary
for m in METHODS:
    print(f"{m} {MNAME[m]:34} sens {sens[m][0]}/{sens[m][1]}  stress {stress[m][0]}/{stress[m][1]}  "
          f"spec {specc[m][0]}/{specc[m][1]}  down {down[m][0]}/{down[m][1]}")

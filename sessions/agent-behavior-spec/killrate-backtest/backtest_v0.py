"""Kill-rate backtest v0 (#602) — sim-free grounded triage vs known outcomes.

Rules sealed in PREREG_KILLRATE_V0.md BEFORE this script was run.
Verdicts are computed from pre-launch-knowable inputs only; outcomes are
joined at scoring time.
"""
import json
import math

import numpy as np
import pandas as pd
from scipy import stats

SCRATCH = "/private/tmp/claude-502/-Users-ram-Projects-sidira-simulator/7d1fcf63-0e16-40b3-baac-8681e42ca90d/scratchpad"
Z_A, Z_B = 1.959964, 0.841621  # alpha=.05 two-sided, 80% power


def mde_abs(p, n_arm):
    return (Z_A + Z_B) * math.sqrt(2.0 * p * (1.0 - p) / n_arm)


# ---------------------------------------------------------------- portfolio 8
print("=" * 72)
print("CORPUS 1: portfolio scored_cases (published narratives)")
print("=" * 72)
cases = json.load(open(f"{SCRATCH}/PORTFOLIO_CASES.json"))["scored_cases"]

# Pre-launch-knowable quantitative facts per prereg (published sources only).
PRELAUNCH = {
    "cookiecats_gate_move": {"n_arm": 45094, "baseline": 0.19, "metric_max": 1.0},
    "tinkoff_defer_passport": {"n_arm": 132500, "baseline": None, "metric_max": 1.0},
}

verdicts = []
for c in cases:
    cid = c["id"]
    facts = PRELAUNCH.get(cid, {})
    n_arm, base = facts.get("n_arm"), facts.get("baseline")
    fired, assessed = [], []
    if n_arm and base:
        assessed.append("K1")
        rel = mde_abs(base, n_arm) / base
        if rel > 0.10:
            fired.append(f"K1(MDE_rel={rel:.1%})")
        if base >= 0.9 * facts.get("metric_max", 1.0):
            fired.append("K2")
        assessed.append("K2")
    verdict = ("KILL" if fired else "RUN") if assessed else "CANNOT_ASSESS"
    verdicts.append((cid, verdict, ",".join(fired) or ",".join(assessed) or "no pre-launch quantitative facts published"))

# scoring (outcomes read only now)
print(f"{'case':34s} {'verdict':14s} {'outcome':8s} detail")
n_assess = n_fail = n_win = killed_fail = killed_win = 0
for (cid, verdict, why), c in zip(verdicts, cases):
    failed = c["real_winner"] == "control"
    print(f"{cid:34s} {verdict:14s} {'FAILED' if failed else 'WON':8s} {why}")
    if verdict == "CANNOT_ASSESS":
        continue
    n_assess += 1
    if failed:
        n_fail += 1
        killed_fail += verdict == "KILL"
    else:
        n_win += 1
        killed_win += verdict == "KILL"
print(f"\ncoverage: {n_assess}/{len(cases)} assessable | kills on failures: "
      f"{killed_fail}/{n_fail} | false kills on winners: {killed_win}/{n_win}")

# ---------------------------------------------------------------- hillstrom
print()
print("=" * 72)
print("CORPUS 2: Hillstrom email RCT (raw rows, per-metric triage)")
print("=" * 72)
hd = pd.read_csv("/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv")
seg_col = "segment" if "segment" in hd.columns else hd.columns[hd.columns.str.contains("segment", case=False)][0]
ctrl = hd[hd[seg_col].str.contains("No E-Mail", case=False)]
arms = {s: g for s, g in hd.groupby(seg_col) if "No E-Mail" not in s}
for metric in ["visit", "conversion"]:
    base = float(ctrl[metric].mean())
    n_arm = int(min(len(ctrl), min(len(g) for g in arms.values())))
    rel = mde_abs(base, n_arm) / base
    verdict = "KILL" if rel > 0.10 else "RUN"
    # ground truth: best arm vs control, two-proportion z
    best_p = 0.0
    for s, g in arms.items():
        p1, p0 = g[metric].mean(), base
        pp = (g[metric].sum() + ctrl[metric].sum()) / (len(g) + len(ctrl))
        z = (p1 - p0) / math.sqrt(pp * (1 - pp) * (1 / len(g) + 1 / len(ctrl)))
        best_p = max(best_p, abs(z))
    sig = 2 * (1 - stats.norm.cdf(best_p)) < 0.05
    ok = "correct" if (verdict == "KILL") != sig else ("FALSE KILL" if verdict == "KILL" else "correct")
    if verdict == "RUN" and not sig:
        ok = "missed kill"
    print(f"metric={metric:11s} baseline={base:.4f} n/arm={n_arm} MDE_rel={rel:.1%} "
          f"-> {verdict:4s} | actual: {'SIGNIFICANT' if sig else 'inconclusive'} ({ok})")

# ---------------------------------------------------------------- upworthy
print()
print("=" * 72)
print("CORPUS 3: Upworthy archive (per-arm impressions/clicks)")
print("=" * 72)
up = pd.read_csv("/Users/ram/Projects/sidira-simulator/local-artifacts/upw_bench/archive.csv",
                 usecols=["clickability_test_id", "impressions", "clicks"])
g = up.groupby("clickability_test_id").agg(arms=("clicks", "size"),
                                           imp=("impressions", "sum"),
                                           clk=("clicks", "sum"))
universe_ids = g[(g.arms >= 2) & (g.imp >= 1000)].index
up = up[up.clickability_test_id.isin(universe_ids)]
print(f"universe: {len(universe_ids)} tests (>=2 arms, >=1000 impressions)")

base_ctr = float((up.clicks / up.impressions.clip(lower=1)).median())

# ground truth: chi-square across arms per test
rows = []
for tid, arm in up.groupby("clickability_test_id"):
    imp, clk = arm.impressions.to_numpy(float), arm.clicks.to_numpy(float)
    if (imp <= 0).any() or clk.sum() == 0 or (clk > imp).any():
        continue
    obs = np.array([clk, imp - clk]).T
    try:
        _, pval, _, _ = stats.chi2_contingency(obs)
    except ValueError:
        continue
    ctr = clk / imp
    order = np.argsort(ctr)[::-1]
    rel_lift = (ctr[order[0]] - ctr[order[1]]) / max(ctr[order[1]], 1e-9) if len(ctr) > 1 else 0.0
    rows.append((tid, len(arm), imp.mean(), pval < 0.05, rel_lift))
res = pd.DataFrame(rows, columns=["tid", "arms", "n_arm", "conclusive", "winner_rel_lift"])

prior = float(res.loc[res.conclusive, "winner_rel_lift"].median())
print(f"baseline CTR (median pkg): {base_ctr:.4f} | plausible-effect prior "
      f"(median winner rel-lift among conclusive): {prior:.1%}")

res["mde_rel"] = res.n_arm.map(lambda n: mde_abs(base_ctr, n) / base_ctr)
res["kill"] = res.mde_rel > prior

fails = res[~res.conclusive]
wins = res[res.conclusive]
kf, fw = int(fails.kill.sum()), int(wins.kill.sum())
print(f"\ntests: {len(res)} | conclusive (found a winner): {len(wins)} "
      f"| inconclusive (wasted slot): {len(fails)}")
print(f"KILL rate on wasted slots:  {kf}/{len(fails)} = {kf/len(fails):.1%}")
print(f"FALSE kills on winners:     {fw}/{len(wins)} = {fw/len(wins):.1%}")
saved = kf
print(f"\nheadline: triage would have flagged {saved} of {len(fails)} wasted "
      f"tests ex ante ({saved/len(fails):.0%}), at {fw/len(wins):.1%} false-kill cost")
# sensitivity: kill threshold at 0.5x and 2x prior
for mult in (0.5, 2.0):
    k = res.mde_rel > prior * mult
    s = int((k & ~res.conclusive).sum())
    f = int((k & res.conclusive).sum())
    print(f"  sensitivity prior x{mult}: kills {s}/{len(fails)} wasted ({s/len(fails):.0%}), "
          f"false-kills {f}/{len(wins)} ({f/len(wins):.1%})")

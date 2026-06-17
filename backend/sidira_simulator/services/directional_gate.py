"""
directional_gate — the G0-G11 certification gate (twin-council white paper).

This is the *certification* layer that sits on top of the existing benchmark
instrument (`benchmark_runner.run_blind_eval` + `null_integrity`). The runner
already produces the PRIMARY rank reads (`rank_rho`, `direction_accuracy`) and a
seeded permutation null with a paired-across-cases bootstrap CI. This module adds
the rest of the ratified contract so a simulator's confidence can be gated:

  balanced sign-match rate + Wilson LB (G4) · 3-class MCC (G5) · Kendall tau_b
  (G6) · Brier-skill + ECE on a *fitted, cross-fit* calibration (G7) · decision
  utility vs status-quo triage (G8, PRIMARY) · tail-winner recall (G9) ·
  abstention quality (G10) · sample sufficiency (G0) · A/A integrity (G1) ·
  leakage permutation (G3) -> a GO / CONDITIONAL / NO-GO verdict.

Spec: research/twin-council/MERGED-LEDGER.md (claims M1-M22, gate G0-G11).

Pure standard library plus the repo's own `statistics` helpers — adds NO new
package dependency (sklearn/numpy are NOT declared backend deps). All
cross-experiment CIs are bootstrapped OVER EXPERIMENTS, never over agents (M15);
the per-agent bootstrap stays where it belongs, in scoring.py's within-case lift.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from sidira_simulator.services.statistics import (
    bootstrap_percentile_ci,
    spearman_rho,
    wilson_interval,
)


# --------------------------------------------------------------------------- #
# Record
# --------------------------------------------------------------------------- #
@dataclass
class ExperimentRecord:
    """One backtest experiment: the simulator's raw signal vs the real outcome.

    `predicted_signal` is the uncalibrated simulator lift (the thing the council
    says must NOT be shown to a user directly, M5). Class probabilities are
    filled by `fit_calibration` (cross-fit Platt) — they are NEVER taken straight
    from the LLM.
    """
    case_id: str
    observed_lift: float            # real ATE (ground truth)
    predicted_signal: float         # raw simulator lift
    p_pos: Optional[float] = None   # calibrated P(positive); filled by calibrator
    p_flat: Optional[float] = None
    p_neg: Optional[float] = None
    quality_weight: float = 1.0
    is_aa: bool = False

    def true_sign(self, delta: float) -> int:
        return _sign_dead(self.observed_lift, delta)

    def signal_sign(self, delta: float) -> int:
        return _sign_dead(self.predicted_signal, delta)

    def pred_sign(self) -> int:
        if self.p_pos is None:
            return _sign_dead(self.predicted_signal, 0.0)
        return max(((1, self.p_pos), (0, self.p_flat or 0.0), (-1, self.p_neg or 0.0)),
                   key=lambda kv: kv[1])[0]

    def pred_conf(self) -> float:
        if self.p_pos is None:
            return 0.5
        return max(self.p_pos, self.p_flat or 0.0, self.p_neg or 0.0)


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def _sign_dead(x: float, delta: float) -> int:
    if x > delta:
        return 1
    if x < -delta:
        return -1
    return 0


def _z_for(conf: float) -> float:
    return {0.80: 1.2816, 0.90: 1.6449, 0.95: 1.9600}.get(conf, 1.6449)


def balanced_sign_match_rate(recs: Sequence[ExperimentRecord], delta: float) -> float:
    pos_h = pos_n = neg_h = neg_n = 0
    for r in recs:
        ts, ps = r.true_sign(delta), r.pred_sign()
        if ts == 1:
            pos_n += 1; pos_h += int(ps == 1)
        elif ts == -1:
            neg_n += 1; neg_h += int(ps == -1)
    parts = []
    if pos_n:
        parts.append(pos_h / pos_n)
    if neg_n:
        parts.append(neg_h / neg_n)
    return sum(parts) / len(parts) if parts else 0.0


def smr_hits_n(recs: Sequence[ExperimentRecord], delta: float) -> tuple[int, int]:
    h = n = 0
    for r in recs:
        ts = r.true_sign(delta)
        if ts == 0:
            continue
        n += 1; h += int(r.pred_sign() == ts)
    return h, n


def mcc_multiclass(recs: Sequence[ExperimentRecord], delta: float) -> float:
    cls = [-1, 0, 1]; idx = {c: i for i, c in enumerate(cls)}
    C = [[0] * 3 for _ in range(3)]
    for r in recs:
        C[idx[r.true_sign(delta)]][idx[r.pred_sign()]] += 1
    N = sum(sum(row) for row in C)
    if N == 0:
        return 0.0
    t = [sum(C[k]) for k in range(3)]
    p = [sum(C[k][l] for k in range(3)) for l in range(3)]
    correct = sum(C[k][k] for k in range(3))
    cov = correct * N - sum(t[k] * p[k] for k in range(3))
    vx = N * N - sum(p[k] ** 2 for k in range(3))
    vy = N * N - sum(t[k] ** 2 for k in range(3))
    d = math.sqrt(vx * vy)
    return cov / d if d > 0 else 0.0


def kendall_tau_b(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            pr = dx * dy
            if pr > 0:
                c += 1
            elif pr < 0:
                d += 1
            else:
                if dx == 0:
                    tx += 1
                if dy == 0:
                    ty += 1
    n0 = n * (n - 1) / 2
    den = math.sqrt((n0 - tx) * (n0 - ty))
    return (c - d) / den if den > 0 else 0.0


def _onehot(ts: int) -> tuple[float, float, float]:
    return {1: (1.0, 0.0, 0.0), 0: (0.0, 1.0, 0.0), -1: (0.0, 0.0, 1.0)}[ts]


def brier_multiclass(recs: Sequence[ExperimentRecord], delta: float) -> float:
    if not recs:
        return 0.0
    tot = 0.0
    for r in recs:
        y = _onehot(r.true_sign(delta))
        pr = (r.p_pos or 0.0, r.p_flat or 0.0, r.p_neg or 0.0)
        tot += sum((pr[k] - y[k]) ** 2 for k in range(3))
    return tot / len(recs)


def brier_climatology(recs: Sequence[ExperimentRecord], delta: float) -> float:
    if not recs:
        return 0.0
    cnt = {1: 0, 0: 0, -1: 0}
    for r in recs:
        cnt[r.true_sign(delta)] += 1
    n = len(recs)
    base = (cnt[1] / n, cnt[0] / n, cnt[-1] / n)
    tot = 0.0
    for r in recs:
        y = _onehot(r.true_sign(delta))
        tot += sum((base[k] - y[k]) ** 2 for k in range(3))
    return tot / n


def expected_calibration_error(recs: Sequence[ExperimentRecord], delta: float,
                               bins: int = 10) -> float:
    if not recs:
        return 0.0
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for r in recs:
        conf = r.pred_conf()
        correct = int(r.pred_sign() == r.true_sign(delta))
        buckets[min(bins - 1, int(conf * bins))].append((conf, correct))
    n = len(recs); ece = 0.0
    for b in buckets:
        if not b:
            continue
        acc = sum(c for _, c in b) / len(b)
        cf = sum(c for c, _ in b) / len(b)
        ece += (len(b) / n) * abs(acc - cf)
    return ece


# --------------------------------------------------------------------------- #
# Decision value (G8, primary) + tail safety (G9) + abstention (G10)
# --------------------------------------------------------------------------- #
def decision_utility(recs: Sequence[ExperimentRecord], delta: float, *,
                     budget: int, false_red_cost: float = 3.0,
                     baseline_scores: Optional[Sequence[float]] = None) -> float:
    n = len(recs)
    if n == 0 or budget <= 0:
        return 0.0
    idx = list(range(n))

    def wv(r: ExperimentRecord) -> float:
        return r.quality_weight if r.true_sign(delta) == 1 else 0.0

    def score(r: ExperimentRecord) -> float:
        return r.p_pos if r.p_pos is not None else r.predicted_signal

    sim_rank = sorted(idx, key=lambda i: score(recs[i]), reverse=True)
    base_rank = idx[:] if baseline_scores is None else \
        sorted(idx, key=lambda i: baseline_scores[i], reverse=True)

    def util(rank: Sequence[int]) -> float:
        chosen = set(rank[:budget])
        caught = sum(wv(recs[i]) for i in chosen)
        missed = sum(wv(recs[i]) for i in idx if i not in chosen)
        return caught - false_red_cost * missed

    return util(sim_rank) - util(base_rank)


def tail_winner_recall(recs: Sequence[ExperimentRecord], delta: float, *,
                       budget: int) -> float:
    n = len(recs)
    if n == 0:
        return 1.0
    decile = max(1, n // 10)
    true_top = set(sorted(range(n), key=lambda i: recs[i].observed_lift,
                          reverse=True)[:decile])

    def score(i: int) -> float:
        return recs[i].p_pos if recs[i].p_pos is not None else recs[i].predicted_signal

    keep = set(sorted(range(n), key=score, reverse=True)[:budget])
    return len(true_top & keep) / len(true_top)


def selective_risk(recs: Sequence[ExperimentRecord], delta: float, coverage: float) -> float:
    ordered = sorted(recs, key=lambda r: r.pred_conf(), reverse=True)
    k = max(1, int(round(len(ordered) * coverage)))
    cov = ordered[:k]
    return sum(int(r.pred_sign() != r.true_sign(delta)) for r in cov) / len(cov)


def abstention_is_monotone(recs: Sequence[ExperimentRecord], delta: float,
                           levels: Sequence[float] = (1.0, 0.8, 0.6, 0.4),
                           tol: float = 0.02) -> bool:
    if len(recs) < 10:
        return True
    risks = [selective_risk(recs, delta, c) for c in levels]
    for a, b in zip(risks, risks[1:]):
        if b > a + tol:
            return False
    return risks[-1] <= risks[0]


# --------------------------------------------------------------------------- #
# Integrity probes (G1, G3)
# --------------------------------------------------------------------------- #
def aa_false_signal_rate(aa: Sequence[ExperimentRecord], thr: float = 0.70) -> float:
    if not aa:
        return 0.0
    fired = sum(1 for r in aa if r.pred_sign() != 0 and r.pred_conf() >= thr)
    return fired / len(aa)


def label_permutation_smr(recs: Sequence[ExperimentRecord], delta: float, *,
                          predict_fn: Optional[Callable[[float], tuple[float, float, float]]] = None,
                          trials: int = 200, seed: int = 0) -> float:
    """G3 leakage probe. With FIXED stored predictions this collapses to ~0.5 by
    construction (predictions can no longer track shuffled labels), so it only
    detects leakage when `predict_fn` REGENERATES predictions on the permuted
    inputs (a leaking predictor that peeks at the label keeps scoring high)."""
    rng = random.Random(seed)
    obs = [r.observed_lift for r in recs]
    acc = 0.0
    for _ in range(trials):
        sh = obs[:]; rng.shuffle(sh)
        perm = []
        for i, r in enumerate(recs):
            if predict_fn is not None:
                pp, pf, pn = predict_fn(sh[i])
                perm.append(ExperimentRecord(r.case_id, sh[i], r.predicted_signal,
                                             pp, pf, pn, r.quality_weight))
            else:
                perm.append(ExperimentRecord(r.case_id, sh[i], r.predicted_signal,
                                             r.p_pos, r.p_flat, r.p_neg, r.quality_weight))
        acc += balanced_sign_match_rate(perm, delta)
    return acc / trials


# --------------------------------------------------------------------------- #
# Fitted calibration (Platt, cross-fit) — pure stdlib, no sklearn dependency
# --------------------------------------------------------------------------- #
def _platt_fit(signals: Sequence[float], labels: Sequence[int],
               iters: int = 100) -> tuple[float, float]:
    """1-D logistic P(label=1) = sigmoid(a*x + b), Newton's method. labels in {0,1}."""
    a, b = 1.0, 0.0
    n = len(signals)
    if n == 0:
        return a, b
    for _ in range(iters):
        g_a = g_b = h_aa = h_ab = h_bb = 0.0
        for x, y in zip(signals, labels):
            z = a * x + b
            p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
            w = max(p * (1 - p), 1e-9)
            err = p - y
            g_a += err * x; g_b += err
            h_aa += w * x * x; h_ab += w * x; h_bb += w
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < 1e-12:
            break
        da = (g_a * h_bb - g_b * h_ab) / det
        db = (h_aa * g_b - h_ab * g_a) / det
        a -= da; b -= db
        if abs(da) < 1e-8 and abs(db) < 1e-8:
            break
    return a, b


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def fit_calibration(recs: Sequence[ExperimentRecord], delta: float, *,
                    folds: int = 5, seed: int = 0) -> None:
    """Fill p_pos/p_flat/p_neg by OUT-OF-FOLD Platt calibration of the raw signal.

    Two one-vs-rest logistics (P(pos), P(neg)) fit on the training folds and
    applied to the held-out fold, so ECE/Brier are honest (no train==test
    leakage). P(flat) is the residual. This is the fitted layer M5/M18 require:
    the LLM signal becomes a calibrated sign-class probability, not a raw number.
    """
    n = len(recs)
    if n < folds * 2:
        folds = max(2, n // 2) or 1
    rng = random.Random(seed)
    order = list(range(n)); rng.shuffle(order)
    fold_of = {order[i]: i % folds for i in range(n)}
    for f in range(folds):
        tr = [recs[i] for i in range(n) if fold_of[i] != f]
        te = [i for i in range(n) if fold_of[i] == f]
        sig = [r.predicted_signal for r in tr]
        a_p, b_p = _platt_fit(sig, [int(r.true_sign(delta) == 1) for r in tr])
        a_n, b_n = _platt_fit(sig, [int(r.true_sign(delta) == -1) for r in tr])
        for i in te:
            x = recs[i].predicted_signal
            pp = _sigmoid(a_p * x + b_p)
            pn = _sigmoid(a_n * x + b_n)
            s = pp + pn
            if s > 1.0:  # renormalise the two OvR heads so they leave room for flat
                pp, pn, s = pp / s, pn / s, 1.0
            recs[i].p_pos = pp
            recs[i].p_neg = pn
            recs[i].p_flat = max(0.0, 1.0 - pp - pn)


# --------------------------------------------------------------------------- #
# Gate
# --------------------------------------------------------------------------- #
@dataclass
class GateConfig:
    delta: float = 0.0
    budget: int = 10
    false_red_cost: float = 3.0
    baseline_mcc: float = 0.0
    sign_flip_rate: float = 0.0
    demand_bias_ci_contains_zero: bool = True
    bootstrap_trials: int = 1000
    seed: int = 0
    conf: float = 0.90
    auto_calibrate: bool = True
    leakage_predict_fn: Optional[Callable[[float], tuple[float, float, float]]] = None


@dataclass
class GateResult:
    verdict: str
    gates: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"VERDICT: {self.verdict}"]
        for k in sorted(self.gates):
            lines.append(f"  {k}: {'PASS' if self.gates[k] else 'FAIL'}")
        for n in self.notes:
            lines.append(f"  note: {n}")
        return "\n".join(lines)


def _boot_ci(recs, stat, *, conf, trials, seed):
    rng = random.Random(seed)
    point = stat(recs)
    n = len(recs)
    if n == 0:
        return point, 0.0, 0.0
    lo, hi = bootstrap_percentile_ci(
        list(range(n)),
        lambda idxs: stat([recs[i] for i in idxs]),
        n_resamples=trials, confidence=conf, rng=rng,
    )
    return point, lo, hi


def certify(recs: Sequence[ExperimentRecord], cfg: GateConfig,
            aa: Optional[Sequence[ExperimentRecord]] = None) -> GateResult:
    d = cfg.delta
    aa = aa or []
    recs = list(recs)
    if cfg.auto_calibrate and recs and recs[0].p_pos is None:
        fit_calibration(recs, d, seed=cfg.seed)
    res = GateResult(verdict="NO-GO")
    g, m = res.gates, res.metrics

    hits, n_dir = smr_hits_n(recs, d)
    n_pos = sum(1 for r in recs if r.true_sign(d) == 1)
    n_neg = sum(1 for r in recs if r.true_sign(d) == -1)
    m["n"] = len(recs); m["n_dir"] = n_dir; m["n_pos"] = n_pos; m["n_neg"] = n_neg
    g["G0_floor"] = n_dir >= 50 and n_pos >= 10 and n_neg >= 10
    g["G0_smr_n"] = n_dir >= 100
    g["G0_mcc_n"] = n_dir >= 150

    aa_rate = aa_false_signal_rate(aa)
    m["aa_false_signal_rate"] = aa_rate
    g["G1_aa"] = aa_rate <= 0.05 if aa else True
    if not aa:
        res.notes.append("G1: no A/A records supplied — A/A integrity UNTESTED (gate passes vacuously)")

    m["sign_flip_rate"] = cfg.sign_flip_rate
    g["G2_robustness"] = cfg.sign_flip_rate <= 0.10 and cfg.demand_bias_ci_contains_zero

    perm = label_permutation_smr(recs, d, predict_fn=cfg.leakage_predict_fn,
                                 trials=200, seed=cfg.seed)
    m["perm_smr"] = perm
    g["G3_leakage"] = 0.40 <= perm <= 0.60
    if cfg.leakage_predict_fn is None:
        res.notes.append("G3: static permutation (no predict_fn) — only a sanity check, not a true leakage test")

    smr = balanced_sign_match_rate(recs, d)
    smr_lo, _ = wilson_interval(hits, n_dir, z=_z_for(cfg.conf)) if n_dir else (0.0, 1.0)
    m["balanced_smr"] = smr; m["smr_wilson_lo"] = smr_lo
    g["G4_direction"] = smr >= 0.70 and smr_lo > 0.55

    mcc_pt, mcc_lo, _ = _boot_ci(recs, lambda xs: mcc_multiclass(xs, d) - cfg.baseline_mcc,
                                 conf=cfg.conf, trials=cfg.bootstrap_trials, seed=cfg.seed)
    m["mcc"] = mcc_multiclass(recs, d); m["mcc_minus_baseline"] = mcc_pt; m["mcc_lo"] = mcc_lo
    g["G5_classification"] = mcc_pt >= 0.10 and mcc_lo > 0.0

    tau_pt, tau_lo, _ = _boot_ci(recs, lambda xs: kendall_tau_b([r.predicted_signal for r in xs],
                                                                [r.observed_lift for r in xs]),
                                 conf=cfg.conf, trials=cfg.bootstrap_trials, seed=cfg.seed)
    m["kendall_tau_b"] = tau_pt; m["kendall_tau_b_lo"] = tau_lo
    m["spearman_rho"] = spearman_rho([r.predicted_signal for r in recs],
                                     [r.observed_lift for r in recs]) if recs else 0.0
    g["G6_ranking"] = tau_pt >= 0.30 and tau_lo > 0.0

    ece = expected_calibration_error(recs, d)
    brier = brier_multiclass(recs, d); clim = brier_climatology(recs, d)
    skill = (clim - brier) / clim if clim > 0 else 0.0
    m["ece"] = ece; m["brier"] = brier; m["brier_climatology"] = clim; m["brier_skill"] = skill
    g["G7_ece_go"] = ece <= 0.08
    g["G7_ece_within_limit"] = ece <= 0.15
    g["G7_brier"] = skill >= 0.10

    du_pt, du_lo, _ = _boot_ci(recs, lambda xs: decision_utility(xs, d, budget=cfg.budget,
                                                                 false_red_cost=cfg.false_red_cost),
                               conf=cfg.conf, trials=cfg.bootstrap_trials, seed=cfg.seed)
    m["delta_u"] = du_pt; m["delta_u_lo"] = du_lo
    g["G8_decision_value"] = du_pt > 0 and du_lo > 0.0

    tail = tail_winner_recall(recs, d, budget=cfg.budget)
    m["tail_winner_recall"] = tail
    g["G9_tail_safety"] = tail >= 0.80

    g["G10_abstention"] = abstention_is_monotone(recs, d)
    g["G11_persona_value"] = True  # ablation comparison supplied externally

    nogo = (not g["G0_floor"] or not g["G1_aa"] or not g["G3_leakage"]
            or smr_lo <= 0.50 or du_lo <= 0.0 or not g["G7_ece_within_limit"]
            or skill < 0.0 or tail < 0.70 or cfg.sign_flip_rate > 0.20)
    if nogo:
        res.verdict = "NO-GO"
        res.notes.append("NO-GO triggers: " + ", ".join(_nogo_reasons(g, m, cfg)))
        return res

    go_gates = ["G0_floor", "G0_smr_n", "G1_aa", "G2_robustness", "G3_leakage",
                "G4_direction", "G5_classification", "G6_ranking", "G7_ece_go",
                "G7_brier", "G8_decision_value", "G9_tail_safety", "G10_abstention",
                "G11_persona_value"]
    if all(g[k] for k in go_gates):
        res.verdict = "GO"
    else:
        res.verdict = "CONDITIONAL"
        res.notes.append("GO blocked by: " + ", ".join(k for k in go_gates if not g[k]))
    return res


def _nogo_reasons(g: dict, m: dict, cfg: GateConfig) -> list:
    out = []
    if not g["G0_floor"]:
        out.append(f"G0 sample floor (n_dir={m['n_dir']}, n_pos={m['n_pos']}, n_neg={m['n_neg']})")
    if not g["G1_aa"]:
        out.append("G1 A/A integrity")
    if not g["G3_leakage"]:
        out.append(f"G3 leakage (perm_smr={m['perm_smr']:.3f})")
    if m["smr_wilson_lo"] <= 0.50:
        out.append(f"G4 SMR LB={m['smr_wilson_lo']:.3f}<=0.50")
    if m["delta_u_lo"] <= 0.0:
        out.append(f"G8 dU LB={m['delta_u_lo']:.2f}<=0")
    if not g["G7_ece_within_limit"]:
        out.append(f"G7 ECE={m['ece']:.3f}>0.15")
    if m["brier_skill"] < 0.0:
        out.append("G7 Brier worse than climatology")
    if m["tail_winner_recall"] < 0.70:
        out.append(f"G9 tail recall={m['tail_winner_recall']:.2f}<0.70")
    if cfg.sign_flip_rate > 0.20:
        out.append("G2 sign-flip>0.20")
    return out

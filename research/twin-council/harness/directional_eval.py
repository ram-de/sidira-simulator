"""
directional_eval — the G0-G11 certification gate from the twin-council white paper.

Pure standard library (math, random, statistics). No third-party deps so it runs
anywhere, including CI. Implements the metrics and the GO / CONDITIONAL / NO-GO
verdict that gate whether a behavioral simulator may emit a numeric confidence
score.

Vocabulary (see WHITE-PAPER.md / MERGED-LEDGER.md):
  - effect:  the true observed ATE of a historical experiment (ground truth).
  - sign:    sign(effect) after a practical-null dead-band delta -> {-1, 0, +1}.
  - g:       the raw, uncalibrated simulator signal (never shown to a user).
  - p_pos:   calibrated probability the change is POSITIVE (what the gate scores).
  - conf:    calibrated reliability of the predicted sign class (the user-facing
             number, only emitted inside the validated regime).

Everything is computed over EXPERIMENTS, not over agents. Agent-level resampling
is Monte-Carlo error only and is intentionally not offered here (M15).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Experiment:
    """One historical experiment used as backtest ground truth."""
    id: str
    true_effect: float          # observed ATE (ground truth)
    g: float                    # raw simulator signal
    p_pos: float                # calibrated P(positive)
    p_flat: float               # calibrated P(flat)
    p_neg: float                # calibrated P(negative)
    quality_weight: float = 1.0  # G/M14: down-weight low-power / SRM-failed exps
    is_aa: bool = False         # True for A/A placebo records

    def true_sign(self, delta: float) -> int:
        return sign_with_deadband(self.true_effect, delta)

    def pred_sign(self) -> int:
        """Argmax of the calibrated class probabilities -> {-1,0,+1}."""
        probs = ((1, self.p_pos), (0, self.p_flat), (-1, self.p_neg))
        return max(probs, key=lambda kv: kv[1])[0]

    def pred_conf(self) -> float:
        return max(self.p_pos, self.p_flat, self.p_neg)


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def sign_with_deadband(x: float, delta: float) -> int:
    if x > delta:
        return 1
    if x < -delta:
        return -1
    return 0


def wilson_interval(k: int, n: int, conf: float = 0.90) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion. conf is two-sided mass."""
    if n == 0:
        return (0.0, 1.0)
    z = _z_for_conf(conf)
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _z_for_conf(conf: float) -> float:
    # two-sided z for common confidence levels; falls back to inverse-erf.
    table = {0.80: 1.2816, 0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}
    if conf in table:
        return table[conf]
    # inverse normal CDF via inverse error function approximation
    p = 1 - (1 - conf) / 2
    return math.sqrt(2) * _erfinv(2 * p - 1)


def _erfinv(x: float) -> float:
    # Winitzki approximation; good to ~1e-3, plenty for z-scores here.
    a = 0.147
    ln = math.log(1 - x * x)
    t = 2 / (math.pi * a) + ln / 2
    return math.copysign(math.sqrt(math.sqrt(t * t - ln / a) - t), x)


# --------------------------------------------------------------------------- #
# Directional metrics
# --------------------------------------------------------------------------- #
def balanced_sign_match_rate(exps: Sequence[Experiment], delta: float) -> float:
    """
    Balanced SMR over sign-decisive (non-flat) experiments: the unweighted mean
    of per-class accuracy on true-positives and true-negatives. Balancing defends
    against a skewed archive base rate (M-C13/C14).
    """
    pos_hits = pos_tot = neg_hits = neg_tot = 0
    for e in exps:
        ts = e.true_sign(delta)
        ps = e.pred_sign()
        if ts == 1:
            pos_tot += 1
            pos_hits += int(ps == 1)
        elif ts == -1:
            neg_tot += 1
            neg_hits += int(ps == -1)
    parts = []
    if pos_tot:
        parts.append(pos_hits / pos_tot)
    if neg_tot:
        parts.append(neg_hits / neg_tot)
    return sum(parts) / len(parts) if parts else 0.0


def _smr_hits_n(exps: Sequence[Experiment], delta: float) -> Tuple[int, int]:
    """Raw (hits, n) on sign-decisive experiments, for Wilson CI on the SMR gate."""
    hits = n = 0
    for e in exps:
        ts = e.true_sign(delta)
        if ts == 0:
            continue
        n += 1
        hits += int(e.pred_sign() == ts)
    return hits, n


def mcc_multiclass(exps: Sequence[Experiment], delta: float) -> float:
    """Gorodkin's R_K (multiclass MCC) over the 3 sign classes."""
    classes = [-1, 0, 1]
    idx = {c: i for i, c in enumerate(classes)}
    C = [[0] * 3 for _ in range(3)]
    for e in exps:
        C[idx[e.true_sign(delta)]][idx[e.pred_sign()]] += 1
    N = sum(sum(row) for row in C)
    if N == 0:
        return 0.0
    t = [sum(C[k][l] for l in range(3)) for k in range(3)]  # true totals per class
    p = [sum(C[k][l] for k in range(3)) for l in range(3)]  # pred totals per class
    correct = sum(C[k][k] for k in range(3))
    cov_xy = correct * N - sum(t[k] * p[k] for k in range(3))
    var_x = N * N - sum(p[k] * p[k] for k in range(3))
    var_y = N * N - sum(t[k] * t[k] for k in range(3))
    denom = math.sqrt(var_x * var_y)
    return cov_xy / denom if denom > 0 else 0.0


def kendall_tau_b(x: Sequence[float], y: Sequence[float]) -> float:
    """Kendall's tau-b (tie-corrected). O(n^2) — fine for backtest sizes."""
    n = len(x)
    if n < 2:
        return 0.0
    concordant = discordant = 0
    tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            prod = dx * dy
            if prod > 0:
                concordant += 1
            elif prod < 0:
                discordant += 1
            else:
                if dx == 0:
                    tx += 1
                if dy == 0:
                    ty += 1
    n0 = n * (n - 1) / 2
    denom = math.sqrt((n0 - tx) * (n0 - ty))
    return (concordant - discordant) / denom if denom > 0 else 0.0


def brier_multiclass(exps: Sequence[Experiment], delta: float) -> float:
    """Mean multiclass Brier score (lower is better)."""
    if not exps:
        return 0.0
    total = 0.0
    for e in exps:
        ts = e.true_sign(delta)
        y = {1: (1, 0, 0), 0: (0, 1, 0), -1: (0, 0, 1)}[ts]
        pr = (e.p_pos, e.p_flat, e.p_neg)
        total += sum((pr[k] - y[k]) ** 2 for k in range(3))
    return total / len(exps)


def brier_climatology(exps: Sequence[Experiment], delta: float) -> float:
    """Brier of the constant base-rate predictor (the honest null baseline)."""
    if not exps:
        return 0.0
    counts = {1: 0, 0: 0, -1: 0}
    for e in exps:
        counts[e.true_sign(delta)] += 1
    n = len(exps)
    base = (counts[1] / n, counts[0] / n, counts[-1] / n)
    total = 0.0
    for e in exps:
        ts = e.true_sign(delta)
        y = {1: (1, 0, 0), 0: (0, 1, 0), -1: (0, 0, 1)}[ts]
        total += sum((base[k] - y[k]) ** 2 for k in range(3))
    return total / n


def expected_calibration_error(exps: Sequence[Experiment], delta: float,
                               bins: int = 10) -> float:
    """ECE on the predicted-sign-class confidence vs. its empirical accuracy."""
    if not exps:
        return 0.0
    buckets: List[List[Tuple[float, int]]] = [[] for _ in range(bins)]
    for e in exps:
        conf = e.pred_conf()
        correct = int(e.pred_sign() == e.true_sign(delta))
        b = min(bins - 1, int(conf * bins))
        buckets[b].append((conf, correct))
    n = len(exps)
    ece = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        acc = sum(c for _, c in bucket) / len(bucket)
        avg_conf = sum(cf for cf, _ in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(acc - avg_conf)
    return ece


# --------------------------------------------------------------------------- #
# Decision value (the PRIMARY criterion, G8)
# --------------------------------------------------------------------------- #
def decision_utility(exps: Sequence[Experiment], delta: float, *,
                     budget: int,
                     false_red_cost: float = 3.0,
                     baseline_scores: Optional[Sequence[float]] = None
                     ) -> float:
    """
    Delta-U = U(pi_sim) - U(pi_0) under a scarce experiment-slot budget.

    pi_sim ranks the backlog by calibrated P(positive) and spends `budget` slots
    on the top items. pi_0 (status quo) ranks by `baseline_scores` (default: the
    PM's order as given, i.e. the input order).

    Utility of shipping a true winner = +1 (weighted); the asymmetric cost of a
    *missed* winner (false-red: a true winner NOT selected) is `false_red_cost`,
    encoding that unobservable missed winners are the dangerous error (M16).
    """
    n = len(exps)
    if n == 0 or budget <= 0:
        return 0.0
    idx = list(range(n))

    def winner_value(e: Experiment) -> float:
        return e.quality_weight if e.true_sign(delta) == 1 else 0.0

    sim_rank = sorted(idx, key=lambda i: exps[i].p_pos, reverse=True)
    if baseline_scores is None:
        base_rank = idx[:]  # PM's given order
    else:
        base_rank = sorted(idx, key=lambda i: baseline_scores[i], reverse=True)

    def utility(rank: Sequence[int]) -> float:
        chosen = set(rank[:budget])
        caught = sum(winner_value(exps[i]) for i in chosen)
        missed = sum(winner_value(exps[i]) for i in idx if i not in chosen)
        return caught - false_red_cost * missed

    return utility(sim_rank) - utility(base_rank)


def tail_winner_recall(exps: Sequence[Experiment], delta: float, *,
                       budget: int) -> float:
    """
    Among the TRUE top-decile winners (by true_effect), what fraction does the
    simulator keep above its deprioritization cutoff (the top-`budget` by p_pos)?
    G9: must be >= 0.80 before any auto-deprioritization is allowed.
    """
    n = len(exps)
    if n == 0:
        return 1.0
    decile = max(1, n // 10)
    true_top = set(sorted(range(n), key=lambda i: exps[i].true_effect,
                          reverse=True)[:decile])
    sim_keep = set(sorted(range(n), key=lambda i: exps[i].p_pos,
                          reverse=True)[:budget])
    kept = len(true_top & sim_keep)
    return kept / len(true_top)


# --------------------------------------------------------------------------- #
# Integrity tests
# --------------------------------------------------------------------------- #
def aa_false_signal_rate(aa_exps: Sequence[Experiment],
                         action_threshold: float = 0.70) -> float:
    """G1: fraction of A/A placebo records that produce an actionable
    (pos or neg) call at confidence >= threshold. Must be <= 0.05."""
    if not aa_exps:
        return 0.0
    fired = 0
    for e in aa_exps:
        ps = e.pred_sign()
        if ps != 0 and e.pred_conf() >= action_threshold:
            fired += 1
    return fired / len(aa_exps)


def label_permutation_smr(exps: Sequence[Experiment], delta: float, *,
                          predict_fn: "Optional[Callable[[float], Tuple[float, float, float]]]" = None,
                          trials: int = 200, seed: int = 0) -> float:
    """
    G3 leakage probe: shuffle the true effects across experiments and recompute
    balanced SMR. A non-leaking simulator collapses to ~0.5.

    IMPORTANT: with FIXED stored predictions this trivially collapses to ~0.5
    (predictions can no longer track the shuffled labels), so it only proves
    leakage when predictions are REGENERATED on the permuted inputs. Pass
    `predict_fn(effect) -> (p_pos, p_flat, p_neg)` to do that: a leaking
    predictor (one that peeks at the true effect/label) will keep scoring high
    under permutation and be caught; a clean predictor collapses to ~0.5.

    Returns the mean permuted balanced SMR.
    """
    rng = random.Random(seed)
    effects = [e.true_effect for e in exps]
    acc = 0.0
    for _ in range(trials):
        shuffled = effects[:]
        rng.shuffle(shuffled)
        permuted = []
        for i, e in enumerate(exps):
            if predict_fn is not None:
                pp, pf, pn = predict_fn(shuffled[i])
            else:
                pp, pf, pn = e.p_pos, e.p_flat, e.p_neg
            permuted.append(Experiment(e.id, shuffled[i], e.g, pp, pf, pn,
                                       e.quality_weight, e.is_aa))
        acc += balanced_sign_match_rate(permuted, delta)
    return acc / trials


def selective_risk(exps: Sequence[Experiment], delta: float,
                   coverage: float) -> float:
    """Error rate on the most-confident `coverage` fraction of predictions."""
    ordered = sorted(exps, key=lambda e: e.pred_conf(), reverse=True)
    k = max(1, int(round(len(ordered) * coverage)))
    cov = ordered[:k]
    return sum(int(e.pred_sign() != e.true_sign(delta)) for e in cov) / len(cov)


def abstention_is_monotone(exps: Sequence[Experiment], delta: float,
                           levels: Sequence[float] = (1.0, 0.8, 0.6, 0.4),
                           tol: float = 0.02) -> bool:
    """
    G10: risk must fall as we narrow coverage to the most confident predictions
    (selective prediction works). Checks the risk-coverage curve is non-increasing
    as coverage tightens, within tolerance `tol` to absorb finite-sample wiggle,
    and that the tightest level has strictly lower risk than full coverage. The
    extreme tail (<40% coverage) is left out because it is too noisy to gate on at
    backtest sample sizes (M15).
    """
    if len(exps) < 10:
        return True
    risks = [selective_risk(exps, delta, c) for c in levels]  # full -> tight
    for a, b in zip(risks, risks[1:]):
        if b > a + tol:           # risk went UP as coverage tightened
            return False
    return risks[-1] <= risks[0]  # tightest must beat full coverage


# --------------------------------------------------------------------------- #
# Bootstrap CI over experiments (M15)
# --------------------------------------------------------------------------- #
def bootstrap_ci(exps: Sequence[Experiment],
                 stat: Callable[[Sequence[Experiment]], float], *,
                 conf: float = 0.90, trials: int = 1000, seed: int = 0
                 ) -> Tuple[float, float, float]:
    """Returns (point, lo, hi) for `stat` via paired bootstrap over experiments."""
    rng = random.Random(seed)
    n = len(exps)
    point = stat(exps)
    if n == 0:
        return (point, 0.0, 0.0)
    samples = []
    for _ in range(trials):
        resample = [exps[rng.randrange(n)] for _ in range(n)]
        samples.append(stat(resample))
    samples.sort()
    alpha = (1 - conf) / 2
    lo = samples[int(alpha * trials)]
    hi = samples[min(trials - 1, int((1 - alpha) * trials))]
    return (point, lo, hi)


# --------------------------------------------------------------------------- #
# The gate
# --------------------------------------------------------------------------- #
@dataclass
class GateConfig:
    delta: float = 0.0
    budget: int = 10
    false_red_cost: float = 3.0
    baseline_mcc: float = 0.0      # best non-LLM baseline MCC (G5)
    sign_flip_rate: float = 0.0    # measured robustness input (G2)
    demand_bias_ci_contains_zero: bool = True  # (G2)
    bootstrap_trials: int = 1000
    seed: int = 0
    # Optional: regenerate predictions on permuted labels so G3 actually detects
    # leakage (see label_permutation_smr). None -> static (weak) check.
    leakage_predict_fn: "Optional[Callable[[float], Tuple[float, float, float]]]" = None


@dataclass
class GateResult:
    verdict: str                       # "GO" | "CONDITIONAL" | "NO-GO"
    gates: Dict[str, bool] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"VERDICT: {self.verdict}"]
        for k in sorted(self.gates):
            lines.append(f"  {k}: {'PASS' if self.gates[k] else 'FAIL'}")
        for n in self.notes:
            lines.append(f"  note: {n}")
        return "\n".join(lines)


def certify(exps: Sequence[Experiment],
            aa_exps: Sequence[Experiment],
            cfg: GateConfig) -> GateResult:
    """Run the full G0-G11 gate and return GO / CONDITIONAL / NO-GO."""
    d = cfg.delta
    res = GateResult(verdict="NO-GO")
    g = res.gates
    m = res.metrics

    # G0 sample sufficiency
    hits, n_dir = _smr_hits_n(exps, d)
    n_pos = sum(1 for e in exps if e.true_sign(d) == 1)
    n_neg = sum(1 for e in exps if e.true_sign(d) == -1)
    m["n_dir"] = n_dir
    g["G0_floor"] = n_dir >= 50 and n_pos >= 10 and n_neg >= 10
    g["G0_smr_n"] = n_dir >= 100
    g["G0_mcc_n"] = n_dir >= 150

    # G1 A/A null integrity
    aa_rate = aa_false_signal_rate(aa_exps)
    m["aa_false_signal_rate"] = aa_rate
    g["G1_aa"] = aa_rate <= 0.05

    # G2 robustness
    m["sign_flip_rate"] = cfg.sign_flip_rate
    g["G2_robustness"] = cfg.sign_flip_rate <= 0.10 and cfg.demand_bias_ci_contains_zero

    # G3 leakage
    perm = label_permutation_smr(exps, d, predict_fn=cfg.leakage_predict_fn,
                                 trials=200, seed=cfg.seed)
    m["perm_smr"] = perm
    g["G3_leakage"] = 0.40 <= perm <= 0.60

    # G4 direction (balanced SMR + Wilson LB on the raw rate)
    smr = balanced_sign_match_rate(exps, d)
    smr_lo, _ = wilson_interval(hits, n_dir, 0.90)
    m["balanced_smr"] = smr
    m["smr_wilson_lo90"] = smr_lo
    g["G4_direction"] = smr >= 0.70 and smr_lo > 0.55

    # G5 classification (MCC beats baseline by >= 0.10, bootstrap LB > 0)
    mcc_point, mcc_lo, _ = bootstrap_ci(
        exps, lambda xs: mcc_multiclass(xs, d) - cfg.baseline_mcc,
        conf=0.90, trials=cfg.bootstrap_trials, seed=cfg.seed)
    m["mcc"] = mcc_multiclass(exps, d)
    m["mcc_minus_baseline"] = mcc_point
    m["mcc_minus_baseline_lo90"] = mcc_lo
    g["G5_classification"] = mcc_point >= 0.10 and mcc_lo > 0.0

    # G6 ranking (Kendall tau_b, bootstrap LB > 0)
    def tau_stat(xs: Sequence[Experiment]) -> float:
        return kendall_tau_b([e.g for e in xs], [e.true_effect for e in xs])
    tau_point, tau_lo, _ = bootstrap_ci(exps, tau_stat, conf=0.90,
                                        trials=cfg.bootstrap_trials, seed=cfg.seed)
    m["kendall_tau_b"] = tau_point
    m["kendall_tau_b_lo90"] = tau_lo
    g["G6_ranking"] = tau_point >= 0.30 and tau_lo > 0.0

    # G7 calibration (ECE band + Brier skill over climatology)
    ece = expected_calibration_error(exps, d)
    brier = brier_multiclass(exps, d)
    clim = brier_climatology(exps, d)
    brier_skill = (clim - brier) / clim if clim > 0 else 0.0
    m["ece"] = ece
    m["brier"] = brier
    m["brier_climatology"] = clim
    m["brier_skill"] = brier_skill
    g["G7_ece_go"] = ece <= 0.08             # GO band
    g["G7_ece_within_limit"] = ece <= 0.15   # PASS unless in NO-GO territory
    g["G7_brier"] = brier_skill >= 0.10

    # G8 decision value (PRIMARY), bootstrap LB > 0
    def du_stat(xs: Sequence[Experiment]) -> float:
        return decision_utility(xs, d, budget=cfg.budget,
                                false_red_cost=cfg.false_red_cost)
    du_point, du_lo, _ = bootstrap_ci(exps, du_stat, conf=0.90,
                                      trials=cfg.bootstrap_trials, seed=cfg.seed)
    m["delta_u"] = du_point
    m["delta_u_lo90"] = du_lo
    g["G8_decision_value"] = du_point > 0 and du_lo > 0.0

    # G9 tail safety
    tail = tail_winner_recall(exps, d, budget=cfg.budget)
    m["tail_winner_recall"] = tail
    g["G9_tail_safety"] = tail >= 0.80

    # G10 abstention quality
    g["G10_abstention"] = abstention_is_monotone(exps, d)

    # G11 persona value is an ablation comparison; supplied externally.
    # Default True so it does not silently block when not measured here.
    g["G11_persona_value"] = True

    # ---- verdict logic ----
    nogo = (
        not g["G0_floor"]
        or not g["G1_aa"]
        or not g["G3_leakage"]
        or smr_lo <= 0.50
        or du_lo <= 0.0
        or not g["G7_ece_within_limit"]
        or brier_skill < 0.0
        or (tail < 0.70)
        or cfg.sign_flip_rate > 0.20
    )
    if nogo:
        res.verdict = "NO-GO"
        return res

    go_gates = [
        "G0_floor", "G0_smr_n", "G1_aa", "G2_robustness", "G3_leakage",
        "G4_direction", "G5_classification", "G6_ranking", "G7_ece_go",
        "G7_brier", "G8_decision_value", "G9_tail_safety", "G10_abstention",
        "G11_persona_value",
    ]
    if all(g[k] for k in go_gates):
        res.verdict = "GO"
    else:
        res.verdict = "CONDITIONAL"
        failed = [k for k in go_gates if not g[k]]
        res.notes.append("GO blocked by: " + ", ".join(failed))
    return res

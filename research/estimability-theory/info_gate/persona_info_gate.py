"""
Persona information-sufficiency gate (Gate 1 of the router).

Answers, BEFORE any simulation: does a persona pack encode the variable a
hypothesis's mechanism turns on? Three layers, cheap -> rigorous:

  L0 presence        - the mechanism feature(s) exist in the pack schema
  L1 variance        - they are non-degenerate across the population
  L2 discriminability - a flexible model recovers a PRE-TEST behavioral proxy
                        from them, beating a permutation null (the information
                        floor; blind to the A/B outcome by construction)

PASS = L0 & L1 & L2. Passing is NECESSARY, not sufficient: it removes the
information-impossible cases; it does NOT promise the engine predicts the
direction correctly (that is the in-distribution accuracy test's job).

The gate never sees the A/B outcome. L2 scores the mechanism feature(s) against a
PRE-TEST behavioral proxy (e.g. historical browse-abandon rate for "overload"),
so the partition it produces is outcome-blind by construction.

Pre-reg: research/estimability-theory/PREREG_INDISTRIBUTION_GATE_DRAFT.md
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.model_selection import KFold, StratifiedKFold, permutation_test_score

EPS = 1e-9


@dataclass(frozen=True)
class GateConfig:
    """Frozen thresholds. At seal time these are fixed WITH the partner's real
    feature distributions and never tuned post-hoc (see the pre-reg)."""
    spread_floor: float = 0.02      # L1 numeric: std/(max-min) must exceed this
    entropy_floor: float = 0.10     # L1 categorical: normalized entropy must exceed
    min_distinct: int = 2           # L1: at least this many distinct values
    l2_alpha: float = 0.05          # L2: permutation p-value must be <= this
    l2_margin: float = 0.02         # L2: (score - null_mean) must exceed this
    n_permutations: int = 200
    cv_folds: int = 3
    random_state: int = 12345
    n_jobs: int = -1


@dataclass
class HypothesisSpec:
    id: str
    change: str                      # the A/B change being predicted
    mechanism: str                   # the causal story ("reduces choice overload")
    mechanism_features: list[str]    # persona features the mechanism implicates
    proxy: str                       # PRE-TEST behavioral proxy column (NOT the outcome)
    proxy_kind: str = "auto"         # "binary" | "continuous" | "auto"


@dataclass
class GateResult:
    hypothesis_id: str
    passed: bool
    tier_failed: Optional[str]       # "L0" | "L1" | "L2" | None
    reason: str
    presence: dict                   # feature -> bool  (L0)
    variance: dict                   # feature -> {ok, measure, note}  (L1)
    usable_features: list            # features that cleared L0 & L1
    l2: dict                         # L2 detail (score / null_mean / pvalue / passed)
    config: dict

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# L1 — non-degeneracy
# --------------------------------------------------------------------------- #
def _l1_check(s: pd.Series, cfg: GateConfig) -> tuple[bool, float, str]:
    s = s.dropna()
    distinct = int(s.nunique())
    if distinct < cfg.min_distinct:
        return False, 0.0, f"degenerate (distinct={distinct})"
    if pd.api.types.is_numeric_dtype(s):
        rng = float(s.max() - s.min())
        spread = float(s.std() / (rng + EPS)) if rng > 0 else 0.0
        return spread >= cfg.spread_floor, spread, f"numeric spread={spread:.3f}"
    vc = s.value_counts(normalize=True).to_numpy()
    ent = float(-(vc * np.log(vc + EPS)).sum())
    norm_ent = ent / (np.log(len(vc)) + EPS) if len(vc) > 1 else 0.0
    return norm_ent >= cfg.entropy_floor, norm_ent, f"categorical norm_entropy={norm_ent:.3f}"


# --------------------------------------------------------------------------- #
# L2 — discriminability (the information floor)
# --------------------------------------------------------------------------- #
def _infer_kind(y: pd.Series, declared: str) -> str:
    if declared in ("binary", "continuous"):
        return declared
    return "binary" if y.dropna().nunique() <= 2 else "continuous"


def _prep_y(y: pd.Series, kind: str) -> np.ndarray:
    if kind == "binary":
        codes, uniques = pd.factorize(y)
        if len(uniques) == 2:
            return codes.astype(int)              # {0,1}
        top = y.mode().iloc[0]                     # >2 values: top-class vs rest
        return (y == top).astype(int).to_numpy()
    return y.astype(float).to_numpy()


def _l2_discriminability(X: pd.DataFrame, y: pd.Series, kind: str, cfg: GateConfig) -> dict:
    mask = y.notna()
    X, y = X.loc[mask], y.loc[mask]
    X_enc = pd.get_dummies(X, dummy_na=False)
    if X_enc.shape[1] == 0 or len(y) < cfg.cv_folds * 3:
        return dict(score=float("nan"), null_mean=float("nan"), pvalue=1.0,
                    passed=False, note="insufficient rows/features for L2")
    y_enc = _prep_y(y, kind)
    rng = cfg.random_state
    if kind == "binary":
        if len(np.unique(y_enc)) < 2:
            return dict(score=float("nan"), null_mean=float("nan"), pvalue=1.0,
                        passed=False, note="proxy single-class after prep")
        model = HistGradientBoostingClassifier(random_state=rng)
        cv = StratifiedKFold(cfg.cv_folds, shuffle=True, random_state=rng)
        scoring, baseline = "roc_auc", 0.5
    else:
        model = HistGradientBoostingRegressor(random_state=rng)
        cv = KFold(cfg.cv_folds, shuffle=True, random_state=rng)
        scoring, baseline = "r2", 0.0
    score, perm, pvalue = permutation_test_score(
        model, X_enc.to_numpy(), y_enc, scoring=scoring, cv=cv,
        n_permutations=cfg.n_permutations, random_state=rng, n_jobs=cfg.n_jobs)
    null_mean = float(np.mean(perm))
    passed = bool((pvalue <= cfg.l2_alpha) and ((score - null_mean) >= cfg.l2_margin))
    return dict(score=float(score), null_mean=null_mean, pvalue=float(pvalue),
                baseline=baseline, scoring=scoring, passed=passed)


# --------------------------------------------------------------------------- #
# The gate
# --------------------------------------------------------------------------- #
def evaluate(pack: pd.DataFrame, h: HypothesisSpec, cfg: GateConfig = GateConfig()) -> GateResult:
    cfgd = asdict(cfg)

    # L0 — presence
    presence = {f: (f in pack.columns) for f in h.mechanism_features}
    present = [f for f, ok in presence.items() if ok]
    if not present:
        return GateResult(h.id, False, "L0",
                          f"no mechanism feature present in pack: {h.mechanism_features}",
                          presence, {}, [], {}, cfgd)

    # L1 — non-degeneracy
    variance, usable = {}, []
    for f in present:
        ok, measure, note = _l1_check(pack[f], cfg)
        variance[f] = dict(ok=ok, measure=measure, note=note)
        if ok:
            usable.append(f)
    if not usable:
        return GateResult(h.id, False, "L1",
                          "mechanism feature(s) present but degenerate (no usable variance)",
                          presence, variance, [], {}, cfgd)

    # L2 — discriminability vs the pre-test proxy
    if h.proxy not in pack.columns:
        return GateResult(h.id, False, "L2",
                          f"pre-test proxy '{h.proxy}' absent — cannot test the information floor",
                          presence, variance, usable, {}, cfgd)
    kind = _infer_kind(pack[h.proxy], h.proxy_kind)
    l2 = _l2_discriminability(pack[usable], pack[h.proxy], kind, cfg)
    if not l2.get("passed"):
        s, nm, p = l2.get("score"), l2.get("null_mean"), l2.get("pvalue")
        return GateResult(h.id, False, "L2",
                          f"present & varying but NOT discriminative for proxy "
                          f"(score={s:.3f} vs null={nm:.3f}, p={p:.3f})",
                          presence, variance, usable, l2, cfgd)

    return GateResult(h.id, True, None,
                      f"SUFFICIENT: {usable} recover proxy '{h.proxy}' "
                      f"(score={l2['score']:.3f} vs null {l2['null_mean']:.3f}, p={l2['pvalue']:.3f})",
                      presence, variance, usable, l2, cfgd)


def partition(cases: list[tuple[pd.DataFrame, HypothesisSpec]],
              cfg: GateConfig = GateConfig()) -> list[GateResult]:
    """Run the gate over (pack, hypothesis) cases -> the pre-committed PASS/FAIL
    partition the in-distribution experiment scores against."""
    return [evaluate(pack, h, cfg) for pack, h in cases]

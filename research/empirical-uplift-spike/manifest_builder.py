"""
manifest_builder.py — the build-time precompute core (router's heavy lift).

Runs at persona-pack build (in sidira-persona-worker, per the architecture decision).
Joins what the worker already has — feature-store ColumnProfiles + the crawler's
Capabilities — into `estimability_manifest.json`, shipped beside persona_pack.json in R2.
At hypothesis runtime the router just MATCHES + RETRIEVES from this; no Snowflake re-query,
no model refit for the common case.

This module is REPO-AGNOSTIC on purpose (mirrors causal_estimator.py): it takes plain
dicts + a `load_frame` callable, so the worker supplies real ColumnProfiles / Capabilities
/ a Snowflake query fn, and tests supply fixtures. The capability->column linkage here is
rule-based (token overlap); in prod it's the LLM-as-translator MAP step — same output shape.

No hard dependency on the product. Deps: numpy, pandas, scikit-learn (via causal_estimator).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Callable
import re
import pandas as pd

from causal_estimator import support_check, estimate

OUTCOME_HINTS = ("order", "retention", "retain", "convert", "conversion", "visit", "spend",
                 "revenue", "churn", "engage", "active", "purchase", "signup", "subscribe")
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_TOKEN.findall(s.lower()))


@dataclass
class ColumnEntry:
    name: str
    dtype: str
    role: str                      # treatment_candidate | outcome_candidate | covariate
    distinct_count: int | None
    null_fraction: float
    has_variation: bool


@dataclass
class CapabilityLink:
    capability_name: str
    surfaces: list[str]
    treatment_column: str | None   # None -> not represented in the data -> LLM route
    linked: bool


@dataclass
class CandidateEffect:
    treatment: str
    outcome: str
    covariates: list[str]
    supportable: bool
    support_reasons: list[str]
    n_treat: int
    n_control: int
    naive_ate: float | None
    t_learner_ate: float | None
    ipw_ate: float | None
    overlap_fraction: float | None
    naive_adjusted_gap: float | None
    sign_adjusted: str | None


@dataclass
class Manifest:
    manifest_version: str
    customer_id: str
    setup_id: str
    pack_version: str
    feature_store: str
    columns: list[ColumnEntry] = field(default_factory=list)
    capability_links: list[CapabilityLink] = field(default_factory=list)
    candidate_effects: list[CandidateEffect] = field(default_factory=list)
    built_at: str | None = None    # stamped by the caller (worker), kept out for determinism


def _classify(profiles: list[dict]) -> list[ColumnEntry]:
    """Tag outcomes vs covariates. Treatment status is decided later, by LINKAGE — a
    covariate must never be demoted just because its name overlaps a capability term."""
    out = []
    for p in profiles:
        name, dc = p["name"], p.get("distinct_count")
        role = "outcome_candidate" if (_tokens(name) & set(OUTCOME_HINTS)) else "covariate"
        out.append(ColumnEntry(name=name, dtype=p.get("dtype", "unknown"), role=role,
                               distinct_count=dc, null_fraction=float(p.get("null_fraction", 0.0)),
                               has_variation=(dc is None or dc >= 2)))
    return out


def _link(capabilities: list[dict], cols: list[ColumnEntry]) -> list[CapabilityLink]:
    # eligible treatment columns = non-outcome, low-cardinality, varying (a lever, not a metric)
    treat_cols = [c for c in cols if c.role != "outcome_candidate" and c.has_variation
                  and c.distinct_count is not None and c.distinct_count <= 10]
    links = []
    for cap in capabilities:
        ctoks = _tokens(cap["capability_name"])
        best, best_score = None, 0
        for c in treat_cols:
            score = len(_tokens(c.name) & ctoks)
            if score > best_score:
                best, best_score = c.name, score
        links.append(CapabilityLink(capability_name=cap["capability_name"],
                                     surfaces=list(cap.get("surfaces", [])),
                                     treatment_column=best, linked=best is not None))
    return links


def build_manifest(customer_id: str, setup_id: str, pack_version: str, feature_store: str,
                   column_profiles: list[dict], capabilities: list[dict],
                   load_frame: Callable[[list[str]], pd.DataFrame]) -> Manifest:
    """Join columns x capabilities and PRE-FIT the candidate (T->Y) effect grid."""
    cols = _classify(column_profiles)
    links = _link(capabilities, cols)
    treatments = sorted({lk.treatment_column for lk in links if lk.treatment_column})

    # promote linked columns to treatment_candidate in the catalog (after linkage, not before)
    for c in cols:
        if c.name in treatments:
            c.role = "treatment_candidate"

    outcomes = [c.name for c in cols if c.role == "outcome_candidate" and c.has_variation]
    covars = [c.name for c in cols if c.role == "covariate" and c.has_variation
              and c.dtype not in ("string", "text")]

    effects: list[CandidateEffect] = []
    for T in treatments:
        X = [c for c in covars if c != T]
        for Y in outcomes:
            df = load_frame([T, Y, *X])                 # the ONE feature-store query, at build time
            sup = support_check(df, T, Y, X)
            if not sup.supportable:
                effects.append(CandidateEffect(T, Y, X, False, sup.reasons, sup.n_treat,
                                               sup.n_control, None, None, None, None, None, None))
                continue
            est = estimate(df, T, Y, X)
            effects.append(CandidateEffect(T, Y, X, True, [], sup.n_treat, sup.n_control,
                                           est.naive_ate, est.t_learner_ate, est.ipw_ate,
                                           est.overlap_fraction, est.naive_adjusted_gap,
                                           est.sign_adjusted))
    return Manifest("1.0", customer_id, setup_id, pack_version, feature_store, cols, links, effects)


# --------------------------------------------------------------------------- #
# Self-test: build a manifest end-to-end against Hillstrom as a stand-in store
# --------------------------------------------------------------------------- #
def _selftest():
    import json
    import numpy as np
    from pathlib import Path
    hs = Path(__file__).resolve().parent / ".data" / "hillstrom.csv"
    if not hs.exists():
        print("(.data/hillstrom.csv absent — run realdata_hillstrom.py once to cache it)")
        return
    raw = pd.read_csv(hs)
    raw = raw[raw["segment"].isin(["Womens E-Mail", "No E-Mail"])].copy()
    store = pd.DataFrame({
        "womens_email": (raw["segment"] == "Womens E-Mail").astype(int),   # treatment lever
        "visit": raw["visit"].astype(float), "conversion": raw["conversion"].astype(float),
        "recency": raw["recency"].astype(float), "loghist": np.log1p(raw["history"]),
        "mens": raw["mens"].astype(float), "womens": raw["womens"].astype(float),
        "newbie": raw["newbie"].astype(float),
    })
    profiles = [{"name": c, "dtype": "number", "distinct_count": int(store[c].nunique()),
                 "null_fraction": 0.0} for c in store.columns]
    capabilities = [{"capability_name": "Womens email campaign", "surfaces": ["email"]},
                    {"capability_name": "Live group-order video feed", "surfaces": ["home"]}]  # novel -> unlinked

    m = build_manifest("acme", "default", "v_1", "fixture://hillstrom",
                       profiles, capabilities, load_frame=lambda cols: store[cols])
    print("roles:", {c.name: c.role for c in m.columns})
    for lk in m.capability_links:
        print(f"link: {lk.capability_name!r:32} -> {lk.treatment_column}  (linked={lk.linked})")
    for e in m.candidate_effects:
        print(f"effect: {e.treatment} -> {e.outcome:11} supportable={e.supportable} "
              f"t_learner={None if e.t_learner_ate is None else round(e.t_learner_ate*100,2)}pp "
              f"sign={e.sign_adjusted}")
    out = Path(__file__).resolve().parent / "estimability_manifest_example.json"
    out.write_text(json.dumps(asdict(m), indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    _selftest()

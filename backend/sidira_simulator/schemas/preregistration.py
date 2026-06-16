"""Pre-registration artifact (ablation-protocol §5).

§5, "Pre-registration (do this before running)": *write down, hash-commit, and
only then run.* This locks in the experiment design BEFORE any data or run is
seen, so the results can't be retrofitted or the analysis silently forked. It is
the integrity counterpart to the §4 null-integrity certificate — applied inward
to our own build decisions (which §1/§2/§3 upgrades earn their place) the same
way the analysis demands it of the buyer backtest (Tier 1).

These schemas are the TYPED, machine-checkable form of the three §5 commitments
plus the run config the eventual run must be bound to:

1. `PreRegistration.primary_endpoint` — the named metric on the named datasets.
2. `PreRegistration.predicted_identity_depth_ordering` and
   `predicted_value_ladder_ordering` — the §3 orderings, stored as ORDERED lists
   so a later analysis can score the realized ordering against the pre-registered
   one (e.g. rank correlation between predicted and observed component order).
3. `PreRegistration.decision_rules` — one `ComponentDecisionRule` per component,
   the §3/§4 build/cut rule captured as structured fields (not prose) so the
   eventual analysis can check it mechanically.
4. `PreRegistration.run_config` — seed, permutation/bootstrap counts, the
   intended datasets, the held-out split policy (§7 Q1), and any explicit
   BLOCKERS, so the artifact is HONEST that it is pre-data / pre-run.
5. `PreRegistration.integrity_hash` — the SHA-256 hash-commit over the canonical
   serialization of everything above (computed by
   `services.benchmark_preregistration`). Any post-hoc edit to a committed field
   moves the hash, so `verify()` catches the tamper.

The hashing/verification logic lives in `services.benchmark_preregistration`;
this module is JUST the typed shape. Frozen where appropriate so a committed
artifact is immutable in-process (a real edit must go through `from_json`, which
re-exposes it to `verify`).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SplitPolicy(str, Enum):
    """Held-out split policy per dataset (ablation-protocol §7 Q1).

    LOO (leave-one-experiment-out) on the small sets (Upworthy, Hillstrom) for
    max data; a FIXED train/test split on Criteo's 13M rows for cost. Committing
    this up front stops a later run from picking whichever split flatters the
    result.
    """

    LEAVE_ONE_OUT = "leave_one_out"
    FIXED_SPLIT = "fixed_split"


class DatasetPlan(BaseModel):
    """One intended dataset + its committed split policy + presence honesty.

    `present` is the honest pre-data flag: at pre-registration time the datasets
    are typically NOT yet imported, so `present=False` is the norm and is itself
    committed into the hash. A later run that flips it must NOT silently mutate
    the committed artifact — it writes a NEW artifact (the old hash stays the
    tamper-evident record of what was promised pre-data).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="Dataset label, e.g. 'upworthy', 'hillstrom', 'criteo'.")
    split_policy: SplitPolicy
    present: bool = Field(
        default=False,
        description="Whether the dataset is already imported at pre-registration time (honesty: usually False — pre-data).",
    )


class ComponentDecisionRule(BaseModel):
    """The build/cut decision rule for ONE ablated component (§3 / §4), structured.

    Captures the §3 rule — "CI-excludes-zero marginal gain on ≥1 slice → build;
    fails both → cut" — as MACHINE-CHECKABLE fields, not prose, so the eventual
    analysis can evaluate it mechanically against the realized CIs:

    * `build_if`  — the realized result that confirms the component (default: its
      marginal-gain CI excludes zero on at least one of the two slices).
    * `cut_if`    — the realized result that cuts it (default: it fails BOTH
      slices, i.e. neither marginal-gain CI excludes zero).
    * `metric`    — the outcome the CI is computed on (the §5 primary is rank-ρ).
    * `slices`    — the slices the rule reads (the §3 ladder + knockout).

    The defaults encode the §3 rule verbatim; a component may override them (e.g.
    a stricter bar for a costly component) and the override is itself committed.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: str = Field(description="Component label, must match an entry in the orderings.")
    metric: Literal["rank_rho", "direction_accuracy"] = Field(
        default="rank_rho",
        description="Outcome the marginal-gain CI is computed on (§5 primary endpoint is rank_rho).",
    )
    slices: tuple[str, ...] = Field(
        default=("value_ladder", "knockout"),
        description="The slices the build/cut rule reads (sufficiency + necessity).",
    )
    build_if: str = Field(
        default="marginal_gain_ci_excludes_zero_on_at_least_one_slice",
        description="Machine-checkable condition that CONFIRMS the component (§3).",
    )
    cut_if: str = Field(
        default="marginal_gain_ci_includes_zero_on_all_slices",
        description="Machine-checkable condition that CUTS the component (§3).",
    )


class RunConfig(BaseModel):
    """The run config the pre-registered analysis is BOUND to (§5 item 4).

    Bound into the hash so the commitment covers not just WHAT we predict but
    exactly HOW the run that tests it is configured — seed, the resampling
    counts, the intended datasets + their split policies, and the explicit
    BLOCKERS that make the artifact honest about being pre-data / pre-run.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    seed: int = Field(description="The seed the eventual run + null permutations are bound to.")
    n_permutations: int = Field(
        ge=1, description="Null-integrity label permutations the run will draw (§4)."
    )
    bootstrap_resamples: int = Field(
        ge=0, description="Paired-bootstrap resamples for the marginal-gain CIs (§4)."
    )
    datasets: tuple[DatasetPlan, ...] = Field(
        min_length=1,
        description="The datasets the run intends, each with its committed split policy.",
    )
    blockers: tuple[str, ...] = Field(
        default=(),
        description=(
            "Explicit, honest pre-conditions not yet met (e.g. 'upworthy-not-yet-imported', "
            "'live-llm-run-deferred'). Committed into the hash so the artifact can never "
            "be read as post-data once it was pre-data."
        ),
    )

    @model_validator(mode="after")
    def _dataset_names_are_distinct(self) -> RunConfig:
        # Each dataset must appear once: a duplicate name would carry two
        # conflicting split-policy / present commitments for the same dataset,
        # so the primary endpoint's binding to it is ambiguous (codex P2).
        names = [d.name for d in self.datasets]
        if len(set(names)) != len(names):
            raise ValueError("run_config.datasets has duplicate dataset names")
        return self


class PreRegistration(BaseModel):
    """The §5 hash-committed pre-registration artifact — the whole commitment.

    Frozen: once built, a committed artifact is immutable in-process. The only
    legitimate way to change it is to build a NEW one (which gets a new hash); an
    illegitimate post-hoc edit (deserialize → mutate a field → re-serialize)
    leaves `integrity_hash` stale, which `verify()` catches.

    `created_at` is INJECTED by the caller (`services.benchmark_preregistration`
    accepts it as a parameter and never calls a clock), so the hashing core stays
    pure and deterministic: the same inputs + the same `created_at` always yield
    the same hash, and the timestamp is itself part of the commitment.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = Field(default=1, description="Artifact schema version.")

    # ── §5 item 1: primary endpoint ──
    primary_metric: Literal["rank_rho"] = Field(
        default="rank_rho",
        description="The pre-registered PRIMARY endpoint metric (§5: rank-ρ).",
    )
    primary_datasets: tuple[str, ...] = Field(
        min_length=1,
        description="Datasets the primary endpoint is measured on (§5: Upworthy + Hillstrom/Criteo).",
    )

    # ── §5 item 2: predicted orderings (ordered lists, best → worst) ──
    predicted_identity_depth_ordering: tuple[str, ...] = Field(
        min_length=1,
        description=(
            "§3 identity-depth ordering, best→worst: "
            "(persona+row, row-only, persona-only, generic). Stored ordered so the "
            "realized ordering can be scored against it."
        ),
    )
    predicted_value_ladder_ordering: tuple[str, ...] = Field(
        min_length=1,
        description=(
            "§3b expected marginal-gain ranking, largest→smallest: "
            "(blinded_framing, individual_row, structural_diff, verbalized_distribution, "
            "paraphrase_k3). Stored ordered for the same reason."
        ),
    )

    # ── §5 item 3: per-component decision rules (structured) ──
    decision_rules: tuple[ComponentDecisionRule, ...] = Field(
        min_length=1,
        description="One build/cut rule per ablated component, machine-checkable (§3 / §4).",
    )

    @model_validator(mode="after")
    def _commitments_are_complete_and_consistent(self) -> PreRegistration:
        # A pre-registration is the machine-checkable contract the later analysis
        # applies; an incomplete or inconsistent one would hash-commit cleanly yet
        # leave the analysis unable to apply the promised rule (codex P2). Reject
        # at the boundary so a malformed commitment can never be sealed.

        # primary_datasets must be one-entry-per-dataset: a repeat would let the
        # later analysis double-count (or silently de-dup) a dataset under the
        # primary endpoint (codex P2), the same one-entry rule already enforced on
        # the orderings and run_config.datasets.
        if len(set(self.primary_datasets)) != len(self.primary_datasets):
            raise ValueError("primary_datasets has duplicate entries; one entry per dataset")

        # Each predicted ordering must be a genuine ORDERING — no duplicate
        # element, or the "best→worst" position of the repeated element is
        # ambiguous and the realized-vs-predicted scoring is ill-defined.
        for label, ordering in (
            ("predicted_identity_depth_ordering", self.predicted_identity_depth_ordering),
            ("predicted_value_ladder_ordering", self.predicted_value_ladder_ordering),
        ):
            if len(set(ordering)) != len(ordering):
                raise ValueError(f"{label} has duplicate elements; an ordering must be distinct")

        # The decision rules are the per-component build/cut contract for the
        # value-ladder components, so they must cover EXACTLY that ordering — no
        # duplicate rule (which component's rule wins?), no rule for an
        # uncommitted component, and no value-ladder component left without a
        # rule (the analysis couldn't decide build/cut for it).
        rule_components = [r.component for r in self.decision_rules]
        if len(set(rule_components)) != len(rule_components):
            raise ValueError("decision_rules has duplicate components; one rule per component")
        ladder = set(self.predicted_value_ladder_ordering)
        rules = set(rule_components)
        if rules != ladder:
            missing = sorted(ladder - rules)
            extra = sorted(rules - ladder)
            raise ValueError(
                "decision_rules must cover exactly the value-ladder components "
                f"(missing rule for {missing}; rule for uncommitted component {extra})"
            )

        # The primary endpoint is measured on `primary_datasets`, but the split
        # policy + pre-data `present` flag that BIND the run to each dataset live
        # on `run_config.datasets`. Every primary dataset must therefore appear
        # in the run config, or the endpoint names a dataset the run isn't
        # actually bound to — no committed split policy, no honest present flag
        # (codex P2).
        configured = {d.name for d in self.run_config.datasets}
        uncovered = sorted(set(self.primary_datasets) - configured)
        if uncovered:
            raise ValueError(
                f"primary_datasets {uncovered} are not in run_config.datasets; "
                "every primary dataset must carry a committed split policy + present flag"
            )
        return self

    # ── §5 item 4: the bound run config (with honest blockers) ──
    run_config: RunConfig

    # ── timestamp (caller-injected, part of the commitment) ──
    created_at: str = Field(
        description="ISO-8601 creation timestamp, INJECTED by the caller (never clock-read in core)."
    )

    # ── §5 item 5: the hash-commit ──
    integrity_hash: str = Field(
        description=(
            "SHA-256 over the canonical serialization of EVERY committed field above. "
            "The tamper-evident commitment: any post-hoc edit moves it; `verify()` recomputes it."
        )
    )

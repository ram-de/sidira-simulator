"""
arm_dictionary.py — the SIDIRA-SIDE decoder ring for a Senu study (ticket #547 part C).

WHY THIS LIVES ON THE SIDIRA SIDE (not in Senu)
-----------------------------------------------
Senu is multi-tenant — built to serve every customer, not just Sidira — so it is
deliberately generic. When you design a Senu game you pick a hand-vetted template,
declare the behavior-schema field that carries the arm, and assign ROLE-named arm
values (`calm`/`urgent`). Senu already knows, GENERICALLY, everything an A/B test
needs:
  - each arm's experimental ROLE: `baseline` (= control) or `manipulation`
    (= treatment)  — enforced in StudySpec (`armRoleSchema`); an arm literally
    cannot be named `control`/`treatment`, only role-tagged;
  - the frozen `primaryOutcome` + template `metric`;
  - a pre-registered `trueDirection` (`treatment_higher`/`control_higher`/null).

What Senu CANNOT hold — and must not, or it stops being multi-tenant — is the one
CUSTOMER-SPECIFIC fact: *what the manipulation arm MEANS in this customer's product.*
"`urgent` = we removed the skip-cap from THIS music app" is Sidira-customer semantics.

So the "arm dictionary" is a small SIDIRA-SIDE artifact, one per study, keyed by
`study_id`. It maps Senu's generic role-named arms to the customer's product change
(the current-state → proposed-state diff the engine renders as a `Hypothesis`), plus
a pointer to the current-state grounding (the crawled feature pack). Senu stays
generic and untouched; nothing is custom-built there.

WHAT'S GATED vs BUILDABLE NOW
-----------------------------
  - control-vs-treatment identification: NOT gated — comes from the arm ROLE that
    Senu already exports at the study level.
  - the product-change SEMANTICS (this file): buildable now as a Sidira-side format;
    it just needs to be AUTHORED per study, and the Senu export needs to be SHARED
    with Sidira (the Sidira–Senu data agreement). No Senu code change.

Schema (one dict per study):
  study_id*        the Senu StudySpec id
  behavior_schema* the emitted behavior-export-schema id (e.g. "split_the_loot.v1")
  arms*            list, one per arm, each:
                     name*   the role-named arm value as Senu emits it ("calm"/"urgent")
                     role*   "baseline" | "manipulation"   (mirrors Senu's StudySpec;
                             we re-assert it so the store is self-contained + checkable)
  product_change*  what the MANIPULATION arm represents vs baseline, in state-diff terms:
                     summary*         one line ("remove the 6-skip/hour cap for free users")
                     current_state*   what baseline reflects ("free tier capped at 6 skips/hr")
                     proposed_state*  what manipulation reflects ("unlimited skips")
                     not_changing     list of things held fixed (parity discipline)
  feature_pack_ref pointer to the crawled feature pack (reverse-engineered current-state
                   PRD/Figma) that grounds the agents — the current-state context, NOT
                   the numeric substrate.
  expected_direction  optional "treatment_higher"|"control_higher"|null — the human/lit
                   prior. If the Senu export already carries `trueDirection`, that is the
                   source of truth; this is a fallback/cross-check only.
  authored_by / authored_at   provenance (role-separation discipline).

This module is intentionally infra-free (plain python, no backend import) so the
research store stays runnable anywhere. When the backend adapter is wired, the same
dict feeds `render_state_diff(capability, hypothesis)` in production.
"""
from __future__ import annotations

import json
from pathlib import Path

ROLES = {"baseline", "manipulation"}
REQUIRED = ("study_id", "behavior_schema", "arms", "product_change")
ARM_REQUIRED = ("name", "role")
CHANGE_REQUIRED = ("summary", "current_state", "proposed_state")


def validate(d: dict) -> dict:
    """Validate an arm-dictionary dict; raise SystemExit with a precise message on any gap."""
    missing = [k for k in REQUIRED if not d.get(k)]
    if missing:
        raise SystemExit(f"arm_dictionary: missing required fields: {missing}")

    arms = d["arms"]
    if not isinstance(arms, list) or not arms:
        raise SystemExit("arm_dictionary: 'arms' must be a non-empty list")
    roles_seen = set()
    names_seen = set()
    for a in arms:
        am = [k for k in ARM_REQUIRED if not a.get(k)]
        if am:
            raise SystemExit(f"arm_dictionary: arm {a!r} missing {am}")
        if a["role"] not in ROLES:
            raise SystemExit(f"arm_dictionary: bad role {a['role']!r}; allowed {sorted(ROLES)}")
        if a["name"] in names_seen:
            raise SystemExit(f"arm_dictionary: duplicate arm name {a['name']!r}")
        names_seen.add(a["name"])
        roles_seen.add(a["role"])
    # The same contrast Senu's validator enforces — a study with no manipulation (or no
    # baseline) isn't an A/B test; refuse it here too so a malformed dict can't silently
    # yield a control-less "ground truth".
    if roles_seen != ROLES:
        raise SystemExit(
            f"arm_dictionary: need at least one 'baseline' AND one 'manipulation' arm; "
            f"got roles {sorted(roles_seen)}"
        )

    ch = d["product_change"]
    cm = [k for k in CHANGE_REQUIRED if not ch.get(k)]
    if cm:
        raise SystemExit(f"arm_dictionary: product_change missing {cm}")
    return d


def load(path: str | Path) -> dict:
    return validate(json.loads(Path(path).read_text()))


def role_of(d: dict, arm_name: str) -> str:
    """Return 'baseline'|'manipulation' for an arm name, or raise if unknown."""
    for a in d["arms"]:
        if a["name"] == arm_name:
            return a["role"]
    raise SystemExit(f"arm_dictionary: arm {arm_name!r} not declared for study {d['study_id']!r}")


def baseline_name(d: dict) -> str:
    return next(a["name"] for a in d["arms"] if a["role"] == "baseline")


def manipulation_name(d: dict) -> str:
    return next(a["name"] for a in d["arms"] if a["role"] == "manipulation")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="validate a Sidira-side arm dictionary")
    ap.add_argument("path")
    args = ap.parse_args()
    d = load(args.path)
    print(f"OK: study {d['study_id']} · baseline={baseline_name(d)!r} "
          f"manipulation={manipulation_name(d)!r} · schema={d['behavior_schema']}")

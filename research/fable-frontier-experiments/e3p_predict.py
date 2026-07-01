"""E3-P pipeline v2 — translator -> availability check -> CALL (deterministic
calculator) / ABSTAIN, per case per arm (A strict pre-launch, B post-pilot).

Per PREREG_E3P_BACKLOG_PREVALENCE.md (sha256 80f5625d...).

v2 REVISION (blind, pre-seal — truths untouched; v1 output kept as
e3p_predictions_v1_discarded.json; see e3p_deviations.md):
v1 asked the translator ONE decidability question, which it answered in the
strict pre-launch sense, collapsing both arms to abstain even where Arm B has
per-arm pilot outcome tables (E1's proven extraction regime). v2 separates:
- translator (claude-opus-4-8, never outputs a sign; prose + metric only):
  estimand, mechanism family, description sufficiency, and
  composition_pre_launch = decidable WITHOUT the experiment's own arm-outcome
  data, from baseline/segment-mix/shift-share tables (this is the prereg's
  PREVALENCE flag), plus required pre-launch quantities.
- decidability-with-observed-tables is deterministic: if per-arm outcome
  aggregates exist for the arm, the calculator extracts the direction.
Deviation (carried from E1): `temperature` omitted — the model rejects it.

Calculator rules fixed before truths are unsealed:
- two-proportion z on per-arm n+rate; |z| >= 1.96 -> sign, else "flat"
- rates without n: relative diff >= 1% -> sign, else "flat"
- parallel per-arm segment tables: Simpson guard — common segment-weight
  perturbations (each segment x0.8/x1.2, all-up, all-down) on the pooled
  diff; any sign flip -> ABSTAIN ambiguous_binding
- arm identification by token overlap between arm keys and the case's
  control/treatment text; tie or zero overlap -> ABSTAIN ambiguous_binding

BLINDING: reads ONLY e3p_backlog.json. Never touches e3p_truths*.
"""
import json
import math
import re
import sys
import time
from pathlib import Path

import anthropic

HERE = Path(__file__).parent
MODEL = "claude-opus-4-8"

TRANSLATOR_SYSTEM = (
    "You are a translator inside a pre-registered evaluation pipeline. You NEVER "
    "predict outcomes, directions, or effect sizes, and you NEVER say which arm "
    "will do better. You only classify the decision problem. Output strict JSON, "
    "no markdown fences."
)

TRANSLATOR_PROMPT = """An A/B experiment decision problem:

{prose}

Primary metric: {metric}

Classify this decision problem. Tier-1 aggregate tables are things like:
baseline outcome rates by segment, segment/traffic mix, treatment-induced
shift shares (how the treatment moves units between segments/states), and
per-segment response rates — all WITHOUT the experiment's own per-arm outcome
data.

Return JSON exactly:
{{
 "estimand": one of "primary" (direct effect on the named primary metric), "guardrail" (effect on a protective secondary metric), "net_business" (net economics combining several quantities), "segment" (effect within a subpopulation),
 "mechanism_family": short snake_case label for the dominant mechanism through which the treatment could move the metric,
 "composition_pre_launch": true ONLY if the primary-metric direction could be decided by deterministic arithmetic over tier-1 aggregate tables as defined above, WITHOUT observing the experiment's own arm outcomes and WITHOUT any behavioral judgment (i.e., the effect is a composition/mix/arithmetic consequence of measurable quantities); false if deciding requires knowing how users behaviorally respond to the change,
 "required_quantities_pre_launch": if composition_pre_launch, the minimal subset of ["segment_mix","baseline_rates","treatment_shift_shares","per_segment_response_rates"] sufficient to decide by arithmetic; else [],
 "description_sufficient": true if control/treatment/metric are concrete enough to bind to data tables, else false,
 "notes": one sentence
}}"""


def load_key() -> str:
    for line in (HERE.parent.parent / "backend" / ".env").read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("no ANTHROPIC_API_KEY")


# ---------- deterministic table adapter + calculator ----------

_RATE_KEY = re.compile(r"(rate|mean|share_converted)", re.I)


def _tok(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower())) - {
        "the", "a", "an", "is", "at", "of", "to", "group", "arm", "and"}


def identify_arms(tables: dict, case: dict):
    """Map the two arm keys to (control_obj, treatment_obj) via token overlap
    with the case's control/treatment descriptions. None on ambiguity."""
    arms = tables.get("arms")
    if not isinstance(arms, dict) or len(arms) != 2:
        return None
    (k1, v1), (k2, v2) = list(arms.items())
    ctok, ttok = _tok(case["control"]), _tok(case["treatment"])

    def score(key):
        kt = _tok(key)
        s = len(kt & ctok) - len(kt & ttok)
        if "control" in kt or "holdout" in kt or "baseline" in kt:
            s += 2
        if "treatment" in kt or "variant" in kt:
            s -= 2
        return s
    s1, s2 = score(k1), score(k2)
    if s1 == s2:
        return None
    return (v1, v2) if s1 > s2 else (v2, v1)


def _arm_stats(obj: dict, metric: str):
    """(n, rate, segments[list of {label, n, rate}]) from one arm object."""
    if not isinstance(obj, dict):
        return None, None, None
    n = next((obj[k] for k in ("n", "total_users", "users", "total")
              if isinstance(obj.get(k), (int, float))), None)
    rate = None
    for k, v in obj.items():
        if isinstance(v, (int, float)) and (k == metric or _RATE_KEY.search(k)):
            rate = float(v)
            break
    segs = None
    for k, v in obj.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            parsed = []
            for x in v:
                sn = next((x[kk] for kk in ("n", "users", "count")
                           if isinstance(x.get(kk), (int, float))), None)
                sr = next((float(vv) for kk, vv in x.items()
                           if isinstance(vv, (int, float)) and _RATE_KEY.search(kk)), None)
                lbl = next((vv for vv in x.values() if isinstance(vv, str)), None)
                if sn is None or sr is None or lbl is None:
                    parsed = None
                    break
                parsed.append({"label": lbl, "n": sn, "rate": sr})
            if parsed:
                segs = parsed
                break
    if rate is None and segs:
        tot = sum(s["n"] for s in segs)
        rate = sum(s["n"] * s["rate"] for s in segs) / tot if tot else None
        n = n or tot
    return n, rate, segs


def _pooled_diff(cs, ts, wmul):
    def pooled(segs):
        num = sum(s["n"] * wmul.get(s["label"], 1.0) * s["rate"] for s in segs)
        den = sum(s["n"] * wmul.get(s["label"], 1.0) for s in segs)
        return num / den
    return pooled(ts) - pooled(cs)


def calculator(tables: dict, case: dict):
    """Returns (decision, direction-or-abstain-reason)."""
    pair = identify_arms(tables, case)
    if pair is None:
        return "abstain", "ambiguous_binding"
    ctrl, treat = pair
    metric = tables.get("metric") or case["primary_metric"]
    cn, cr, csegs = _arm_stats(ctrl, metric)
    tn, tr, tsegs = _arm_stats(treat, metric)
    if cr is None or tr is None:
        return "abstain", "missing_response_quantity"
    # Simpson guard on parallel segment tables
    if csegs and tsegs:
        labels = [s["label"] for s in csegs]
        if labels == [s["label"] for s in tsegs]:
            base = _pooled_diff(csegs, tsegs, {})
            perturbs = []
            for lbl in labels:
                for m in (0.8, 1.2):
                    perturbs.append(_pooled_diff(csegs, tsegs, {lbl: m}))
            perturbs.append(_pooled_diff(csegs, tsegs, {l: 0.8 for l in labels}))
            perturbs.append(_pooled_diff(csegs, tsegs, {l: 1.2 for l in labels}))
            if abs(base) > 1e-12 and any((p > 0) != (base > 0) for p in perturbs):
                return "abstain", "ambiguous_binding"
    if cn and tn and 0 <= cr <= 1 and 0 <= tr <= 1:
        p = (cr * cn + tr * tn) / (cn + tn)
        se = math.sqrt(max(p * (1 - p) * (1 / cn + 1 / tn), 1e-18))
        z = (tr - cr) / se
        if abs(z) >= 1.96:
            return "call", ("up" if tr > cr else "down")
        return "call", "flat"
    rel = abs(tr - cr) / abs(cr) if cr else float("inf")
    if rel >= 0.01:
        return "call", ("up" if tr > cr else "down")
    return "call", "flat"


# ---------- availability (arm A pre-launch quantities) ----------

def availability_a(case: dict) -> set:
    a = case.get("arm_a_tables")
    if not a:
        return set()
    have = {"baseline_rates"}
    blob = json.dumps(a).lower()
    if "segment" in blob or "mix" in blob or "bin" in blob:
        have.add("segment_mix")
        if "rate" in blob:
            have.add("per_segment_response_rates")
    if "shift" in blob:
        have.add("treatment_shift_shares")
    return have


def main() -> None:
    client = anthropic.Anthropic(api_key=load_key())
    backlog = json.loads((HERE / "e3p_backlog.json").read_text())
    preds, n_api = [], 0
    for i, case in enumerate(backlog):
        prompt = TRANSLATOR_PROMPT.format(prose=case["prose"],
                                          metric=case["primary_metric"])
        tr = None
        for attempt in range(3):
            try:
                resp = client.messages.create(
                    model=MODEL, max_tokens=500, system=TRANSLATOR_SYSTEM,
                    messages=[{"role": "user", "content": prompt}])
                txt = resp.content[0].text.strip()
                if txt.startswith("```"):
                    txt = txt.strip("`").lstrip("json").strip()
                tr = json.loads(txt)
                n_api += 1
                break
            except Exception as e:  # noqa: BLE001
                print(f"  translator retry {case['id']}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        if tr is None:
            tr = {"estimand": "primary", "mechanism_family": "unknown",
                  "composition_pre_launch": False,
                  "required_quantities_pre_launch": [],
                  "description_sufficient": False, "notes": "translator failed"}

        comp = bool(tr.get("composition_pre_launch"))
        suff = bool(tr.get("description_sufficient", True))
        need = set(tr.get("required_quantities_pre_launch") or [])
        have_a = availability_a(case)

        for arm in ("A", "B"):
            rec = {"id": case["id"], "arm": arm, "stratum": case["stratum"],
                   "estimand": tr.get("estimand"),
                   "mechanism_family": tr.get("mechanism_family"),
                   "prevalence_flag": comp,
                   "required_quantities_pre_launch": sorted(need)}
            if not suff:
                rec.update(decision="abstain", direction=None,
                           abstain_reason="insufficient_description")
            elif arm == "B" and case.get("arm_b_tables"):
                decision, out = calculator(case["arm_b_tables"], case)
                if decision == "call":
                    rec.update(decision="call", direction=out, abstain_reason=None)
                else:
                    rec.update(decision="abstain", direction=None, abstain_reason=out)
            elif comp:
                missing = need - have_a
                if not missing:
                    # composition path with complete pre-launch tables: no case
                    # in this backlog carries shift shares, but keep it honest
                    rec.update(decision="abstain", direction=None,
                               abstain_reason="missing_shift_quantity",
                               note="composition path present but no composer for this table shape")
                elif "treatment_shift_shares" in missing:
                    rec.update(decision="abstain", direction=None,
                               abstain_reason="missing_shift_quantity",
                               missing=sorted(missing))
                else:
                    rec.update(decision="abstain", direction=None,
                               abstain_reason="missing_response_quantity",
                               missing=sorted(missing))
            else:
                # non-composition mechanism: pre-launch (A) the mechanism itself
                # is the blocker; post-pilot (B) the blocker is the absent
                # per-arm pilot aggregates (unpublished in the artifact)
                reason = ("non_composition_mechanism" if arm == "A"
                          else "missing_response_quantity")
                rec.update(decision="abstain", direction=None, abstain_reason=reason)
            preds.append(rec)
        print(f"[{i+1}/{len(backlog)}] {case['id']}: "
              f"A={preds[-2]['decision']}({preds[-2].get('abstain_reason') or preds[-2]['direction']}) "
              f"B={preds[-1]['decision']}({preds[-1].get('abstain_reason') or preds[-1]['direction']})")

    (HERE / "e3p_predictions.json").write_text(json.dumps(preds, indent=1))
    print(f"done: {len(preds)} predictions ({n_api} translator calls)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""E2 — Same-Tag, Opposite-Sign Library Audit (pre-registered).

Implements PREREG_E2_TAG_SIGN_AMBIGUITY.md exactly.

Real arm: 15 scored portfolio cases (PORTFOLIO_CASES_V3.json) + 2 Hillstrom
outcome-level cases (visit, conversion) constructed from the sealed spike
results in research/empirical-uplift-spike/realdata_hillstrom_result.json.
Truth encoding: real_winner=treatment -> '+', control -> '-'.

Tagger: claude-opus-4-8, temperature 0, 3 runs/case. Prompt contains ONLY
control description + treatment description + metric name (leakage guard:
no effect, no winner, no counter_intuitive flag, no domain field).

Outputs research/fable-frontier-experiments/e2_result.json with verbatim
prompts, all raw tagger outputs, metrics, and the pre-registered verdict.
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import anthropic

WORKTREE = Path("/Users/ram/Projects/sidira-simulator/.claude/worktrees/fable-e1-e2")
EXP_DIR = WORKTREE / "research" / "fable-frontier-experiments"
PORTFOLIO = WORKTREE / "sessions" / "agent-behavior-spec" / "portfolio-benchmark" / "PORTFOLIO_CASES_V3.json"
HILLSTROM = WORKTREE / "research" / "empirical-uplift-spike" / "realdata_hillstrom_result.json"
ENV_FILE = WORKTREE / "backend" / ".env"
RESULT_FILE = EXP_DIR / "e2_result.json"

MODEL = "claude-opus-4-8"
N_RUNS = 3
FAMILIES = [
    "mix_shift", "gross_vs_net", "trade_down_cannibalization", "friction_change",
    "salience_attention", "trust_signal", "habit_loop", "layout_navigation",
    "personalization", "other",
]

SYSTEM_PROMPT = (
    "You are a mechanism classifier for A/B test changes. Given a control description, "
    "a treatment description, and a metric name, classify the mechanism by which the "
    "treatment could move the metric.\n\n"
    "Respond with strict JSON only (no markdown, no prose):\n"
    '{"family": "<one of: ' + ", ".join(FAMILIES) + '>", '
    '"mediator_role": "<the named behavioral lever, lowercase_snake_case>"}\n\n'
    "Do not predict the direction or size of the effect. Do not mention any outcome."
)

PROMPT_TEMPLATE = (
    "Control: {control}\n"
    "Treatment: {treatment}\n"
    "Metric: {metric}\n"
)


def load_api_key() -> str:
    for line in ENV_FILE.read_text().splitlines():
        m = re.match(r"^\s*ANTHROPIC_API_KEY\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise RuntimeError("ANTHROPIC_API_KEY not found in backend/.env")


def build_cases() -> tuple[list[dict], list[str]]:
    """Return (cases, notes). Each case: id, control, treatment, metric, truth."""
    notes = []
    cases = []
    portfolio = json.loads(PORTFOLIO.read_text())
    for c in portfolio["scored_cases"]:
        truth = "+" if c["real_winner"] == "treatment" else "-"
        cases.append({
            "id": c["id"],
            "control": c["control"],
            "treatment": c["treatment"],
            "metric": c["metric"],
            "truth": truth,
            "source": "PORTFOLIO_CASES_V3.scored_cases",
        })

    hs = json.loads(HILLSTROM.read_text())
    hs_metrics = {r["metric"]: r for r in hs["results"]}
    hs_control = ("Customers on the retail mailing list receive no email campaign "
                  "during the two-week test window.")
    hs_treatment = ("Customers on the retail mailing list are sent an email campaign "
                    "featuring men's merchandise during the two-week test window.")
    hs_metric_names = {
        "visit": "website visit rate within two weeks",
        "conversion": "purchase conversion rate within two weeks",
    }
    for outcome in ("visit", "conversion", "spend"):
        r = hs_metrics.get(outcome)
        if r is None:
            notes.append(
                f"Hillstrom outcome '{outcome}' EXCLUDED: not present in "
                f"realdata_hillstrom_result.json (prereg notes spend ~0 / ambiguous)."
            )
            continue
        ate = r["true_ate_pp"]
        if ate == 0:
            notes.append(f"Hillstrom outcome '{outcome}' EXCLUDED: true_ate_pp == 0 (null sign).")
            continue
        truth = "+" if ate > 0 else "-"
        notes.append(
            f"Hillstrom outcome '{outcome}' INCLUDED with truth '{truth}': "
            f"true_ate_pp={ate}, all estimator signs RIGHT in the sealed file."
        )
        cases.append({
            "id": f"hillstrom_mens_email_{outcome}",
            "control": hs_control,
            "treatment": hs_treatment,
            "metric": hs_metric_names[outcome],
            "truth": truth,
            "source": "realdata_hillstrom_result.json (constructed outcome-level case)",
        })
    return cases, notes


def snake(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s.strip().lower()).strip("_")
    return s or "unparsed"


def parse_output(text: str) -> dict:
    """Strict-ish JSON parse; returns {'family','mediator_role','parse_error'?}."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    try:
        obj = json.loads(t)
        fam = str(obj.get("family", "")).strip()
        med = snake(str(obj.get("mediator_role", "")))
        if fam not in FAMILIES:
            return {"family": "invalid", "mediator_role": med, "parse_error": f"family '{fam}' not in closed set"}
        return {"family": fam, "mediator_role": med}
    except Exception as e:
        return {"family": "invalid", "mediator_role": "unparsed", "parse_error": str(e)}


def majority(values: list[str]) -> str:
    """Majority (>N/2) of 3 runs; ties/no-majority -> 'unstable' per prereg."""
    top, n = Counter(values).most_common(1)[0]
    return top if n > len(values) / 2 else "unstable"


def compute_metrics(cases: list[dict], grain: str) -> dict:
    """grain: 'family' or 'family_mediator'. Excludes tag=='unstable' from denominator."""
    tagged = [c for c in cases if c[f"tag_{grain}"] != "unstable"]
    groups: dict[str, list[dict]] = {}
    for c in tagged:
        groups.setdefault(c[f"tag_{grain}"], []).append(c)
    ge2 = {t: g for t, g in groups.items() if len(g) >= 2}
    n_in_groups = sum(len(g) for g in ge2.values())
    ambiguous = {t: g for t, g in ge2.items() if {"+", "-"} <= {c["truth"] for c in g}}
    n_ambiguous = sum(len(g) for g in ambiguous.values())
    return {
        "grain": grain,
        "groups": {t: {"members": [c["id"] for c in g],
                       "signs": [c["truth"] for c in g],
                       "sign_ambiguous": t in ambiguous}
                   for t, g in sorted(groups.items())},
        "n_cases_tagged": len(tagged),
        "n_unstable": len(cases) - len(tagged),
        "n_cases_in_ge2_groups": n_in_groups,
        "n_cases_in_ambiguous_groups": n_ambiguous,
        "ambiguity": (n_ambiguous / n_in_groups) if n_in_groups else None,
    }


def main() -> None:
    client = anthropic.Anthropic(api_key=load_api_key())
    cases, notes = build_cases()
    print(f"{len(cases)} cases; notes: {notes}", file=sys.stderr)

    total_in = total_out = n_calls = 0
    for c in cases:
        prompt = PROMPT_TEMPLATE.format(control=c["control"], treatment=c["treatment"], metric=c["metric"])
        c["prompt_verbatim"] = prompt
        c["runs"] = []
        for i in range(N_RUNS):
            # DEVIATION: prereg says temperature 0, but the claude-opus-4-8 API
            # rejects the parameter ("`temperature` is deprecated for this model").
            # It is omitted; the pre-registered 3-run majority rule covers stability.
            resp = client.messages.create(
                model=MODEL, max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
            parsed = parse_output(raw)
            c["runs"].append({"run": i + 1, "raw_output": raw, "parsed": parsed})
            total_in += resp.usage.input_tokens
            total_out += resp.usage.output_tokens
            n_calls += 1
        fams = [r["parsed"]["family"] for r in c["runs"]]
        meds = [r["parsed"]["family"] + "::" + r["parsed"]["mediator_role"] for r in c["runs"]]
        c["tag_family"] = majority(fams)
        c["tag_family_mediator"] = majority(meds)
        c["stable_family"] = len(set(fams)) == 1
        c["stable_family_mediator"] = len(set(meds)) == 1
        print(f"{c['id']}: family={c['tag_family']} truth={c['truth']} runs={fams}", file=sys.stderr)

    primary = compute_metrics(cases, "family")
    secondary = compute_metrics(cases, "family_mediator")

    # Per-family sign base rates (all tagged cases, primary grain).
    base_rates = {}
    for c in cases:
        if c["tag_family"] == "unstable":
            continue
        br = base_rates.setdefault(c["tag_family"], {"+": 0, "-": 0})
        br[c["truth"]] += 1

    n_ge2 = primary["n_cases_in_ge2_groups"]
    amb = primary["ambiguity"]
    if n_ge2 < 5:
        verdict = "UNMEASURABLE"
        rationale = f"<5 real cases in >=2-member groups (n={n_ge2}); conservative branch — tags stay an uncertainty axis."
    elif amb > 0.30:
        verdict = "KILL"
        rationale = f"AMBIGUITY {amb:.3f} > 0.30 on the real arm; mechanism-tag retrieval banned from selecting a sign."
    else:
        verdict = "SURVIVE"
        rationale = f"AMBIGUITY {amb:.3f} <= 0.30 with {n_ge2} >= 5 in-group cases; tag-conditioned sign priors may be investigated (not shipped)."

    stability = {
        "family_identical_across_3_runs": sum(c["stable_family"] for c in cases),
        "family_mediator_identical_across_3_runs": sum(c["stable_family_mediator"] for c in cases),
        "n_cases": len(cases),
    }

    result = {
        "experiment": "E2_TAG_SIGN_AMBIGUITY",
        "prereg": "PREREG_E2_TAG_SIGN_AMBIGUITY.md",
        "model": MODEL,
        "temperature": "omitted — DEVIATION from prereg (temperature 0): claude-opus-4-8 API rejects the parameter as deprecated; 3-run majority rule (pre-registered) covers stability",
        "runs_per_case": N_RUNS,
        "system_prompt_verbatim": SYSTEM_PROMPT,
        "construction_notes": notes,
        "cases": cases,
        "primary_metric_family_grain": primary,
        "secondary_metric_family_mediator_grain": secondary,
        "per_family_sign_base_rates": base_rates,
        "tag_stability": stability,
        "verdict": verdict,
        "verdict_rationale": rationale,
        "api_usage": {"n_calls": n_calls, "input_tokens": total_in, "output_tokens": total_out},
    }
    RESULT_FILE.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "ambiguity": amb, "n_in_ge2_groups": n_ge2,
                      "api_calls": n_calls, "in_tok": total_in, "out_tok": total_out}, indent=2))


if __name__ == "__main__":
    main()

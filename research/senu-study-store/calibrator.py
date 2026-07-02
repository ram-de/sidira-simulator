"""
calibrator.py — the study-store → calibrator wiring (the #222 slice).

SCAFFOLD — 0 real cases; runs on fixtures. This is the NARROW calibrator-wiring
slice of ticket #222 (the Tier-0 benchmark harness), NOT the full epic. The full
Tier-0 harness (Upworthy 22k held-out headlines, Hewitt archive, Hillstrom/Criteo
end-to-end, the 150–200-experiment null-integrity + power suite) remains a separate,
founder-gated, cross-repo epic. All this module does is fill "the empty slot #222
waits for": the predicted-vs-measured SCORER that reads the shipped Senu study-store's
three artifacts and computes directional accuracy.

WHAT IT DOES
------------
Pairs each case's engine **BLIND** prediction against its **MEASURED** ground truth and
reports calibration. The scored comparison is `engine_blind` vs `measured` — and ONLY
that. The sealed `human_truth` hypothesis is a third, separate artifact and is NEVER
scored here (3-artifact role-separation discipline, calibration contract §11): a WIN is
engine_blind-vs-measured, never human_truth-vs-anything. Neither side is ever authored to
match the other — both are read verbatim.

Outputs:
  - Directional accuracy = hits / (hits + misses) over NON-abstain, NON-tie cases (the WIN
    metric), with the abstain rate reported ALONGSIDE (an abstain is honest, not a miss).
  - Guard × correctness table: for each guard verdict (CONFIRMS / CONTRADICTS /
    CANT-VALIDATE) the hit/miss/abstain breakdown — the watchdog's real-world validation
    slot (does CONFIRMS correlate with hits? does CANT-VALIDATE correctly abstain?).
  - Null-integrity check: cases flagged placebo/null (a `null_case: true` marker on the
    prereg, or an A/A groundTruthName) must predict ≈ abstain/tie — violations counted.
  - Power honesty: N and a loud caveat that directional accuracy from < ~150 cases is NOT
    a track-record claim (the Kohavi "always-flat scores 67–90%" / 20-experiment-pilot
    warning) is baked into the report text.

DORMANT until real sealed pairs land. Senu is founder-gated / operationally not producing
results yet, so no real engine_blind/measured pairs exist. The scorer runs on the shipped
`examples/` fixtures as a dry demo and is otherwise dormant. No network, no LLM, no prod
imports — pure stdlib (+ the study-store modules in this directory).

CLI:
  python calibrator.py --from-examples [--out CALIBRATION_REPORT.md]
  python calibrator.py --store studies.jsonl [--out CALIBRATION_REPORT.md]
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Power honesty: below this many scored cases, directional accuracy is NOT a track record.
POWER_MIN_CASES = 150

# Outcomes.
HIT = "hit"
MISS = "miss"
ABSTAIN = "abstain"          # engine declined → excluded from directional accuracy, counted separately
TIE_EXCLUDED = "tie-excluded"  # measured is a tie → excluded from directional accuracy
UNSCORABLE = "unscorable"    # malformed artifact → flagged, never raises

GUARDS = ("CONFIRMS", "CONTRADICTS", "CANT-VALIDATE")


# --------------------------------------------------------------------------- #
# Verbatim readers — read BOTH artifact shapes, never author either side.
# --------------------------------------------------------------------------- #
def _prediction_block(engine_blind: dict) -> dict:
    """The engine's prediction fields, whether nested under `prediction` (the prereg
    TEMPLATE shape) or flat on the engine_blind dict (the studystore `engine_blind` shape).
    Read verbatim — we never synthesize a prediction."""
    if not isinstance(engine_blind, dict):
        return {}
    pred = engine_blind.get("prediction")
    if isinstance(pred, dict):
        return pred
    return engine_blind


def _engine_sign(engine_blind: dict) -> str | None:
    """Normalize the engine's blind sign to one of '+', '-', 'abstain', or None if malformed."""
    raw = _prediction_block(engine_blind).get("sign")
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if s in ("+", "positive", "up", "treatment_higher"):
        return "+"
    if s in ("-", "negative", "down", "control_higher"):
        return "-"
    if s in ("abstain", "abstained", "decline", "declined", "na", "n/a"):
        return "abstain"
    return None


def _engine_guard(engine_blind: dict) -> str | None:
    raw = _prediction_block(engine_blind).get("guard")
    if not isinstance(raw, str):
        return None
    g = raw.strip().upper()
    return g if g in GUARDS else raw.strip()  # keep unknown verdicts visible, don't drop


def _engine_confidence(engine_blind: dict) -> float | None:
    raw = _prediction_block(engine_blind).get("confidence")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _measured_sign(ground_truth: dict) -> str | None:
    """Map the MEASURED truth to a sign: '+', '-', '0' (tie), or None if malformed.

    Reads BOTH shapes verbatim:
      - the adapter `GroundTruth` (has `winner` ∈ {treatment, control, tie}), or
      - the studystore `measured` block (has a `sign` ∈ {'+','-','~0'}).
    treatment → '+', control → '-', tie → '0'. NEVER inferred from the engine's call.
    """
    if not isinstance(ground_truth, dict):
        return None
    winner = ground_truth.get("winner")
    if isinstance(winner, str):
        w = winner.strip().lower()
        if w == "treatment":
            return "+"
        if w == "control":
            return "-"
        if w in ("tie", "~0", "0", "none", "null"):
            return "0"
        return None
    sign = ground_truth.get("sign")
    if isinstance(sign, str):
        s = sign.strip().lower()
        if s == "+":
            return "+"
        if s == "-":
            return "-"
        if s in ("~0", "0", "0.0", "tie", "none"):
            return "0"
    return None


# --------------------------------------------------------------------------- #
# Null / placebo detection (the A/A honesty check, §222 item 3 in miniature).
# --------------------------------------------------------------------------- #
def _ground_truth_name(case_id: str | None) -> str | None:
    """The 4th segment of 'senu:<studyId>:<behaviorSchema>:<groundTruthName>'."""
    if not isinstance(case_id, str):
        return None
    parts = case_id.split(":")
    return parts[3] if len(parts) == 4 else None


def _is_aa_name(name: str | None) -> bool:
    """True if a metric/groundTruthName looks like an A/A or placebo/null cell."""
    if not isinstance(name, str):
        return False
    tokens = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t]
    if any(t in {"aa", "placebo", "sham", "null", "noop"} for t in tokens):
        return True
    # consecutive a,a → A/A (matches "a_a", "a-a", "a/a")
    return any(tokens[i] == "a" and tokens[i + 1] == "a" for i in range(len(tokens) - 1))


def _is_null_case(engine_blind: dict, ground_truth: dict, case_id: str | None) -> bool:
    """A case is null/placebo if the prereg carries a `null_case: true` marker, or the
    groundTruthName / measured metric name reads as A/A."""
    if isinstance(engine_blind, dict):
        if engine_blind.get("null_case") is True:
            return True
        if isinstance(engine_blind.get("prediction"), dict) and \
                engine_blind["prediction"].get("null_case") is True:
            return True
    if _is_aa_name(_ground_truth_name(case_id)):
        return True
    if isinstance(ground_truth, dict) and _is_aa_name(
        ground_truth.get("metric_name") or ground_truth.get("metric")
    ):
        return True
    return False


# --------------------------------------------------------------------------- #
# CaseScore
# --------------------------------------------------------------------------- #
@dataclass
class CaseScore:
    case_id: str
    engine_sign: str | None          # '+','-','abstain', or None
    measured_sign: str | None        # '+','-','0', or None
    guard: str | None
    confidence: float | None
    outcome: str                     # HIT|MISS|ABSTAIN|TIE_EXCLUDED|UNSCORABLE
    is_null: bool
    null_violation: bool
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "engine_sign": self.engine_sign,
            "measured_sign": self.measured_sign,
            "guard": self.guard,
            "confidence": self.confidence,
            "outcome": self.outcome,
            "is_null": self.is_null,
            "null_violation": self.null_violation,
            "note": self.note,
        }


def score_case(engine_blind: dict, ground_truth: dict, case_id: str | None = None) -> CaseScore:
    """Score ONE case: engine BLIND prediction vs MEASURED truth. Never raises — a malformed
    artifact returns a flagged UNSCORABLE CaseScore.

    Outcome precedence: unscorable → abstain (engine declined) → tie-excluded (measured tie)
    → hit/miss. An abstain is excluded from directional accuracy and counted separately; a
    measured tie is excluded too. NEVER authors either side to match the other.
    """
    cid = case_id or (engine_blind.get("case_id") if isinstance(engine_blind, dict) else None) \
        or "unknown"
    try:
        e_sign = _engine_sign(engine_blind)
        m_sign = _measured_sign(ground_truth)
        guard = _engine_guard(engine_blind)
        conf = _engine_confidence(engine_blind)
        is_null = _is_null_case(engine_blind, ground_truth, cid)

        # A null/placebo case that got a DIRECTIONAL (non-abstain) engine sign is a violation.
        null_violation = bool(is_null and e_sign in ("+", "-"))

        if e_sign is None or m_sign is None:
            missing = []
            if e_sign is None:
                missing.append("engine_blind.sign")
            if m_sign is None:
                missing.append("measured winner/sign")
            return CaseScore(cid, e_sign, m_sign, guard, conf, UNSCORABLE, is_null,
                             null_violation, note=f"unscorable: unreadable {', '.join(missing)}")

        if e_sign == "abstain":
            outcome = ABSTAIN
            note = "engine abstained (honest non-answer; excluded from directional accuracy)"
        elif m_sign == "0":
            outcome = TIE_EXCLUDED
            note = "measured tie (excluded from directional accuracy)"
        elif e_sign == m_sign:
            outcome = HIT
            note = f"blind {e_sign} == measured {m_sign}"
        else:
            outcome = MISS
            note = f"blind {e_sign} != measured {m_sign}"

        return CaseScore(cid, e_sign, m_sign, guard, conf, outcome, is_null,
                         null_violation, note=note)
    except Exception as exc:  # defensive: the scorer must NEVER raise on bad data
        return CaseScore(cid, None, None, None, None, UNSCORABLE, False, False,
                         note=f"unscorable: {type(exc).__name__}: {exc}")


# --------------------------------------------------------------------------- #
# CalibrationReport
# --------------------------------------------------------------------------- #
@dataclass
class CalibrationReport:
    cases: list[CaseScore] = field(default_factory=list)

    @property
    def n_total(self) -> int:
        return len(self.cases)

    def _count(self, outcome: str) -> int:
        return sum(1 for c in self.cases if c.outcome == outcome)

    @property
    def hits(self) -> int:
        return self._count(HIT)

    @property
    def misses(self) -> int:
        return self._count(MISS)

    @property
    def abstains(self) -> int:
        return self._count(ABSTAIN)

    @property
    def tie_excluded(self) -> int:
        return self._count(TIE_EXCLUDED)

    @property
    def unscorable(self) -> int:
        return self._count(UNSCORABLE)

    @property
    def directional_accuracy(self) -> float | None:
        """hits / (hits + misses) — the WIN metric, over non-abstain, non-tie cases.
        None when there are no directional cases (don't fabricate a rate from nothing)."""
        denom = self.hits + self.misses
        return (self.hits / denom) if denom else None

    @property
    def abstain_rate(self) -> float | None:
        """Abstains among directional-eligible cases (hits + misses + abstains)."""
        denom = self.hits + self.misses + self.abstains
        return (self.abstains / denom) if denom else None

    @property
    def null_cases(self) -> int:
        return sum(1 for c in self.cases if c.is_null)

    @property
    def null_violations(self) -> int:
        return sum(1 for c in self.cases if c.null_violation)

    @property
    def guard_table(self) -> dict[str, dict[str, int]]:
        """{guard_verdict: {hit, miss, abstain, tie-excluded, unscorable}}."""
        table: dict[str, dict[str, int]] = {}
        for c in self.cases:
            g = c.guard or "(none)"
            row = table.setdefault(
                g, {HIT: 0, MISS: 0, ABSTAIN: 0, TIE_EXCLUDED: 0, UNSCORABLE: 0}
            )
            row[c.outcome] = row.get(c.outcome, 0) + 1
        return table

    @property
    def underpowered(self) -> bool:
        return (self.hits + self.misses) < POWER_MIN_CASES

    def power_caveat(self) -> str:
        scored = self.hits + self.misses
        loud = (
            f"⚠️  POWER CAVEAT: {scored} directional case(s) is FAR below the "
            f"~{POWER_MIN_CASES}-case floor. Directional accuracy here is NOT a track-record "
            f"claim. Kohavi's warning applies: a stopped-clock 'always predict flat/lift' "
            f"baseline scores 67–90% on small, unbalanced experiment sets, and 20-experiment "
            f"pilots routinely mislead. Treat this number as a wiring smoke-test, not evidence."
        )
        ok = (
            f"{scored} directional case(s) — at or above the ~{POWER_MIN_CASES}-case floor. "
            f"Still read accuracy against the base rate and the null-integrity check."
        )
        return loud if self.underpowered else ok

    def to_dict(self) -> dict:
        return {
            "scaffold": True,
            "note": "SCAFFOLD — study-store → calibrator wiring (#222 slice). Dormant until "
                    "real sealed engine_blind/measured pairs land (founder-gated Senu). "
                    "Does NOT close #222; the full Tier-0 harness is a separate epic.",
            "win_definition": "engine_blind sign vs measured sign ONLY; human_truth is NOT "
                              "scored (3-artifact role-separation).",
            "n_total": self.n_total,
            "hits": self.hits,
            "misses": self.misses,
            "abstains": self.abstains,
            "tie_excluded": self.tie_excluded,
            "unscorable": self.unscorable,
            "directional_accuracy": self.directional_accuracy,
            "abstain_rate": self.abstain_rate,
            "guard_table": self.guard_table,
            "null_cases": self.null_cases,
            "null_violations": self.null_violations,
            "underpowered": self.underpowered,
            "power_caveat": self.power_caveat(),
            "cases": [c.to_dict() for c in self.cases],
        }


def calibrate(pairs: list[tuple[dict, dict]] | list[CaseScore]) -> CalibrationReport:
    """Score N paired cases. Accepts either (engine_blind, ground_truth) tuples or
    already-scored CaseScore objects."""
    cases: list[CaseScore] = []
    for item in pairs:
        if isinstance(item, CaseScore):
            cases.append(item)
        else:
            engine_blind, ground_truth = item
            cases.append(score_case(engine_blind, ground_truth))
    return CalibrationReport(cases=cases)


# --------------------------------------------------------------------------- #
# Report rendering
# --------------------------------------------------------------------------- #
def _fmt_pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def render_markdown(report: CalibrationReport, source: str) -> str:
    da = report.directional_accuracy
    da_str = "—" if da is None else f"{report.hits}/{report.hits + report.misses} ({_fmt_pct(da)})"

    guard_rows = ["| Guard verdict | hit | miss | abstain | tie-excl | unscorable |",
                  "|---|---|---|---|---|---|"]
    for g in list(GUARDS) + [g for g in report.guard_table if g not in GUARDS]:
        row = report.guard_table.get(g)
        if not row:
            continue
        guard_rows.append(
            f"| {g} | {row[HIT]} | {row[MISS]} | {row[ABSTAIN]} | "
            f"{row[TIE_EXCLUDED]} | {row[UNSCORABLE]} |"
        )

    case_rows = ["| Case | Guard | Conf | Blind | Measured | Outcome | Null | Note |",
                 "|---|---|---|---|---|---|---|---|"]
    for c in report.cases:
        conf = "—" if c.confidence is None else f"{c.confidence:.2f}"
        nullmark = "‼ VIOLATION" if c.null_violation else ("null" if c.is_null else "—")
        case_rows.append(
            f"| `{c.case_id}` | {c.guard or '—'} | {conf} | {c.engine_sign or '—'} | "
            f"{c.measured_sign or '—'} | **{c.outcome}** | {nullmark} | {c.note[:60]} |"
        )

    ni_line = (
        f"**{report.null_violations} violation(s)** out of {report.null_cases} null/placebo "
        f"case(s)." if report.null_cases else "No null/placebo cases in this set."
    )

    return f"""# Calibration Report — Senu study-store → engine-blind vs measured

> **SCAFFOLD — {report.n_total} case(s) from `{source}`.** This is the NARROW
> **calibrator-wiring slice of #222**, not the full Tier-0 benchmark harness (Upworthy /
> Hewitt / Hillstrom / Criteo / 150–200-experiment power + null suite — a separate,
> founder-gated, cross-repo epic). **This report does NOT close #222.** DORMANT until real
> sealed engine_blind/measured pairs land (founder-gated Senu); it runs on fixtures now.

## The only rule that counts

A **WIN is `engine_blind` sign vs `measured` sign — nothing else.** The sealed
`human_truth` hypothesis is a third, separate artifact and is **NEVER scored** here
(3-artifact role-separation discipline). Neither side is authored to match the other; both
are read verbatim.

## Directional accuracy (the WIN metric)

- **Directional accuracy: {da_str}** — hits / (hits + misses), over NON-abstain, NON-tie cases.
- **Abstain rate: {_fmt_pct(report.abstain_rate)}** ({report.abstains} abstain(s)) — reported
  ALONGSIDE. An abstain is an honest non-answer, **not** a miss.
- Tie-excluded: {report.tie_excluded} · Unscorable (flagged malformed): {report.unscorable}.

{report.power_caveat()}

## Guard × correctness (the watchdog's validation slot)

Does `CONFIRMS` correlate with hits? Does `CANT-VALIDATE` correctly abstain?

{chr(10).join(guard_rows)}

## Null-integrity check (the A/A honesty check — §222 item 3 in miniature)

Null/placebo cases (a `null_case: true` prereg marker, or an A/A groundTruthName) must
predict ≈ abstain/tie. A directional (non-abstain) prediction on a null case is a violation.

{ni_line}

## Cases

{chr(10).join(case_rows)}

---
_Generated by `calibrator.py`. Research-only; no prod, no redeploy. Feeds the #222
conversion_calibrator once real sealed pairs land. Sibling of the study-store `LEDGER.md`._
"""


# --------------------------------------------------------------------------- #
# Fixture demo (dry, no network) — pairs derived from the shipped examples.
# --------------------------------------------------------------------------- #
def example_pairs() -> list[tuple[dict, dict]]:
    """Build a small illustrative set from the shipped fixtures so the scaffold has
    something to score in a dry run. These are SYNTHETIC demo pairs — clearly not real
    results — exercising hit / miss / abstain / tie / null-violation outcomes.

    The FIRST pair is the real fixture pairing: the example arm-dictionary + envelope run
    through the adapter (measured winner=control → '-') against the example_case engine_blind
    (blind sign '-') → a HIT.
    """
    import arm_dictionary as armdict  # local import: keeps top-level infra-free
    from senu_export_to_benchmarkcase import export_to_benchmarkcases

    env = json.loads((HERE / "examples/study_S123_envelope.json").read_text())
    ad = armdict.load(HERE / "examples/study_S123_arm_dictionary.json")
    gt = export_to_benchmarkcases(env, ad, ["accept_rate"])[0]["ground_truth"]  # winner=control

    ex_case = json.loads((HERE / "example_case.json").read_text())
    real_blind = {"case_id": "senu:S123:split_the_loot.v1:accept_rate", **ex_case["engine_blind"]}

    return [
        # 1. real fixture pairing — engine blind '-' vs measured control ('-') → HIT
        (real_blind, gt),
        # 2. a WRONG-sign demo — engine blind '+' vs the same measured control ('-') → MISS
        ({"case_id": "senu:DEMO:split_the_loot.v1:accept_rate_wrong",
          "prediction": {"sign": "+", "confidence": 0.62, "guard": "CONFIRMS"}}, gt),
        # 3. an ABSTAIN demo — engine declined (CANT-VALIDATE) → excluded from directional acc
        ({"case_id": "senu:DEMO:split_the_loot.v1:net_revenue",
          "prediction": {"sign": "abstain", "confidence": 0.2, "guard": "CANT-VALIDATE"}},
         {"metric_name": "net_revenue", "winner": "treatment"}),
        # 4. a measured TIE demo → tie-excluded
        ({"case_id": "senu:DEMO:split_the_loot.v1:dwell_ms",
          "prediction": {"sign": "+", "confidence": 0.55, "guard": "CONFIRMS"}},
         {"metric_name": "dwell_ms", "winner": "tie"}),
        # 5. a NULL/placebo A/A demo where the engine predicted a sign → null-integrity VIOLATION
        ({"case_id": "senu:DEMO:split_the_loot.v1:aa_placebo",
          "prediction": {"sign": "+", "confidence": 0.6, "guard": "CONFIRMS"}},
         {"metric_name": "aa_placebo", "winner": "control"}),
        # 6. a NULL/placebo A/A demo where the engine correctly ABSTAINED → no violation
        ({"case_id": "senu:DEMO:split_the_loot.v1:a_a_null", "null_case": True,
          "prediction": {"sign": "abstain", "confidence": 0.1, "guard": "CANT-VALIDATE"}},
         {"metric_name": "a_a_null", "winner": "tie"}),
        # 7. a malformed artifact demo → unscorable, never raises
        ({"case_id": "senu:DEMO:split_the_loot.v1:broken",
          "prediction": {"sign": "???"}}, {"winner": "banana"}),
    ]


# --------------------------------------------------------------------------- #
# Store loading
# --------------------------------------------------------------------------- #
# Non-final store statuses whose records are not yet a sealed engine_blind/measured pair.
_NON_FINAL_STATUS = {"RUNNING", "PENDING", "VOID"}


def load_store_pairs(store_path: Path) -> tuple[list[tuple[dict, dict, str]], int]:
    """Read a studystore JSONL, keep the latest line per case_id, and return
    ``(pairs, skipped)`` where ``pairs`` is the (engine_blind, measured, case_id) triples
    for the SCORABLE records only.

    A studystore holds records at every lifecycle stage (RUNNING / PENDING / SCORED /
    ABSTAINED / VOID), and `append_case` defaults an unfilled record to empty
    engine_blind/measured blocks. Only records that are actually PAIRED — a non-empty
    engine_blind AND a non-empty measured, and not VOID / still-running — are calibration
    cases. Unpaired / non-final rows are SKIPPED (not counted as `unscorable`), so pending
    or voided studies never make the report look noisier than it is."""
    from studystore import latest_by_id

    cases = [json.loads(ln) for ln in store_path.read_text().splitlines() if ln.strip()]
    pairs: list[tuple[dict, dict, str]] = []
    skipped = 0
    for rec in latest_by_id(cases):
        engine_blind = rec.get("engine_blind") or {}
        measured = rec.get("measured") or {}
        status = (rec.get("status") or "").upper()
        if status in _NON_FINAL_STATUS or not engine_blind or not measured:
            skipped += 1
            continue
        pairs.append((engine_blind, measured, rec.get("case_id", "unknown")))
    return pairs, skipped


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(
        description="study-store → calibrator: engine-blind vs measured directional scorer "
                    "(#222 slice; scaffold, dormant until real sealed pairs land)."
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--store", help="path to a studystore JSONL (studies.jsonl)")
    src.add_argument("--from-examples", action="store_true",
                     help="run the dry demo on the shipped example fixtures (no network)")
    ap.add_argument("--out", default="CALIBRATION_REPORT.md",
                    help="markdown report path (a .json sibling is written too)")
    args = ap.parse_args()

    skipped = 0
    if args.from_examples:
        source = "examples/ (dry demo — SYNTHETIC, not real results)"
        report = calibrate(example_pairs())
    else:
        store_path = Path(args.store)
        pairs, skipped = load_store_pairs(store_path)
        source = str(store_path)
        report = CalibrationReport(cases=[
            score_case(eb, me, case_id=cid) for eb, me, cid in pairs
        ])

    md = render_markdown(report, source)
    out_md = Path(args.out)
    out_md.write_text(md)
    out_json = out_md.with_suffix(".json")
    out_json.write_text(json.dumps(report.to_dict(), indent=2))

    da = report.directional_accuracy
    print(f"calibrator: scored {report.n_total} paired case(s) from {source}"
          + (f" ({skipped} unpaired/non-final record(s) skipped)" if skipped else ""))
    print(f"  directional accuracy: "
          f"{'—' if da is None else f'{report.hits}/{report.hits + report.misses} ({da * 100:.1f}%)'} "
          f"| abstains {report.abstains} | tie-excl {report.tie_excluded} "
          f"| unscorable {report.unscorable}")
    print(f"  null cases {report.null_cases}, violations {report.null_violations}")
    if report.underpowered:
        print(f"  ⚠️  underpowered: < {POWER_MIN_CASES} directional cases — NOT a track record.")
    print(f"  wrote {out_md} and {out_json}")


if __name__ == "__main__":
    main()

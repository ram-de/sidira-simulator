"""
studystore.py — the append-only study-results store for Senu → Sidira engine feedback.

Every completed Senu study lands here as one JSON line in `studies.jsonl`, carrying the
whole reproducible chain in one findable record: the raw export envelope reference, the
computed MEASURED truth (the realized A/B outcome), the engine's BLIND prediction (made
without seeing the outcome), the score, and the sealed pre-registration sha. The store is
append-only (full history kept, diffable in git); corrections/late-arriving fields append a
NEW line and "latest line per case_id wins". `LEDGER.md` is REGENERATED — never hand-edited.

This is the sibling of `research/engine-strength-campaign/runstore.py`. Same discipline,
different payload: runstore logs *engine-method* validation runs; studystore logs
*real-world Senu cases* and how the engine's blind call fared against measured truth. It is
the durable home for the predicted-vs-actual pairs the #222 conversion_calibrator waits on.

Why a store and not a DB: queryable with jq/pandas, git-committed and reviewable, zero infra,
no prod coupling, and every case stays reproducible from its sealed prereg + seeded harness.

--- The case_id convention (the join key) -------------------------------------------------
  case_id = "senu:<studyId>:<behaviorSchema>:<groundTruthName>"
    studyId        the Senu StudySpec id that ran the game
    behaviorSchema the emitted behavior schema/version (e.g. "split-the-loot.v2")
    groundTruthName the named measured outcome (e.g. "accept_rate", "net_revenue")
  One study that yields two scored outcomes → two case_ids (…:accept_rate, …:net_revenue).
  This is also the id under which the case maps to a `BenchmarkCase` (see the adapter stub).

--- The 3-artifact role-separation discipline (LOCKED, calibration contract §11) ----------
  Three things that must be authored by SEPARATE roles / at separate times and NEVER tuned
  to each other. A WIN is engine_blind vs measured — never human_truth vs anything.
    human_truth_sha    sha256 of the sealed thoughtful-human hypothesis (before data)
    engine_blind       the engine's prediction made WITHOUT the measured outcome
    measured           the realized A/B result (ground truth)

Record schema (required *) :
  case_id*        "senu:<studyId>:<behaviorSchema>:<groundTruthName>"
  study_id*       the Senu StudySpec id (redundant-but-queryable)
  title*          one-line human description of the study/change
  pattern*        taxonomy tag from reference/engine-needs.md (e.g. "cannibalization",
                  "gross-vs-net", "segment-mix-flip", "dominance-flip", ...) or "other"
  status*         RUNNING | PENDING | SCORED | ABSTAINED | VOID
  data_type       "real"  (Senu cases are real per-user; kept for parity with runstore)
  human_truth_sha sha256 of the sealed human hypothesis (or null if not sealed yet)
  prereg_sha      sha256 of the sealed engine-blind prereg (or null)
  engine_blind    dict: {"sign": "+"|"-"|"abstain", "confidence": 0..1, "guard":
                  "CONFIRMS"|"CONTRADICTS"|"CANT-VALIDATE", "note": str}
  measured        dict: {"sign": "+"|"-"|"~0", "effect": float, "ci": [lo,hi],
                  "n": int, "metric": str}   (the realized truth; filled post-launch)
  score           dict: {"outcome": "HIT"|"MISS"|"ABSTAIN"|"PENDING", "sign_correct":
                  bool|null, "note": str}    (engine_blind vs measured — the only "win")
  envelope_ref    pointer to the raw senu.export.v1 envelope (path / R2 key / hash)
  benchmarkcase_ref  path to the derived BenchmarkCase json (or null until adapter runs)
  n               respondents / #players
  artifacts       list of file paths (prereg, envelope, harness, analysis notebook)
  timestamp       ISO-8601 (auto if omitted)
  notes           short string

CLI:
  python studystore.py add --file case.json          # or: --json '<record>' / stdin
  python studystore.py update --case-id ID --set status=SCORED --set score.outcome=HIT
  python studystore.py seal --file artifact.json      # print sha256 (for prereg sealing)
  python studystore.py ledger                         # regenerate LEDGER.md
  python studystore.py list
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORE = HERE / "studies.jsonl"
LEDGER = HERE / "LEDGER.md"

REQUIRED = ("case_id", "study_id", "title", "pattern", "status")
STATUSES = {"RUNNING", "PENDING", "SCORED", "ABSTAINED", "VOID"}
OUTCOMES = {"HIT", "MISS", "ABSTAIN", "PENDING"}
# taxonomy tags mirror reference/engine-needs.md — kept loose (validated as a warning only)
PATTERNS = {
    "cannibalization", "trade-down", "substitution", "novelty-decay", "gross-vs-net",
    "segment-mix-flip", "declutter-relevance", "friction-as-filter", "congestion",
    "habit-disruption", "anchoring", "paywall-nudge-removal", "dominance-flip", "other",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _sha256(obj) -> str:
    """Canonical sha256 of a JSON-serializable artifact (sorted keys, no whitespace drift)."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()

def load_cases() -> list[dict]:
    if not STORE.exists():
        return []
    return [json.loads(ln) for ln in STORE.read_text().splitlines() if ln.strip()]

def latest_by_id(cases: list[dict]) -> list[dict]:
    d: dict[str, dict] = {}
    for c in cases:
        d[c["case_id"]] = c          # last occurrence wins
    return list(d.values())

def _validate(rec: dict) -> None:
    missing = [k for k in REQUIRED if not rec.get(k)]
    if missing:
        raise SystemExit(f"studystore: missing required fields: {missing}")
    if rec["status"] not in STATUSES:
        raise SystemExit(f"studystore: bad status {rec['status']!r}; allowed {sorted(STATUSES)}")
    cid = rec["case_id"]
    if not (cid.startswith("senu:") and cid.count(":") == 3):
        raise SystemExit(f"studystore: case_id must be 'senu:<studyId>:<behaviorSchema>:"
                         f"<groundTruthName>', got {cid!r}")
    if rec["pattern"] not in PATTERNS:
        # a warning, not a hard fail — taxonomy can grow; keep the record but flag it
        print(f"studystore: WARNING unknown pattern {rec['pattern']!r} "
              f"(known: {sorted(PATTERNS)})", file=sys.stderr)
    sc = rec.get("score") or {}
    if sc.get("outcome") and sc["outcome"] not in OUTCOMES:
        raise SystemExit(f"studystore: bad score.outcome {sc['outcome']!r}; allowed {sorted(OUTCOMES)}")

def append_case(rec: dict) -> dict:
    _validate(rec)
    rec.setdefault("timestamp", _now())
    for k, v in (("data_type", "real"), ("human_truth_sha", None), ("prereg_sha", None),
                 ("engine_blind", {}), ("measured", {}), ("score", {"outcome": "PENDING"}),
                 ("envelope_ref", None), ("benchmarkcase_ref", None), ("n", None),
                 ("artifacts", []), ("notes", "")):
        rec.setdefault(k, v)
    with STORE.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec

def _coerce(v: str):
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v

def _set_path(rec: dict, dotted: str, value) -> None:
    """Support dotted keys so `--set score.outcome=HIT` reaches nested dicts."""
    parts = dotted.split(".")
    d = rec
    for p in parts[:-1]:
        d = d.setdefault(p, {})
        if not isinstance(d, dict):
            raise SystemExit(f"studystore: cannot set {dotted!r}; {p!r} is not an object")
    d[parts[-1]] = value

def update_case(case_id: str, sets: list[str]) -> dict:
    cur = {c["case_id"]: c for c in load_cases()}.get(case_id)
    if not cur:
        raise SystemExit(f"studystore: no case {case_id!r} to update")
    rec = json.loads(json.dumps(cur))  # deep copy
    for kv in sets:
        if "=" not in kv:
            raise SystemExit(f"studystore: --set expects key=value, got {kv!r}")
        k, v = kv.split("=", 1)
        _set_path(rec, k, _coerce(v))
    rec["timestamp"] = _now()
    return append_case(rec)

# --------------------------------------------------------------------------- #
def _outcome(c: dict) -> str:
    return (c.get("score") or {}).get("outcome") or "PENDING"

def _blind_vs_measured(c: dict) -> str:
    eb, me = c.get("engine_blind") or {}, c.get("measured") or {}
    ebs, mes = eb.get("sign", "—"), me.get("sign", "—")
    guard = eb.get("guard")
    g = f" [{guard}]" if guard else ""
    return f"blind {ebs} vs meas {mes}{g}"

def regenerate_ledger() -> None:
    cases = sorted(latest_by_id(load_cases()), key=lambda c: c.get("timestamp", ""))
    scored = [c for c in cases if _outcome(c) in ("HIT", "MISS")]
    hits = [c for c in cases if _outcome(c) == "HIT"]
    abstains = [c for c in cases if _outcome(c) == "ABSTAIN"]
    patterns_covered = sorted({c["pattern"] for c in cases})

    rows = ["| Case | Pattern | Human‑sha | Prereg | Blind vs Measured | Outcome | N | Notes |",
            "|---|---|---|---|---|---|---|---|"]
    for c in cases:
        hsha = (c.get("human_truth_sha") or "—"); hsha = hsha[:8] + "…" if len(hsha) > 9 else hsha
        psha = (c.get("prereg_sha") or "—");      psha = psha[:8] + "…" if len(psha) > 9 else psha
        rows.append(f"| `{c['case_id']}` | {c['pattern']} | `{hsha}` | `{psha}` | "
                    f"{_blind_vs_measured(c)} | **{_outcome(c)}** | {c.get('n') or '—'} | "
                    f"{(c.get('notes') or '')[:50]} |")

    acc = f"{len(hits)}/{len(scored)}" if scored else "0/0"
    md = f"""# Senu Study-Results Ledger — predicted‑vs‑actual, engine‑blind

> **Auto-generated from `studies.jsonl` by `studystore.py` — do not hand-edit.**
> Regenerate: `python studystore.py ledger`. Abstains and misses are findings and stay logged.

Each row is one real Senu case scored by the ONLY rule that counts: the engine's **blind**
prediction (made without the measured outcome) vs the **measured** truth. The sealed
`human_truth` hypothesis is a third, separate artifact — never the yardstick for a "win".

Outcome legend: `HIT` (blind sign == measured sign) · `MISS` (wrong sign) ·
`ABSTAIN` (engine declined — guard `CANT-VALIDATE` or low confidence; honest non-answer) ·
`PENDING` (not yet scored). Status legend: RUNNING · PENDING · SCORED · ABSTAINED · VOID.

**Scoreboard:** {len(cases)} case(s) · **sign accuracy {acc}** on scored cases · \
{len(abstains)} honest abstain(s). \
Taxonomy patterns covered: {', '.join(patterns_covered) if patterns_covered else '—'}.

> Read accuracy against the attempt count and remember the discipline: a win is only
> `engine_blind` vs `measured`. Never author one artifact to match another.

## Cases
{chr(10).join(rows)}

## Reproducibility contract
Every scored case must carry: (1) a sealed `human_truth_sha`, (2) a sealed `prereg_sha`
for the engine-blind call, (3) an `envelope_ref` to the raw `senu.export.v1` export, and
(4) a `benchmarkcase_ref` once the adapter has run. Re-running the sealed harness on the
referenced envelope must reproduce the `measured` block. See `README.md`.

_Feeds the #222 conversion_calibrator. Sibling of `../engine-strength-campaign/LEDGER.md`._
"""
    LEDGER.write_text(md)
    print(f"studystore: wrote {LEDGER} ({len(cases)} cases, {len(scored)} scored, sign-acc {acc})")

# --------------------------------------------------------------------------- #
def _load_rec(args) -> dict:
    if args.file:
        return json.loads(Path(args.file).read_text())
    if args.json:
        return json.loads(args.json)
    return json.loads(sys.stdin.read())

def main():
    p = argparse.ArgumentParser(description="Senu study-results store")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("--file"); a.add_argument("--json")
    u = sub.add_parser("update"); u.add_argument("--case-id", required=True)
    u.add_argument("--set", action="append", default=[], dest="sets")
    s = sub.add_parser("seal"); s.add_argument("--file"); s.add_argument("--json")
    sub.add_parser("ledger")
    sub.add_parser("list")
    args = p.parse_args()

    if args.cmd == "add":
        rec = append_case(_load_rec(args)); regenerate_ledger()
        print(f"studystore: added {rec['case_id']} ({rec['status']})")
    elif args.cmd == "update":
        rec = update_case(args.case_id, args.sets); regenerate_ledger()
        print(f"studystore: updated {rec['case_id']} -> {rec['status']}/{_outcome(rec)}")
    elif args.cmd == "seal":
        print(_sha256(_load_rec(args)))
    elif args.cmd == "ledger":
        regenerate_ledger()
    elif args.cmd == "list":
        for c in sorted(latest_by_id(load_cases()), key=lambda c: c.get("timestamp", "")):
            print(f"{_outcome(c):8} {c['case_id']:44} {c['title']}")

if __name__ == "__main__":
    main()

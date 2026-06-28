"""
runstore.py — the append-only run-store for the engine-strength campaign.

Every validation run (iteration 0 onward) is one JSON line in `runs.jsonl`. The store is
append-only (full history kept, diffable in git); status updates append a NEW line and
"latest line per run_id wins". `LEDGER.md` is REGENERATED from the store — never hand-edited.

Why a store and not a DB: queryable with jq/pandas, git-committed and reviewable, zero infra,
no prod coupling. It keeps every run in the campaign findable and honest in one place.

Record schema (required *) :
  run_id*        unique slug, e.g. "iter0-streamly" or "T1-ttscaling-k64"
  idea*          backlog id ("iter0", "T1".."T12", or "new")
  title*         one-line description
  dataset*       dataset name, e.g. "synthetic_streamly_10regimes"
  data_type*     "real" | "synthetic" | "public-real"   (synthetic != validation)
  verdict*       PROMOTED | LEAD | NULL | MECH-ONLY | RUNNING | PENDING
  prereg_sha     sha256 of the sealed pre-registration (or null)
  n              sample size / #cases
  baseline       what it's measured against (e.g. "router / comparative 0.50")
  result         dict of key numbers (free-form); a "headline" key is shown in the ledger
  replicated     true | false | null   (held-out replication done?)
  adversarially_verified  true | false | null
  artifacts      list of file paths (result json, prereg, harness)
  timestamp      ISO-8601 (auto if omitted)
  notes          short string

CLI:
  python runstore.py add --file rec.json          # or: --json '<record>' / stdin
  python runstore.py update --run-id ID --set verdict=NULL --set replicated=true
  python runstore.py ledger                        # regenerate LEDGER.md
  python runstore.py list
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORE = HERE / "runs.jsonl"
LEDGER = HERE / "LEDGER.md"

REQUIRED = ("run_id", "idea", "title", "dataset", "data_type", "verdict")
VERDICTS = {"PROMOTED", "LEAD", "NULL", "MECH-ONLY", "RUNNING", "PENDING"}
DATA_TYPES = {"real", "synthetic", "public-real"}
BACKLOG_SIZE = 12
CURRENT_BEST = ("empirical+LLM **router** (empirical/causal on the feature-expressible slice; "
                "LLM elsewhere, flagged). Baselines: roleplay 0.286, comparative 0.50.")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_runs() -> list[dict]:
    if not STORE.exists():
        return []
    return [json.loads(ln) for ln in STORE.read_text().splitlines() if ln.strip()]

def latest_by_id(runs: list[dict]) -> list[dict]:
    d: dict[str, dict] = {}
    for r in runs:
        d[r["run_id"]] = r          # last occurrence wins
    return list(d.values())

def _validate(rec: dict) -> None:
    missing = [k for k in REQUIRED if not rec.get(k)]
    if missing:
        raise SystemExit(f"runstore: missing required fields: {missing}")
    if rec["verdict"] not in VERDICTS:
        raise SystemExit(f"runstore: bad verdict {rec['verdict']!r}; allowed {sorted(VERDICTS)}")
    if rec["data_type"] not in DATA_TYPES:
        raise SystemExit(f"runstore: bad data_type {rec['data_type']!r}; allowed {sorted(DATA_TYPES)}")

def append_run(rec: dict) -> dict:
    _validate(rec)
    rec.setdefault("timestamp", _now())
    for k, v in (("prereg_sha", None), ("n", None), ("baseline", None), ("result", {}),
                 ("replicated", None), ("adversarially_verified", None),
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

def update_run(run_id: str, sets: list[str]) -> dict:
    cur = {r["run_id"]: r for r in load_runs()}.get(run_id)
    if not cur:
        raise SystemExit(f"runstore: no run {run_id!r} to update")
    rec = dict(cur)
    for kv in sets:
        if "=" not in kv:
            raise SystemExit(f"runstore: --set expects key=value, got {kv!r}")
        k, v = kv.split("=", 1)
        rec[k] = _coerce(v)
    rec["timestamp"] = _now()
    return append_run(rec)

# --------------------------------------------------------------------------- #
def _headline(r: dict) -> str:
    res = r.get("result") or {}
    if isinstance(res, dict) and res.get("headline"):
        return str(res["headline"])
    if isinstance(res, dict) and res:
        return ", ".join(f"{k}={v}" for k, v in list(res.items())[:3])
    return "—"

def _flags(r: dict) -> str:
    rep = {True: "yes", False: "no", None: "—"}[r.get("replicated")]
    adv = r.get("adversarially_verified")
    return rep + ("·adv✓" if adv else "")

def regenerate_ledger() -> None:
    runs = sorted(latest_by_id(load_runs()), key=lambda r: r.get("timestamp", ""))
    verdicted = [r for r in runs if r["verdict"] not in ("RUNNING", "PENDING")]
    promoted = [r for r in runs if r["verdict"] == "PROMOTED"]
    leads = [r for r in runs if r["verdict"] == "LEAD"]

    rows = ["| Idea | Title | Data | Prereg | Result (headline) | Verdict | Repl | Notes |",
            "|---|---|---|---|---|---|---|---|"]
    for r in runs:
        sha = (r.get("prereg_sha") or "—")
        sha = sha[:8] + "…" if len(sha) > 9 else sha
        rows.append(f"| {r['idea']} | {r['title']} | {r['dataset']} ({r['data_type']}) | "
                    f"`{sha}` | {_headline(r)} | **{r['verdict']}** | {_flags(r)} | "
                    f"{(r.get('notes') or '')[:60]} |")

    md = f"""# Engine-Strength Campaign — Results Ledger

> **Auto-generated from `runs.jsonl` by `runstore.py` — do not hand-edit.**
> Regenerate: `python runstore.py ledger`. Nulls are findings and stay logged.

Verdict legend: `PROMOTED` (beat current best, held-out + replicated + adversarially
verified) · `LEAD` (positive once, needs replication) · `NULL` (tested, no signal) ·
`MECH-ONLY` (synthetic only, not real-data validated) · `RUNNING` · `PENDING`.

**Current best to beat:** {CURRENT_BEST}

**Multiple-comparisons honesty:** {len(verdicted)} verdicted / {BACKLOG_SIZE} backlog · \
**{len(promoted)} promoted, {len(leads)} open lead(s)**. \
(A single p<0.05 across many ideas is expected by chance — read wins against the attempt count.)

## Runs
{chr(10).join(rows)}

## Pending backlog
T1–T{BACKLOG_SIZE} not yet run — see `PLAN.md` (seed backlog, tiered by cost × info). The
order there is a default, not a rule.

_See `PLAN.md` for the protocol, guardrails, and the promotion decision rule._
"""
    LEDGER.write_text(md)
    print(f"runstore: wrote {LEDGER} ({len(runs)} runs, {len(verdicted)} verdicted)")

# --------------------------------------------------------------------------- #
def _load_rec(args) -> dict:
    if args.file:
        return json.loads(Path(args.file).read_text())
    if args.json:
        return json.loads(args.json)
    return json.loads(sys.stdin.read())

def main():
    p = argparse.ArgumentParser(description="engine-strength run-store")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("--file"); a.add_argument("--json")
    u = sub.add_parser("update"); u.add_argument("--run-id", required=True)
    u.add_argument("--set", action="append", default=[], dest="sets")
    sub.add_parser("ledger")
    sub.add_parser("list")
    args = p.parse_args()

    if args.cmd == "add":
        rec = append_run(_load_rec(args)); regenerate_ledger()
        print(f"runstore: added {rec['run_id']} ({rec['verdict']})")
    elif args.cmd == "update":
        rec = update_run(args.run_id, args.sets); regenerate_ledger()
        print(f"runstore: updated {rec['run_id']} -> {rec['verdict']}")
    elif args.cmd == "ledger":
        regenerate_ledger()
    elif args.cmd == "list":
        for r in sorted(latest_by_id(load_runs()), key=lambda r: r.get("timestamp", "")):
            print(f"{r['verdict']:9} {r['run_id']:24} {r['title']}")

if __name__ == "__main__":
    main()

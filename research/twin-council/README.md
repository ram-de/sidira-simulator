# Twin-Council: directionally-correct simulation as a precursor to experimentation

Two independent expert councils — one on **Claude**, one on **Codex** — were each
convened as the same five seats (causal inference, LLM silicon-sampling,
agent-based modeling, survey/measurement, ML evaluation) and run on a loop until
they reached consensus on how to build a behavioral simulator that is
*directionally correct* enough to use as a precursor to A/B experimentation.

## Outcome

**Unanimous ratification, both councils, zero objections** — after two
substantive rounds plus a ratification round. They independently converged on a
single thesis and a single certification gate.

> The thing to build is **not a "digital twin."** It is a **calibrated causal
> prior over a backlog of changes** that ranks experiments and predicts the
> *sign* (positive / flat / harmful) of each, gated by a **held-out backtest of
> the product's own historical experiments**. Realism of personas is a means to a
> sign-informative feature, not the product. The live experiment stays ground
> truth. Below ~50 labeled past experiments the honest output is "uncalibrated."

Read **`WHITE-PAPER.md`** for the full argument.

## Artifacts (provenance)

| File | What it is |
|------|------------|
| `BRIEF.md` | The question + required output structure given to both councils |
| `rounds/r1-claude.md`, `rounds/r1-codex.md` | Round 1 — independent position papers |
| `ROUND1-ARBITRATION.md` | Neutral arbiter: agreed core (A1–A12) + 5 open items (D1–D5) |
| `rounds/r2-claude.md`, `rounds/r2-codex.md` | Round 2 — cross-critique resolving D1–D5 |
| `MERGED-LEDGER.md` | Arbiter-canonical merged ledger (M1–M22 + the G0–G11 gate) |
| `rounds/r3-claude.md`, `rounds/r3-codex.md` | Round 3 — both councils ratify (YES, no objections) |
| `WHITE-PAPER.md` | The joint white paper |
| `harness/` | Runnable implementation + tests of the G0–G11 gate |
| `rounds/*.log`, `codex-prompt-*.txt` | Raw Codex run logs and the prompts used |

## The gate, in one line

A simulator may show a PM a numeric confidence score only when `harness/certify()`
returns **GO**: enough labeled history (G0), passes A/A and leakage integrity
(G1, G3), predicts direction and rank above thresholds (G4–G6), is calibrated
(G7), improves decision utility over status-quo triage (G8, primary), is
tail-safe (G9), benefits from abstention (G10), and earns its personas over a
no-persona baseline (G11). Otherwise it abstains or stays qualitative — and never
auto-kills an idea.

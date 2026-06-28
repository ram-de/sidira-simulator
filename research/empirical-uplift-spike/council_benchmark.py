"""
Council-of-priors + router — benchmark prototype (Phase C).

WHY
---
The single-agent engine scores 0.50 directional accuracy on the portfolio
(portfolio_comparative_result.json: 7/14), and its errors are NOT random: on
high-counter-intuitive cases it predicts `treatment` almost every time the real
winner was `control` — a systematic "the new thing wins" prior. The council
makes that hidden prior EXPLICIT and PLURAL, then a router decides which prior
to trust per hypothesis. The test: does router+council beat the 0.50 baseline by
catching the cases where the obvious "treatment wins" is wrong?

DESIGN (one council per case, replacing the single reacting agent)
------
Members (same blinded case, different inductive bias in the system prompt):
  naive             — react plainly, no special prior.
  more_is_better    — believes richer / more-helpful / more-featured wins.
  contrarian        — has learned obvious product wins often backfire; hunts for
                      the mechanism by which the obvious choice LOSES.
  base_rate_skeptic — most changes move the metric ~zero; default to control
                      unless a strong, specific mechanism says otherwise.
Router/classifier:
  classifies the hypothesis regime {DEFAULT, MORE_BETTER, COUNTER_INTUITIVE}
  and names which member to trust.

PRE-REGISTERED consolidation (FIXED before seeing any result — do NOT tune to the
8 answers; n=8 is underpowered, directional-only, contamination-prone):
  regime -> member weights (multiplied by each member's self-reported confidence):
    DEFAULT          : skeptic 1.0, naive 0.5, more_is_better 0.3, contrarian 0.3
    MORE_BETTER      : more_is_better 1.0, naive 0.7, skeptic 0.4, contrarian 0.3
    COUNTER_INTUITIVE: contrarian 1.0, skeptic 0.8, naive 0.4, more_is_better 0.2
  Final winner = argmax over {control, treatment} of summed (weight * confidence)
  for members voting that winner. Ties -> control (status-quo default).

BLINDNESS: members + router see ONLY domain / control / treatment / metric.
real_winner, effect, counter_intuitive, contamination, credibility, source,
status are stripped — they ride only on scoring, never in the stimulus.

ABLATIONS scored side by side:
  naive_only       — just the naive member  (a single-agent stand-in)
  council_unrouted — equal-weight majority of all 4 members (council, no router)
  council_routed   — the pre-registered router-weighted consolidation

RUN
---
  GROQ_API_KEY=...  python3.11 council_benchmark.py            # live (Groq, llama-3.3-70b)
  ANTHROPIC_API_KEY=... python3.11 council_benchmark.py --provider anthropic
  python3.11 council_benchmark.py --dry-run                    # print prompts, no spend
Deterministic (temperature 0, fixed seed). Writes council_result.json.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path

CASES_PATH = Path(__file__).resolve().parents[2] / "sessions/agent-behavior-spec/portfolio-benchmark/PORTFOLIO_CASES.json"
SEED = 20260627
MODEL_GROQ = "llama-3.3-70b-versatile"
MODEL_ANTHROPIC = "claude-sonnet-4-6"

# --------------------------------------------------------------------------- #
# Council member system prompts (the explicit priors)
# --------------------------------------------------------------------------- #
_COMMON = (
    "You are forecasting the result of a real A/B test on a product. You will be "
    "shown a CONTROL variant and a TREATMENT variant and the metric being measured. "
    "Decide which variant produced the higher value of the metric. Reason from "
    "behavioral mechanism, not from which option sounds more modern. Respond ONLY "
    'with JSON: {"winner": "control"|"treatment", "confidence": 0.0-1.0, "reason": "<one sentence>"}.'
)
MEMBERS = {
    "naive": _COMMON,
    "more_is_better": (
        "You believe that giving users more — more features, more help, more "
        "reward, more guidance, fewer restrictions — generally improves engagement "
        "and the target metric. Lean toward whichever variant offers more to the "
        "user, unless something is clearly broken. " + _COMMON
    ),
    "contrarian": (
        "You have studied many product experiments and learned that the obvious, "
        "intuitive winner frequently BACKFIRES: added help can signal low status, "
        "removed friction can cheapen a habit, more reward can crowd out intrinsic "
        "motivation, more choice can paralyze. For this case, actively look for the "
        "mechanism by which the seemingly-better variant LOSES. " + _COMMON
    ),
    "base_rate_skeptic": (
        "You know most product changes move the target metric by approximately "
        "nothing, and that the control (status quo) is a strong default. Predict "
        "treatment ONLY when there is a specific, strong behavioral mechanism; "
        "otherwise favor control. " + _COMMON
    ),
}
ROUTER_SYSTEM = (
    "You are a hypothesis classifier for product A/B tests. Given a control and a "
    "treatment and the metric, classify the change into exactly one regime:\n"
    "  DEFAULT          — likely little/no real effect; status quo is a strong default.\n"
    "  MORE_BETTER      — a straightforward improvement where the obvious 'more/better' "
    "intuition is likely CORRECT.\n"
    "  COUNTER_INTUITIVE— the obvious intuition is likely WRONG; the change plausibly "
    "backfires through a behavioral side-effect.\n"
    'Respond ONLY with JSON: {"regime": "DEFAULT"|"MORE_BETTER"|"COUNTER_INTUITIVE", '
    '"confidence": 0.0-1.0, "reason": "<one sentence>"}.'
)

# regime -> member weights (PRE-REGISTERED, do not tune)
ROUTER_WEIGHTS = {
    "DEFAULT":           {"base_rate_skeptic": 1.0, "naive": 0.5, "more_is_better": 0.3, "contrarian": 0.3},
    "MORE_BETTER":       {"more_is_better": 1.0, "naive": 0.7, "base_rate_skeptic": 0.4, "contrarian": 0.3},
    "COUNTER_INTUITIVE": {"contrarian": 1.0, "base_rate_skeptic": 0.8, "naive": 0.4, "more_is_better": 0.2},
}

def blinded_case_text(c: dict) -> str:
    return (
        f"Domain: {c['domain']}\n"
        f"Metric (higher is better): {c['metric']}\n\n"
        f"CONTROL variant:\n{c['control']}\n\n"
        f"TREATMENT variant:\n{c['treatment']}"
    )

# --------------------------------------------------------------------------- #
# Minimal chat client (mirrors backend GroqChat / AnthropicChat; self-contained)
# --------------------------------------------------------------------------- #
class Chat:
    def __init__(self, provider: str, model: str | None):
        self.provider = provider
        if provider == "groq":
            from openai import OpenAI
            self._c = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
            self.model = model or MODEL_GROQ
        elif provider == "anthropic":
            from anthropic import Anthropic
            self._c = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            self.model = model or MODEL_ANTHROPIC
        else:
            raise SystemExit(f"unknown provider {provider}")

    def ask(self, system: str, user: str) -> str:
        if self.provider == "groq":
            r = self._c.chat.completions.create(
                model=self.model, temperature=0.0, seed=SEED, max_tokens=512,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            return r.choices[0].message.content or ""
        r = self._c.messages.create(
            model=self.model, temperature=0.0, max_tokens=512, system=system,
            messages=[{"role": "user", "content": user}])
        return r.content[0].text

def extract_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON in: {raw[:200]}")
    return json.loads(m.group(0))

# --------------------------------------------------------------------------- #
# Council evaluation of one case
# --------------------------------------------------------------------------- #
def eval_case(chat: Chat, case: dict) -> dict:
    stim = blinded_case_text(case)
    votes = {}
    for name, sys_prompt in MEMBERS.items():
        j = extract_json(chat.ask(sys_prompt, stim))
        w = str(j.get("winner", "")).lower()
        votes[name] = {"winner": "treatment" if "treat" in w else "control",
                       "confidence": float(j.get("confidence", 0.5)),
                       "reason": j.get("reason", "")}
    rj = extract_json(chat.ask(ROUTER_SYSTEM, stim))
    regime = str(rj.get("regime", "DEFAULT")).upper()
    if regime not in ROUTER_WEIGHTS:
        regime = "DEFAULT"

    def tally(weights):
        score = {"control": 0.0, "treatment": 0.0}
        for name, v in votes.items():
            score[v["winner"]] += weights.get(name, 1.0) * v["confidence"]
        # tie -> control (status-quo default)
        return "treatment" if score["treatment"] > score["control"] else "control"

    return {
        "id": case["id"],
        "real": case["real_winner"],
        "counter_intuitive": case.get("counter_intuitive", ""),
        "regime": regime,
        "votes": {k: v["winner"] for k, v in votes.items()},
        "pred_naive_only": votes["naive"]["winner"],
        "pred_council_unrouted": tally({k: 1.0 for k in MEMBERS}),
        "pred_council_routed": tally(ROUTER_WEIGHTS[regime]),
    }

def score(results: list[dict], key: str) -> float:
    hits = sum(1 for r in results if r[key] == r["real"])
    return hits / len(results) if results else 0.0

# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=None, help="groq|anthropic (auto from env if unset)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--dry-run", action="store_true", help="print prompts for case 1, no API calls")
    args = ap.parse_args()

    cases = json.loads(CASES_PATH.read_text())["scored_cases"]

    if args.dry_run:
        c = cases[0]
        print(f"# DRY RUN — {len(cases)} scored cases. Showing prompts for case: {c['id']}\n")
        print("=== BLINDED STIMULUS (what every member + router sees) ===")
        print(blinded_case_text(c))
        for name, s in MEMBERS.items():
            print(f"\n=== MEMBER system: {name} ===\n{s}")
        print(f"\n=== ROUTER system ===\n{ROUTER_SYSTEM}")
        print(f"\n(real_winner={c['real_winner']} — withheld from the model; used only to score.)")
        return

    provider = args.provider or ("groq" if "GROQ_API_KEY" in os.environ
                                 else "anthropic" if "ANTHROPIC_API_KEY" in os.environ else None)
    if provider is None:
        sys.exit("No LLM key found. Set GROQ_API_KEY (or ANTHROPIC_API_KEY), or use --dry-run.")
    chat = Chat(provider, args.model)

    results = [eval_case(chat, c) for c in cases]

    print(f"{'case':<40} {'real':<10} {'regime':<18} {'naive':<10} {'unrouted':<10} {'routed':<10}")
    print("-" * 100)
    for r in results:
        def mark(p): return f"{p}{'✓' if p==r['real'] else '✗'}"
        print(f"{r['id']:<40} {r['real']:<10} {r['regime']:<18} "
              f"{mark(r['pred_naive_only']):<11} {mark(r['pred_council_unrouted']):<11} {mark(r['pred_council_routed']):<11}")
    acc = {k: score(results, f"pred_{k}") for k in ("naive_only", "council_unrouted", "council_routed")}
    print("-" * 100)
    print(f"directional accuracy (n={len(results)}):  "
          f"naive_only={acc['naive_only']:.2f}  council_unrouted={acc['council_unrouted']:.2f}  "
          f"council_routed={acc['council_routed']:.2f}")
    print("baseline: single-agent engine = 0.50 (portfolio_comparative_result.json); prior_accuracy = 0.286")
    print("NOTE: n=8, directional-only, contamination-prone — a SIGNAL, not a validation.")

    out = Path(__file__).with_name("council_result.json")
    out.write_text(json.dumps({"provider": provider, "model": chat.model, "accuracy": acc,
                               "baseline_single_agent": 0.50, "results": results}, indent=2))
    print(f"\nwrote {out}")

if __name__ == "__main__":
    main()

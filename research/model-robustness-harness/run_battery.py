#!/usr/bin/env python3
"""One-command per-model robustness runner for the sealed AMBDOM + GNCE battery (ticket #546).

Re-run the sealed battery for a NAMED translator/narrator model and emit a scorecard
(directional/magnitude accuracy per slice + calibration + optimism/pessimism direction +
the flip-ceiling PASS/FAIL). The grounded predictor and the sealed truth are NEVER
re-run — they are read from the sealed result JSON. Only the LLM (words-only) arm
reflects the model under test.

    # live pre-adoption check for a new narrator model (needs the matching API key in ENV)
    python run_battery.py --model claude-opus-4-8 --arm narrator
    python run_battery.py --model gpt-5.5 --arm translator

    # DRY sanity — regenerate a scorecard from a saved log, NO network, NO key:
    python run_battery.py --score-only --from-log results/opus_llm_log.jsonl \
        --model claude-opus-4-8

Provider dispatch (by model-id prefix), key strictly from ENV, NEVER embedded / printed:
    claude-* / anthropic  -> ANTHROPIC_API_KEY   (https://api.anthropic.com/v1/messages)
    gpt-*    / o*         -> OPENAI_API_KEY       (https://api.openai.com/v1/chat/completions)
    llama-*  / groq/*     -> GROQ_API_KEY         (https://api.groq.com/openai/v1/chat/completions)

Faithful to the promoted runners (run_opus.py / run_gpt55.py): same SYSMSG, same
parse rule, cache-by-narrative (the battery reuses symmetric prose templates by design).
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request

from build_cases import build, cell_type

SYS = ("You are forecasting the direction of a product A/B test outcome. Answer with exactly "
       "one of: UP, DOWN, UNSURE on the first line, then a confidence between 0 and 1 on the "
       "second line. No other text.")

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_answer(text):
    """(sign in {-1,0,1}, confidence in [0,1] or None) — the promoted parse rule."""
    up = (text or "").upper()
    if "DOWN" in up:
        sign = -1
    elif "UP" in up:
        sign = 1
    else:
        sign = 0
    conf = None
    for mm in re.finditer(r"\d*\.?\d+", text or ""):
        try:
            v = float(mm.group())
            if 0.0 <= v <= 1.0:
                conf = v
                break
        except ValueError:
            pass
    return sign, conf


# ---------- provider dispatch (keys read from ENV only, never embedded/printed) ----------

def _provider_for(model_id):
    m = model_id.lower()
    if m.startswith("claude") or m.startswith("anthropic"):
        return "anthropic"
    if m.startswith("llama") or m.startswith("groq/") or "groq" in m:
        return "groq"
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
        return "openai"
    return "openai"  # OpenAI-compatible default


def _env_key(var):
    key = os.environ.get(var)
    if not key:
        sys.exit(f"ERROR: {var} not set in environment. "
                 "Keys must come from ENV (never embedded). Aborting — no network call made.")
    return key


def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def make_caller(model_id):
    """Return call(narrative)->raw_text for the model, or exit if reasoning provider needs care."""
    provider = _provider_for(model_id)

    if provider == "anthropic":
        key = _env_key("ANTHROPIC_API_KEY")
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}

        def call(nar):
            body = {"model": model_id, "max_tokens": 20, "system": SYS,
                    "messages": [{"role": "user", "content": nar}]}
            d = _post(url, body, headers)
            return "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
        return call

    # openai / groq — OpenAI-compatible chat completions
    if provider == "groq":
        key = _env_key("GROQ_API_KEY")
        url = "https://api.groq.com/openai/v1/chat/completions"
    else:
        key = _env_key("OPENAI_API_KEY")
        url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    reasoning = model_id.lower().startswith(("gpt-5", "o1", "o3", "o4"))

    def call(nar):
        msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": nar}]
        if reasoning:
            # reasoning models reject temperature and need a larger token budget
            body = {"model": model_id, "messages": msgs,
                    "max_completion_tokens": 3000, "reasoning_effort": "low"}
        else:
            body = {"model": model_id, "messages": msgs, "max_tokens": 20, "temperature": 0}
        d = _post(url, body, headers)
        return d["choices"][0]["message"]["content"] or ""
    return call


# ---------- log normalization (historical logs use arm-specific key names) ----------

_SIGN_KEYS = ["model_sign", "opus_sign", "gpt55_sign", "parsed_sign", "sign"]
_CONF_KEYS = ["model_conf", "opus_conf", "gpt55_conf", "confidence", "conf"]


def _s2i(s):
    if isinstance(s, (int, float)):
        return int(s)
    return {"+": 1, "-": -1, "0": 0}.get(str(s), 0)


def _resolve_keys(sample, sign_key, conf_key):
    """Pick which log field holds this model's sign/conf, erroring on ambiguity."""
    if sign_key is None:
        present = [k for k in _SIGN_KEYS if k in sample]
        if not present:
            sys.exit("ERROR: no sign field found in log; pass --sign-key.")
        if len(present) > 1:
            sys.exit(f"ERROR: log carries multiple arm signs {present}; "
                     "this is a multi-model log — pass --sign-key (and --conf-key), "
                     f"e.g. --sign-key gpt55_sign --conf-key gpt55_conf.")
        sign_key = present[0]
    if conf_key is None:
        present = [k for k in _CONF_KEYS if k in sample]
        conf_key = present[0] if len(present) == 1 else None
    return sign_key, conf_key


def normalize_log(path, truth_lookup, sign_key=None, conf_key=None):
    """Read any historical/emitted log into normalized rows for scoring.

    truth_lookup: tag -> (battery, truth_sign, llama_sign, grounded_sign) from build_cases,
    used to backfill truth/grounded/llama for logs that don't carry them (e.g. the llama logs).
    For a multi-model log (e.g. the council log has opus_sign AND gpt55_sign) pass sign_key
    explicitly so the right arm is scored.
    """
    raw = [json.loads(x) for x in open(path) if x.strip()]
    if not raw:
        sys.exit(f"ERROR: {path} is empty.")
    sign_key, conf_key = _resolve_keys(raw[0], sign_key, conf_key)
    rows = []
    for d in raw:
        tag = d.get("tag") or (f'{d["archetype"]}' if "archetype" in d else None)
        if tag is None:
            continue
        sign = _s2i(d.get(sign_key))
        conf = d.get(conf_key) if conf_key else None
        battery = d.get("battery")
        truth = d.get("truth_sign")
        llama = d.get("llama_sign")
        grounded = d.get("grounded_sign")
        if truth is None and tag in truth_lookup:
            battery, truth, llama, grounded = truth_lookup[tag]
        rows.append(dict(
            tag=tag, battery=battery,
            cell_type=d.get("cell_type") or cell_type(tag, battery or ""),
            model_sign=sign, model_conf=(float(conf) if conf is not None else None),
            truth_sign=_s2i(truth), llama_sign=_s2i(llama), grounded_sign=_s2i(grounded)))
    return rows


def _truth_lookup(cases):
    """tag -> (battery, truth, llama, grounded). GNCE log tags lack the seed suffix used in cases."""
    lut = {}
    for c in cases:
        lut[c["tag"]] = (c["battery"], c["truth_sign"], c["llama_sign"], c["grounded_sign"])
        base = c["tag"].split("|")[0]  # e.g. GNCE archetype without |sNNN
        lut.setdefault(base, (c["battery"], c["truth_sign"], c["llama_sign"], c["grounded_sign"]))
    return lut


def run_live(model_id, data_dir):
    """Call the model once per unique narrative, return normalized rows + emit a fresh log."""
    cases = build(data_dir)
    call = make_caller(model_id)
    cache = {}
    rows = []
    log_rows = []
    for i, c in enumerate(cases):
        nar = c["narrative"]
        if nar not in cache:
            for attempt in range(3):
                try:
                    cache[nar] = call(nar)
                    break
                except Exception as e:  # noqa: BLE001 - research runner, surface + retry
                    if attempt == 2:
                        raise
                    print(f"  retry {attempt+1} ({type(e).__name__})", file=sys.stderr)
                    time.sleep(1.0)
            time.sleep(0.3)
        raw = cache[nar]
        sign, conf = parse_answer(raw)
        rows.append(dict(
            tag=c["tag"], battery=c["battery"],
            cell_type=cell_type(c["tag"], c["battery"]),
            model_sign=sign, model_conf=conf,
            truth_sign=c["truth_sign"], llama_sign=c["llama_sign"],
            grounded_sign=c["grounded_sign"]))
        log_rows.append(dict(
            tag=c["tag"], battery=c["battery"], narrative=nar, model=model_id,
            raw=raw, model_sign=sign, model_conf=conf,
            cell_type=cell_type(c["tag"], c["battery"]),
            truth_sign=c["truth_sign"], llama_sign=c["llama_sign"],
            grounded_sign=c["grounded_sign"]))
        print(f'{i+1:2d}/{len(cases)} {c["battery"]:6s} {c["tag"]:30s} '
              f'{model_id}={sign:+d} conf={conf} | truth={c["truth_sign"]:+d}')
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", model_id)
    logpath = os.path.join(HERE, f"log_{slug}.jsonl")
    with open(logpath, "w") as f:
        for r in log_rows:
            f.write(json.dumps(r) + "\n")
    print(f"WROTE {logpath} ({len(log_rows)} rows; {len(cache)} unique narratives called)")
    return rows


def main():
    ap = argparse.ArgumentParser(
        description="Re-run the sealed AMBDOM+GNCE battery for a named model and emit a scorecard.")
    ap.add_argument("--model", required=True,
                    help="model id, e.g. claude-opus-4-8, gpt-5.5, llama-3.3-70b-versatile")
    ap.add_argument("--arm", choices=["translator", "narrator"], default="narrator",
                    help="role the model would fill (words-only). The PREDICTOR is always "
                         "grounded and is never an LLM arm.")
    ap.add_argument("--score-only", action="store_true",
                    help="do NOT call any API; score an existing log (dry / offline).")
    ap.add_argument("--from-log", default=None,
                    help="path to an existing *_llm_log.jsonl to score with --score-only.")
    ap.add_argument("--sign-key", default=None,
                    help="sign field to read from a multi-model log (e.g. gpt55_sign).")
    ap.add_argument("--conf-key", default=None,
                    help="confidence field for a multi-model log (e.g. gpt55_conf).")
    ap.add_argument("--data-dir", default=os.path.join(HERE, "results"),
                    help="dir with the sealed result JSON + llama logs (default: ./results).")
    ap.add_argument("--out-dir", default=HERE, help="where to write the scorecard.")
    args = ap.parse_args()

    import scorecard as sc_mod

    if args.score_only:
        if not args.from_log:
            ap.error("--score-only requires --from-log <path>")
        cases = build(args.data_dir)
        rows = normalize_log(args.from_log, _truth_lookup(cases),
                             sign_key=args.sign_key, conf_key=args.conf_key)
        print(f"[score-only] {len(rows)} rows from {args.from_log} — NO network call made.")
    else:
        rows = run_live(args.model, args.data_dir)

    sc = sc_mod.score(rows, args.model, arm=args.arm)
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", args.model)
    md_path = os.path.join(args.out_dir, f"SCORECARD_{slug}.md")
    json_path = os.path.join(args.out_dir, f"scorecard_{slug}.json")
    with open(md_path, "w") as f:
        f.write(sc_mod.to_markdown(sc))
    with open(json_path, "w") as f:
        json.dump(sc, f, indent=2)

    fg = sc["gates"]["flip_ceiling"]
    print(f'\n=== {args.model} ({args.arm}) ===')
    print(f'  flip-ceiling: {fg["verdict"]} (clean-flip acc {fg["clean_flip_acc"]:.2f})')
    print(f'  direction:    {sc["gates"]["direction"]["stance"]} '
          f'(index {sc["gates"]["direction"]["optimism_index"]:+.2f})')
    print(f'  calibration:  {sc["gates"]["calibration"]["verdict"]}')
    print(f'  ADOPT AS NARRATOR: {sc["adopt_as_narrator"]}')
    print(f'  wrote {md_path}')
    print(f'  wrote {json_path}')


if __name__ == "__main__":
    main()

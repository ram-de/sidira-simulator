"""Scoring for the model-robustness harness.

Consumes a list of NORMALIZED rows and emits (a) a machine-readable dict and
(b) a Markdown scorecard, reporting the three regression gates a new
translator/narrator model must pass before it is trusted in the pipeline:

    1. FLIP-CEILING  (load-bearing) — a words-only model must NOT beat chance on
       the magnitude-driven-flip slice. Only the grounded g-formula (which reads
       the withheld per-unit magnitudes from data) may clear 0.50 here. A
       words-only model that significantly beats chance is a RED FLAG (prose
       leakage / contamination / mis-sealed cases), not a capability win.
    2. DIRECTION — optimism vs pessimism. Characterises the model's stance:
       llama-style pro-feature optimism (over-predicts UP), Opus-style constant
       pessimism (over-predicts DOWN), or gpt-5.5-style balanced/abstaining.
    3. CALIBRATION — does stated confidence discriminate correct from wrong
       (and is ECE within a research tolerance)?

A normalized row is a dict with keys:
    tag, battery, cell_type, model_sign (∈ {-1,0,1}), model_conf (float|None),
    truth_sign, llama_sign, grounded_sign.
"""

import math

# --- gate thresholds (research tolerances; tune deliberately, never to a result) ---
FLIP_CEILING = 0.50          # structural chance ceiling on magnitude-flip cells
FLIP_ALPHA = 0.05            # one-sided binomial significance for "beats chance"
EXPECTED_CLEAN_FLIP = 12     # full clean-flip coverage (DISAGREE-WIDE + DISAGREE-NARROW)
DIRECTION_BALANCED_BAND = 0.34   # |optimism index| <= band => balanced stance
ECE_TOLERANCE = 0.20         # loose research ECE bound


def _binom_sf(k, n, p):
    """P(X >= k) for X~Binom(n,p). One-sided upper-tail, exact."""
    if n == 0:
        return float("nan")
    k = max(k, 0)
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _acc(rows, key="model_sign"):
    """Directional sign accuracy on scored (non-null-truth) cells."""
    nn = [r for r in rows if r["truth_sign"] != 0]
    c = sum(1 for r in nn if r[key] == r["truth_sign"])
    return c, len(nn), (c / len(nn) if nn else float("nan"))


def _tally(rows):
    up = sum(1 for r in rows if r["model_sign"] == 1)
    down = sum(1 for r in rows if r["model_sign"] == -1)
    unsure = sum(1 for r in rows if r["model_sign"] == 0)
    return up, down, unsure


def _calibration(rows):
    """Brier, ECE, and mean-confidence-when-correct vs wrong over scored cells with conf."""
    scored = [r for r in rows
              if r["truth_sign"] != 0 and r.get("model_conf") is not None
              and r["model_sign"] != 0]
    n = len(scored)
    if n == 0:
        return dict(n=0, brier=None, ece=None, mean_conf_correct=None,
                    mean_conf_wrong=None, discriminates=None)
    correct = [1 if r["model_sign"] == r["truth_sign"] else 0 for r in scored]
    confs = [float(r["model_conf"]) for r in scored]
    brier = sum((c - y) ** 2 for c, y in zip(confs, correct)) / n
    # 5-bin ECE
    bins = [[] for _ in range(5)]
    for conf, y in zip(confs, correct):
        idx = min(int(conf * 5), 4)
        bins[idx].append((conf, y))
    ece = 0.0
    for b in bins:
        if not b:
            continue
        avg_conf = sum(c for c, _ in b) / len(b)
        avg_acc = sum(y for _, y in b) / len(b)
        ece += (len(b) / n) * abs(avg_conf - avg_acc)
    cc = [conf for conf, y in zip(confs, correct) if y == 1]
    cw = [conf for conf, y in zip(confs, correct) if y == 0]
    mcc = sum(cc) / len(cc) if cc else None
    mcw = sum(cw) / len(cw) if cw else None
    discriminates = None
    if mcc is not None and mcw is not None:
        discriminates = mcc >= mcw
    return dict(n=n, brier=brier, ece=ece, mean_conf_correct=mcc,
                mean_conf_wrong=mcw, discriminates=discriminates)


def score(rows, model_id, arm="narrator"):
    """Return a machine-readable scorecard dict for a normalized row set."""
    amb = [r for r in rows if r["battery"] == "AMBDOM"]
    gnce = [r for r in rows if r["battery"] == "GNCE"]
    flip = [r for r in rows if r["cell_type"] == "FLIP"]
    clean_flip = [r for r in rows
                  if r["tag"].startswith("DISAGREE-WIDE")
                  or r["tag"].startswith("DISAGREE-NARROW")]
    guessable = [r for r in rows if r["cell_type"] == "GUESSABLE"]
    real = [r for r in rows if r["cell_type"] == "REAL"]
    scored = [r for r in rows if r["truth_sign"] != 0]

    slices = {}
    for name, rs in [("OVERALL", scored), ("AMBDOM", amb), ("GNCE", gnce),
                     ("clean_FLIP", clean_flip), ("all_FLIP", flip),
                     ("GUESSABLE", guessable), ("REAL", real)]:
        c, n, a = _acc(rs)
        gc, gn, ga = _acc(rs, "grounded_sign")
        lc, ln, la = _acc(rs, "llama_sign")
        slices[name] = dict(model_correct=c, n=n, model_acc=a,
                            grounded_acc=ga, llama_acc=la)

    # --- gate 1: flip ceiling ---
    cfc, cfn, cfa = _acc(clean_flip)
    p_beats = _binom_sf(cfc, cfn, FLIP_CEILING) if cfn else float("nan")
    beats_chance = (cfn > 0) and (cfa > FLIP_CEILING) and (p_beats < FLIP_ALPHA)
    # The load-bearing gate can only PASS with full clean-flip coverage; a partial log
    # (e.g. GNCE-only) must NOT silently pass without evaluating the decisive slice.
    if cfn < EXPECTED_CLEAN_FLIP:
        flip_verdict = "N/A"
        flip_note = (f"only {cfn}/{EXPECTED_CLEAN_FLIP} clean-flip cells scored — the "
                     "decisive slice is not covered; run the full battery. Not evaluable.")
    elif beats_chance:
        flip_verdict = "FLAG"
        flip_note = ("RED FLAG: beats chance via words alone — investigate leakage / "
                     "contamination / mis-sealed cases (only grounding should clear this)")
    else:
        flip_verdict = "PASS"
        flip_note = "does not beat chance on magnitude flips (expected for words-only)"
    flip_gate = dict(
        clean_flip_acc=cfa, correct=cfc, n=cfn, expected_n=EXPECTED_CLEAN_FLIP,
        chance=FLIP_CEILING, p_value_beats_chance=p_beats,
        beats_chance=beats_chance, verdict=flip_verdict, note=flip_note)

    # --- gate 2: direction (optimism vs pessimism) ---
    # Computed on the AMBIGUOUS AMBDOM prose, where the stance shows. GNCE is guessable
    # (every arm calls UP there), so including it washes the bias out.
    n_scored = len(scored)
    up_all, down_all, unsure_all = _tally(scored)
    amb_scored = [r for r in amb if r["truth_sign"] != 0]
    up, down, unsure = _tally(amb_scored)
    n_amb = len(amb_scored)
    opt_index = (up - down) / n_amb if n_amb else float("nan")
    abstain_rate = unsure / n_amb if n_amb else float("nan")
    if not (opt_index == opt_index):  # NaN guard (no AMBDOM cells)
        stance = "UNKNOWN"
    elif opt_index > DIRECTION_BALANCED_BAND:
        stance = "OPTIMIST"          # llama-like: over-predicts UP (pro-feature)
    elif opt_index < -DIRECTION_BALANCED_BAND:
        stance = "PESSIMIST"         # Opus-like: over-predicts DOWN
    else:
        stance = "BALANCED"          # split UP/DOWN
    abstain_note = " · abstain-heavy" if (abstain_rate == abstain_rate and abstain_rate >= 0.40) else ""
    dir_gate = dict(up=up, down=down, unsure=unsure, n_ambdom_scored=n_amb,
                    up_overall=up_all, down_overall=down_all, unsure_overall=unsure_all,
                    optimism_index=opt_index, abstain_rate=abstain_rate, stance=stance,
                    verdict="PASS" if stance == "BALANCED" else "FLAG",
                    note=f"{stance} on ambiguous prose (optimism index {opt_index:+.2f}"
                         f"{abstain_note}); narrator adoption is fine, but record the prior")

    # --- gate 3: calibration ---
    cal = _calibration(rows)
    cal_ok = None
    if cal["n"] > 0:
        cal_ok = bool(cal["discriminates"]) and (cal["ece"] is not None and cal["ece"] <= ECE_TOLERANCE)
    cal_gate = dict(**cal, tolerance_ece=ECE_TOLERANCE,
                    verdict=("PASS" if cal_ok else ("FLAG" if cal["n"] else "N/A")),
                    note=("confidence discriminates correct vs wrong and ECE within tolerance"
                          if cal_ok else
                          ("no confidence values in log" if cal["n"] == 0 else
                           "confidence does not discriminate or ECE over tolerance")))

    # narrator-adoption summary — the flip ceiling is the load-bearing gate
    safe = flip_gate["verdict"] == "PASS"
    return dict(
        model_id=model_id, arm=arm, n_cases=len(rows), n_scored=n_scored,
        slices=slices,
        gates=dict(flip_ceiling=flip_gate, direction=dir_gate, calibration=cal_gate),
        adopt_as_narrator=("YES" if safe else "REVIEW"),
        adopt_note=("Predictor stays GROUNDED regardless; this verdict concerns the "
                    "words-only translator/narrator role only. The flip ceiling is the "
                    "load-bearing gate: a narrator that beats it needs investigation."))


def _fmt(x, spec=".2f"):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return format(x, spec)


def to_markdown(sc):
    g = sc["gates"]
    fg, dg, cg = g["flip_ceiling"], g["direction"], g["calibration"]
    lines = []
    lines.append(f'# SCORECARD — {sc["model_id"]}  (arm: {sc["arm"]})')
    lines.append("")
    lines.append("Auto-generated by `run_battery.py` against the sealed AMBDOM + GNCE battery. "
                 "Grounded-sim and truth are read from the sealed result JSON and are NOT re-run; "
                 "only the LLM arm reflects this model.")
    lines.append("")
    lines.append(f'**Adopt as narrator: {sc["adopt_as_narrator"]}**  ·  '
                 f'cases {sc["n_cases"]}  ·  scored {sc["n_scored"]}')
    lines.append("")
    lines.append(f'> {sc["adopt_note"]}')
    lines.append("")
    lines.append("## Directional / magnitude accuracy per slice")
    lines.append("")
    lines.append("| slice | n | this model | grounded | llama (ref) |")
    lines.append("|---|---|---|---|---|")
    order = ["OVERALL", "AMBDOM", "GNCE", "clean_FLIP", "all_FLIP", "GUESSABLE", "REAL"]
    for name in order:
        s = sc["slices"][name]
        lines.append(f'| {name} | {s["n"]} | {_fmt(s["model_acc"])} '
                     f'({s["model_correct"]}/{s["n"]}) | {_fmt(s["grounded_acc"])} '
                     f'| {_fmt(s["llama_acc"])} |')
    lines.append("")
    lines.append("The **clean_FLIP** row is the magnitude-driven-flip slice — the decisive test. "
                 "Grounded should be ~1.00; any words-only model should sit at ~chance (0.50).")
    lines.append("")
    lines.append("## Gate 1 — FLIP CEILING (load-bearing)")
    lines.append("")
    lines.append(f'- clean-flip accuracy: **{_fmt(fg["clean_flip_acc"])}** '
                 f'({fg["correct"]}/{fg["n"]}), chance = {fg["chance"]:.2f}')
    lines.append(f'- one-sided binomial P(beats chance): {_fmt(fg["p_value_beats_chance"], ".4f")}')
    lines.append(f'- beats chance via words alone: **{fg["beats_chance"]}**')
    lines.append(f'- **verdict: {fg["verdict"]}** — {fg["note"]}')
    lines.append("")
    lines.append("## Gate 2 — DIRECTION (optimism vs pessimism)")
    lines.append("")
    lines.append("Measured on the ambiguous AMBDOM prose (where stance shows; GNCE is guessable).")
    lines.append(f'- AMBDOM scored (n={dg["n_ambdom_scored"]}): '
                 f'UP {dg["up"]} · DOWN {dg["down"]} · UNSURE {dg["unsure"]} '
                 f'(abstain rate {_fmt(dg["abstain_rate"])})')
    lines.append(f'- overall tally: UP {dg["up_overall"]} · DOWN {dg["down_overall"]} '
                 f'· UNSURE {dg["unsure_overall"]}')
    lines.append(f'- optimism index (UP−DOWN)/n: **{_fmt(dg["optimism_index"], "+.2f")}** '
                 f'→ **{dg["stance"]}**')
    lines.append(f'- **verdict: {dg["verdict"]}** — {dg["note"]}')
    lines.append("")
    lines.append("## Gate 3 — CALIBRATION")
    lines.append("")
    if cg["n"] == 0:
        lines.append("- no confidence values present in the log → calibration not evaluable.")
    else:
        lines.append(f'- scored-with-confidence cells: {cg["n"]}')
        lines.append(f'- Brier: {_fmt(cg["brier"], ".3f")} · ECE: {_fmt(cg["ece"], ".3f")} '
                     f'(tolerance {cg["tolerance_ece"]:.2f})')
        lines.append(f'- mean confidence — correct {_fmt(cg["mean_conf_correct"], ".3f")} '
                     f'vs wrong {_fmt(cg["mean_conf_wrong"], ".3f")} '
                     f'(discriminates: {cg["discriminates"]})')
    lines.append(f'- **verdict: {cg["verdict"]}** — {cg["note"]}')
    lines.append("")
    lines.append("## Adoption rule")
    lines.append("")
    lines.append("The **narrator/translator MAY upgrade** to a stronger model on overall/GUESSABLE "
                 "accuracy. The **predictor STAYS GROUNDED** — never swap an LLM in for the "
                 "grounded g-formula on the magnitude question. A narrator that clears the flip "
                 "ceiling is a red flag to investigate, not a reason to promote it to predictor.")
    lines.append("")
    return "\n".join(lines)

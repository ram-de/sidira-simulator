"""Feasibility-only consumer-side check: translate the producer pack into the
simulator PersonaPack, then exercise render_individual_row across sample_index.

Run with the simulator backend venv, pointing PYTHONPATH at the worktree source:
    PYTHONPATH=<worktree>/backend <main>/backend/.venv/bin/python consume_pack.py
"""
from __future__ import annotations

import json
from pathlib import Path

from sidira_simulator.services.persona_pack_translator import translate_producer_pack
from sidira_simulator.services.behavioral_profile import render_individual_row

HERE = Path(__file__).resolve().parent
producer = json.loads((HERE / "producer_pack.json").read_text())

pack = translate_producer_pack(producer, version="v_feasibility")
print(f"TRANSLATE OK: schema_version={pack.schema_version} "
      f"customer_id={pack.customer_id} n_personas={len(pack.personas)}")

for persona in pack.personas[:3]:
    print(f"\n=== {persona.id} ({persona.name}) ===")
    print(f"  centroid_full keys={list((persona.centroid_full or {}).keys())}")
    print(f"  feature_scale keys={list((persona.feature_scale or {}).keys())}")
    print(f"  n sample_rows={len(persona.sample_rows or [])}")
    seen = {}
    for idx in (0, 1, 2, 3):
        prof = render_individual_row(persona, idx)
        delta_sig = tuple(sorted((d.feature, round(d.z, 4)) for d in prof.deltas))
        seen[idx] = delta_sig
        print(f"  [sample_index={idx}] grounded={prof.grounded} "
              f"tier={prof.source_tier} n_deltas={len(prof.deltas)} "
              f"suppressed={prof.suppressed_count}")
        for d in prof.deltas:
            print(f"      - {d.feature}: z={d.z:+.3f} -> {d.line()}")
    distinct = len(set(seen.values()))
    print(f"  DISTINCT delta-signatures across idx 0-3: {distinct} of 4")

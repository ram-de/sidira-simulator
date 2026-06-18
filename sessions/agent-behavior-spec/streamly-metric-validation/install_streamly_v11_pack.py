"""STEP A1 (part 2) — translate the producer pack to the consumer PersonaPack and
install it as streamly_sample/personas/v_2, repointing `latest`.

Runs in the sidira-simulator venv (PYTHONPATH=backend). FICTIONAL data.
"""
from __future__ import annotations
import json
from pathlib import Path

from sidira_simulator.services.persona_pack_translator import translate_producer_pack

ROOT = Path("/Users/ram/Projects/sidira-simulator/.claude/worktrees/benchmark-gate-validation")
PRODUCER = ROOT / "sessions/agent-behavior-spec/streamly-metric-validation/streamly_producer_pack_v11.json"
PERSONAS_DIR = ROOT / "local-artifacts/customers/streamly_sample/personas"
VERSION = "v_2"


def main():
    producer = json.loads(PRODUCER.read_text())
    pack = translate_producer_pack(producer, version=VERSION)
    print(f"translated: version={pack.version} customer={pack.customer_id} "
          f"schema={pack.schema_version} n={len(pack.personas)} stability={pack.stability_score}")

    # quad presence on the CONSUMER pack
    for p in pack.personas:
        quad = bool(p.centroid_full) and bool(p.feature_scale) and bool(p.sample_rows) and (p.posterior_mean is not None)
        seeds = "set" if p.behavioral_seeds is not None else "None(fallback)"
        print(f"  {p.id:>5} | {p.name!r:40} quad={'OK' if quad else 'MISSING'} "
              f"behavioral_seeds={seeds} centroid_features={len(p.centroid_features)}")

    out_dir = PERSONAS_DIR / VERSION
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "persona_pack.json"
    out_path.write_text(pack.model_dump_json(indent=2))
    print(f"wrote {out_path}")

    (PERSONAS_DIR / "latest").write_text(VERSION)
    print(f"repointed latest -> {VERSION}")


if __name__ == "__main__":
    main()

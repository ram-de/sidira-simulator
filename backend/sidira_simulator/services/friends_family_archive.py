"""Friends-&-Family validation game → DERIVED v1.1 persona pack (ticket #443).

The F&F validation game (``sessions/ff-validation-game/app``) profiles players
through pre-treatment "rooms" and writes Table A (``player_features``) behind a
two-table leakage firewall: the arm + outcome live in a SEPARATE sealed table
the pipeline never sees. The simulated audience for that game's micro-A/Bs is a
v1.1 persona pack DERIVED from Table A via the ``sidira-personas`` GMM pipeline —
the same discipline as the Hillstrom / Cookie Cats RCT packs
(``services.hillstrom_archive`` / ``services.cookiecats_archive``).

Like those packs it carries the v1.1 quantitative quad (``centroid_full`` /
``feature_scale`` / ``sample_rows`` / ``posterior_mean``) so it EXERCISES the
``render_individual_row`` (``individual_row_synthetic``) tier, and — unlike the
no-LLM Hillstrom/Cookie Cats builds — it is built with ``require_llm=True`` so
every persona ALSO carries non-null ``behavioral_seeds`` (the five identity-draw
pools the simulator's ``identity_seed`` service reads). That is what keeps a run
from logging ``identity_seed fallback active`` for this pack.

⚠️  SYNTHETIC PROVENANCE (ticket #443). The COMMITTED pack
(``adapters/friends_family_panel_v1.json``) is currently built from a SYNTHETIC
``player_features.csv`` (``config/friends_family.yaml`` → ``source.path``), not
from real players — it exists so the data → pack → loader path is wired and
testable BEFORE any friend/family member has played. When real players exist,
the real Table A export replaces the source and the pack is rebuilt from THAT at
run time. The committed JSON is statistics (cluster centroids + privacy-clean GMM
draws), not raw rows, so it is safe to redistribute either way.

The build is GATED (refuses under pytest / CI) for the SAME reason as the
Hillstrom build: it imports the heavy ML stack (pandas + ``sidira-personas``,
intentionally absent from the API image) and is a deliberate, reproducible
offline step, never a test/CI side effect. Tests validate the COMMITTED pack.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# The pre-registered panel id (the PersonaPack.version, reported as panel_id so a
# run is traceable to the exact population). Versioned independently of the
# on-disk filename, mirroring the Hillstrom / Cookie Cats convention.
FRIENDS_FAMILY_PANEL_VERSION = "friends-family-validation-v1"

# The frozen sidira-personas pipeline config lives in the producer repo
# (single source of truth for the feature-group mapping + k_range / stability):
#   ~/Projects/sidira-personas/config/friends_family.yaml
# The build reads it from there; override with FF_PERSONAS_CONFIG for a custom
# location. The synthetic source CSV path inside that config is relative to the
# personas repo root (``fixtures/friends_family_synthetic_features.csv``).
_DEFAULT_PERSONAS_REPO = Path.home() / "Projects" / "sidira-personas"


def _resolve_config_path() -> Path:
    override = os.environ.get("FF_PERSONAS_CONFIG")
    if override:
        return Path(override)
    return _DEFAULT_PERSONAS_REPO / "config" / "friends_family.yaml"


def build_friends_family_panel_pack(
    *,
    config_path: str | Path | None = None,
    personas_repo: str | Path | None = None,
):
    """Build the DERIVED F&F v1.1 persona pack from the configured source (gated).

    Reads ``config/friends_family.yaml`` (in the ``sidira-personas`` repo), loads
    its local source CSV (Table A — pre-treatment features ONLY), runs the GMM
    pipeline with ``require_llm=True`` (so personas carry both the v1.1 quad AND
    non-null ``behavioral_seeds``), and translates the producer pack into the
    simulator's :class:`~sidira_simulator.schemas.persona.PersonaPack`. Returns the
    validated pack; the caller writes the JSON to
    ``adapters/friends_family_panel_v1.json``.

    GATED: refuses under pytest / CI (imports the heavy ML stack + makes live LLM
    naming calls). Raises RuntimeError under pytest / CI, if ``sidira-personas`` is
    not installed, or if no LLM naming provider is reachable (``require_llm``).
    """
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(
            "build_friends_family_panel_pack imports the heavy ML stack and makes "
            "live LLM naming calls; it must not run under pytest / CI. The committed "
            "pack (adapters/friends_family_panel_v1.json) is what tests validate; "
            "rebuild it offline with this function when the source / mapping changes."
        )

    try:
        import pandas as pd
        import yaml

        from sidira_personas import run_pipeline
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "sidira-personas (+ pandas + pyyaml) not installed — install it "
            "(Python 3.11+) to rebuild the F&F persona pack: `python3.11 -m pip "
            "install -e ~/Projects/sidira-personas`. Run with the personas venv so "
            "the behavioral_seeds emitter (#18) is present."
        ) from exc

    from sidira_simulator.services.persona_pack_translator import translate_producer_pack

    cfg_path = Path(config_path) if config_path else _resolve_config_path()
    cfg = yaml.safe_load(cfg_path.read_text())

    # The config's source.path is relative to the personas repo root.
    repo = Path(personas_repo) if personas_repo else cfg_path.parent.parent
    src = cfg["source"]
    if src.get("type") != "local":
        raise RuntimeError(
            f"F&F build expects a local CSV source; got source.type={src.get('type')!r}"
        )
    csv_path = (repo / src["path"]).resolve()
    if not csv_path.exists():
        raise RuntimeError(
            f"source CSV not found: {csv_path}. Generate the synthetic features first "
            "(sessions/ff-validation-game/app: `node scripts/gen_synthetic_features.js "
            f"60 {csv_path}`), or export real Table A."
        )

    df = pd.read_csv(csv_path)
    logger.info("Building F&F panel pack from %d rows (%s)", len(df), csv_path.name)

    result = run_pipeline(
        df,
        cfg,
        run_id=FRIENDS_FAMILY_PANEL_VERSION,
        require_llm=True,
    )

    from dataclasses import asdict

    producer_pack = asdict(result.pack)
    pack = translate_producer_pack(producer_pack, version=FRIENDS_FAMILY_PANEL_VERSION)
    logger.info(
        "Built F&F pack: k=%d, %d personas, stability=%.3f",
        result.pack.k_selected,
        len(pack.personas),
        pack.stability_score,
    )
    return pack, result


def write_friends_family_panel_pack(
    dest_path: str | Path,
    *,
    config_path: str | Path | None = None,
    personas_repo: str | Path | None = None,
) -> Path:
    """Build + serialize the F&F panel pack to ``dest_path`` (gated).

    The reproducible offline build entry point: regenerates the committed
    ``adapters/friends_family_panel_v1.json``. Refuses under pytest / CI via
    :func:`build_friends_family_panel_pack`. Returns the path written.
    """
    pack, _ = build_friends_family_panel_pack(
        config_path=config_path, personas_repo=personas_repo
    )
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(pack.model_dump_json(indent=2))
    logger.info("Wrote F&F panel pack to %s", dest)
    return dest

"""Tests for services.identity_seed (Phase 2.5, issue #5).

Covers determinism, variance across sample indices, persona-pool usage,
v1.0 fallback with WARN, distinctness threshold, cross-process determinism,
and the explicit prose=None assertion.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap

import pytest

from pythia_simulator.schemas.persona import BehavioralSeedSchema, Persona
from pythia_simulator.services import identity_seed as identity_seed_module
from pythia_simulator.services.identity_seed import (
    _DEFAULT_BEHAVIORAL_SEEDS,
    draw_identity_seed,
)


def _rich_seeds() -> BehavioralSeedSchema:
    """A pool deep enough that 50 draws should yield >=45 distinct tuples."""
    return BehavioralSeedSchema(
        age_bands=["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
        locale_bands=[
            "sf_bay",
            "nyc_metro",
            "chicago",
            "austin",
            "seattle",
            "miami",
            "denver",
            "boston",
        ],
        tenure_bands=["<3mo", "3-12mo", "1-3y", "3-5y", "5y+"],
        current_state_pool=[
            f"state_{i}" for i in range(12)
        ],
        recent_gripe_pool=[
            f"gripe_{i}" for i in range(12)
        ],
    )


def _persona(pid: str = "p_test", seeds: BehavioralSeedSchema | None = None) -> Persona:
    return Persona(id=pid, name="P", description="d", behavioral_seeds=seeds)


@pytest.fixture(autouse=True)
def _reset_fallback_warned():
    """The fallback-warned set is module-level; reset between tests."""
    identity_seed_module._fallback_warned.clear()
    yield
    identity_seed_module._fallback_warned.clear()


def test_seed_is_deterministic_for_same_inputs() -> None:
    p = _persona(seeds=_rich_seeds())
    a = draw_identity_seed(p, sample_index=3, run_seed=42)
    b = draw_identity_seed(p, sample_index=3, run_seed=42)
    assert a == b


def test_seed_differs_across_sample_indices() -> None:
    """Adjacent sample indices can collide on individual fields; assert that
    across a small batch of pairs the average diff is >=3/5, which is what the
    plan calls for ('at least 3/5 fields differ; allowing rare collisions')."""
    p = _persona(seeds=_rich_seeds())
    fields = ("age_band", "locale_band", "tenure_band", "current_state", "recent_gripe")
    pairs = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    total_diffs = 0
    for i, j in pairs:
        a = draw_identity_seed(p, sample_index=i, run_seed=42)
        b = draw_identity_seed(p, sample_index=j, run_seed=42)
        total_diffs += sum(1 for f in fields if getattr(a, f) != getattr(b, f))
    avg = total_diffs / len(pairs)
    assert avg >= 3, f"expected avg >=3 fields differing across {len(pairs)} pairs, got {avg}"


def test_seed_uses_persona_pools_when_present() -> None:
    seeds = _rich_seeds()
    p = _persona(seeds=seeds)
    s = draw_identity_seed(p, sample_index=7, run_seed=123)
    assert s.age_band in seeds.age_bands
    assert s.locale_band in seeds.locale_bands
    assert s.tenure_band in seeds.tenure_bands
    assert s.current_state in seeds.current_state_pool
    assert s.recent_gripe in seeds.recent_gripe_pool


def test_seed_falls_back_to_default_schema_when_v1_pack(capsys) -> None:
    p = _persona(pid="p_v10_alpha", seeds=None)
    s = draw_identity_seed(p, sample_index=0, run_seed=1)
    assert s.age_band in _DEFAULT_BEHAVIORAL_SEEDS.age_bands
    assert s.locale_band in _DEFAULT_BEHAVIORAL_SEEDS.locale_bands
    assert s.tenure_band in _DEFAULT_BEHAVIORAL_SEEDS.tenure_bands
    assert s.current_state in _DEFAULT_BEHAVIORAL_SEEDS.current_state_pool
    assert s.recent_gripe in _DEFAULT_BEHAVIORAL_SEEDS.recent_gripe_pool

    # The named WARN line is the user-visible mitigation for FM-2.
    captured = capsys.readouterr().out
    assert "cross-persona variance degraded" in captured
    assert "p_v10_alpha" in captured
    assert p.id in identity_seed_module._fallback_warned

    # Second call for same persona must NOT re-warn.
    draw_identity_seed(p, sample_index=1, run_seed=1)
    second = capsys.readouterr().out
    assert "cross-persona variance degraded" not in second


def test_50_seeds_for_one_persona_produce_distinct_tuples() -> None:
    p = _persona(seeds=_rich_seeds())
    seeds = [
        draw_identity_seed(p, sample_index=i, run_seed=2026)
        for i in range(50)
    ]
    tuples = {
        (s.age_band, s.locale_band, s.tenure_band, s.current_state, s.recent_gripe)
        for s in seeds
    }
    assert len(tuples) >= 45, f"expected >=45 distinct tuples out of 50, got {len(tuples)}"


def test_cross_process_determinism(tmp_path) -> None:
    """A fresh Python process must produce the same IdentitySeed.

    Catches anyone "simplifying" the sha256 path to random.Random(str), which
    has implementation-defined string hashing across Python versions.
    """
    script = textwrap.dedent(
        """
        import json
        from pythia_simulator.schemas.persona import BehavioralSeedSchema, Persona
        from pythia_simulator.services.identity_seed import draw_identity_seed

        seeds = BehavioralSeedSchema(
            age_bands=["18-24", "25-34", "35-44"],
            locale_bands=["sf_bay", "nyc_metro"],
            tenure_bands=["<3mo", "1-3y"],
            current_state_pool=["a", "b", "c"],
            recent_gripe_pool=["x", "y", "z"],
        )
        p = Persona(id="p_test", name="P", description="d", behavioral_seeds=seeds)
        s = draw_identity_seed(p, sample_index=5, run_seed=99)
        print(s.model_dump_json())
        """
    )
    script_path = tmp_path / "subproc.py"
    script_path.write_text(script)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    subproc_seed = json.loads(result.stdout.strip().splitlines()[-1])

    seeds = BehavioralSeedSchema(
        age_bands=["18-24", "25-34", "35-44"],
        locale_bands=["sf_bay", "nyc_metro"],
        tenure_bands=["<3mo", "1-3y"],
        current_state_pool=["a", "b", "c"],
        recent_gripe_pool=["x", "y", "z"],
    )
    p = _persona(seeds=seeds)
    in_proc = draw_identity_seed(p, sample_index=5, run_seed=99).model_dump()
    assert subproc_seed == in_proc


def test_demo_persona_overrides_constrain_lex_to_new_tenure() -> None:
    """#78: identity_seed for `lex_new_explorer` (persona description says
    "signed up six weeks ago") must NEVER draw tenure_band="veteran (3y+)".
    Sweep 20 sample indices to make the assertion robust against draw luck."""
    p = _persona(pid="lex_new_explorer", seeds=None)
    drawn = [
        draw_identity_seed(p, sample_index=i, run_seed=12345).tenure_band
        for i in range(20)
    ]
    # Every draw lands in the per-persona override pool ({new (<3mo)} only)
    assert set(drawn) == {"new (<3mo)"}, f"got unexpected tenure bands: {set(drawn)}"


def test_demo_persona_overrides_constrain_maya_to_long_tenure() -> None:
    """#78 mirror: `maya_late_night_premium` (32yo DashPass subscriber) must
    NEVER draw tenure_band="new (<3mo)" or "early (3-12mo)" — the persona
    description doesn't support those."""
    p = _persona(pid="maya_late_night_premium", seeds=None)
    drawn = [
        draw_identity_seed(p, sample_index=i, run_seed=98765).tenure_band
        for i in range(20)
    ]
    allowed = {"established (1-3y)", "veteran (3y+)"}
    assert set(drawn).issubset(allowed), (
        f"maya should never draw new/early tenure; got {set(drawn) - allowed}"
    )


def test_schema_with_overrides_passes_through_unknown_persona_id() -> None:
    """#79 codex round-1 P2: deterministic helper-level assertion that an
    unknown persona_id returns the default schema unchanged. Stronger than
    the probabilistic draw test below — directly compares schemas, not
    draws."""
    from pythia_simulator.services.identity_seed import (
        _DEFAULT_BEHAVIORAL_SEEDS,
        _schema_with_overrides,
    )

    result = _schema_with_overrides("not_a_real_persona_id", _DEFAULT_BEHAVIORAL_SEEDS)
    assert result.age_bands == _DEFAULT_BEHAVIORAL_SEEDS.age_bands
    assert result.locale_bands == _DEFAULT_BEHAVIORAL_SEEDS.locale_bands
    assert result.tenure_bands == _DEFAULT_BEHAVIORAL_SEEDS.tenure_bands
    assert result.current_state_pool == _DEFAULT_BEHAVIORAL_SEEDS.current_state_pool
    assert result.recent_gripe_pool == _DEFAULT_BEHAVIORAL_SEEDS.recent_gripe_pool


def test_persona_without_override_uses_default_pools_unchanged() -> None:
    """A persona not in the demo override table (e.g. a customer-supplied
    persona with no behavioral_seeds) falls through to _DEFAULT_BEHAVIORAL_SEEDS
    untouched. Sanity: the override table is opt-in per persona_id, not a
    global narrowing of the defaults."""
    p = _persona(pid="some_unknown_persona_id", seeds=None)
    drawn = [
        draw_identity_seed(p, sample_index=i, run_seed=42).tenure_band
        for i in range(40)
    ]
    # 40 draws from a 4-element pool — should hit at least 3 of the 4
    # default tenure bands.
    assert len(set(drawn)) >= 3, (
        f"override leaked: unknown persona drew only {set(drawn)}, "
        f"expected diversity from _DEFAULT_BEHAVIORAL_SEEDS.tenure_bands"
    )


def test_persona_with_pack_supplied_seeds_skips_override() -> None:
    """#78 invariant: when a persona ships its own behavioral_seeds (v1.1
    packs, eventually), the simulator-side override table is NOT consulted.
    Overrides are a stopgap for v1.0; pack-supplied schemas are authoritative."""
    # Use lex_new_explorer's persona_id (which IS in the override table) but
    # supply EXPLICIT behavioral_seeds with veteran-only tenure. The override
    # would constrain to "new" — but the pack-supplied schema must win.
    seeds = BehavioralSeedSchema(
        age_bands=["55-64"],
        locale_bands=["urban_us"],
        tenure_bands=["veteran (3y+)"],
        current_state_pool=["weekend, no rush, browsing options"],
        recent_gripe_pool=["last order arrived cold"],
    )
    p = _persona(pid="lex_new_explorer", seeds=seeds)
    s = draw_identity_seed(p, sample_index=0, run_seed=1)
    assert s.tenure_band == "veteran (3y+)"  # pack wins, override skipped
    assert s.age_band == "55-64"


def test_prose_is_none_in_v1() -> None:
    """Explicit assertion: prose synthesis is a follow-up PR.

    Insurance against a future PR silently shipping LLM call infra here.
    """
    p_with = _persona(seeds=_rich_seeds())
    p_without = _persona(pid="p_v10", seeds=None)
    assert draw_identity_seed(p_with, 0, 1).prose is None
    assert draw_identity_seed(p_without, 0, 1).prose is None

"""Feature Pack schema — produced by sidira-crawler, consumed here.

Duplicated from sidira-crawler until pythia-schemas package lands.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ComponentState(BaseModel):
    name: str
    text: str | None = Field(default=None, description="Product copy shown in this state")
    annotations: dict[str, str] = Field(default_factory=dict)


class Component(BaseModel):
    id: str
    role: str
    states: list[ComponentState] = Field(default_factory=list)
    text: str | None = Field(default=None, description="Product copy displayed by this component")
    visible_to_roles: list[str] | None = None


class Transition(BaseModel):
    trigger: str
    from_screen: str
    to_screen: str
    role_gated: list[str] | None = None
    # Mirrors sidira-crawler#14: True when this is a boundary edge whose target
    # screen lives in a *different* capability (the clustering split the user's
    # observed path across a seam). ``to_screen`` still names the external
    # target. Optional and back-compat — packs predating the crawler change omit
    # it and default to an in-capability hop.
    external: bool = False


class Screen(BaseModel):
    id: str
    name: str
    role: str | None = None
    components: list[Component] = Field(default_factory=list)


class ReverseFigma(BaseModel):
    screens: list[Screen] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)


class Capability(BaseModel):
    name: str
    surfaces: list[str]
    roles: list[str]
    entry_points: list[str]
    reverse_prd: str
    reverse_figma: ReverseFigma
    implicit_metric: str | None = None
    # Mirrors sidira-crawler#18: the second-level grouping label (capability →
    # domain). Optional and back-compat — packs predating the crawler change omit
    # it, and the Library buckets a domainless capability under "Ungrouped".
    domain: str | None = None


class FeaturePackManifest(BaseModel):
    customer_id: str
    snapshot_version: str
    generated_at: datetime
    schema_version: Literal["1.0"] = "1.0"
    capabilities: list[str]
    # Persisted grouping index (capability name → domain) written by the crawler
    # (sidira-crawler#18). The per-capability artifacts carry only the
    # reverse-PRD/Figma, so this map is how the summary endpoint reads `domain`
    # in a single manifest read. Optional/back-compat: empty on older packs.
    capability_domains: dict[str, str] = Field(default_factory=dict)
    crawl_metadata: dict[str, str] = Field(default_factory=dict)


class CapabilityRecord(BaseModel):
    """A single capability plus the provenance of the pack it was read from.

    Carries the snapshot version and capture timestamp alongside the capability
    so the Library's record header (#207, DESIGN.md §7.6) is sourced from the
    SAME read that served the body. The pack provenance and the capability are
    both pinned to one `snapshot_version`, so a crawl that flips the `latest`
    pointer mid-request can't label a record with a different snapshot's date.
    """

    snapshot_version: str
    generated_at: datetime
    capability: Capability


class CapabilitySummary(BaseModel):
    """A capability projected to just its name + roles — no reverse-PRD/Figma body.

    The names-only :class:`FeaturePackManifest` can't drive a group-by-role view,
    and shipping every full :class:`Capability` to the Library browse page just to
    read `roles` would be wasteful. This is the lightweight projection in between.
    `domain` (#244) rides along from the manifest's `capability_domains` map so the
    browse page can also group by domain; ``None`` means the capability is ungrouped.
    """

    name: str
    roles: list[str]
    domain: str | None = None


class FeaturePackSummary(BaseModel):
    """The latest pack as `{name, roles}` rows plus its provenance.

    Mirrors :class:`FeaturePackManifest` (same version + timestamp header) but
    carries per-capability `roles`, so the Library browse page (#207) gets names,
    roles, version and date from a single fetch and can group by role.
    """

    customer_id: str
    snapshot_version: str
    generated_at: datetime
    schema_version: Literal["1.0"] = "1.0"
    capabilities: list[CapabilitySummary]

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


class FeaturePackManifest(BaseModel):
    customer_id: str
    snapshot_version: str
    generated_at: datetime
    schema_version: Literal["1.0"] = "1.0"
    capabilities: list[str]
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

/**
 * Typed API client.
 *
 * Run `npm run gen-types` against a running backend to refresh `./api-types.ts`
 * from the FastAPI OpenAPI export. Types here import from `./api-types`.
 */

import type { components } from "./api-types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

// ── Re-exported schema types for page imports ──────────────────────────

// #214 adds an API-side `archived` flag the checked-in api-types.ts predates (the
// generated file is stale — same caveat as Capability/CrawlSummary below). The
// crawler never writes it; the listing route sets it from the archive marker so the
// Library labels a version and offers the right action from fact. Optional so a
// stale/older response (no field) reads as not-archived. Collapse to the bare
// generated type once api-types.ts is regenerated against the live backend.
export type FeaturePackManifest = components["schemas"]["FeaturePackManifest"] & {
  archived?: boolean;
};
export type ReverseFigma = components["schemas"]["ReverseFigma"];
export type Screen = components["schemas"]["Screen"];
export type FigmaComponent = components["schemas"]["Component"];
export type Transition = components["schemas"]["Transition"];
// The single-capability schema isn't in the committed generated types — the
// checked-in api-types.ts predates several backend endpoints (the crawl routes
// are hand-typed here too, see CrawlCapability below). Mirror the backend
// Capability model from its generated sub-schemas; collapse to
// components["schemas"]["Capability"] whenever api-types.ts is regenerated.
export type Capability = {
  name: string;
  surfaces: string[];
  roles: string[];
  entry_points: string[];
  reverse_prd: string;
  reverse_figma: ReverseFigma;
  implicit_metric?: string | null;
};
// The capability detail read wraps the capability in its pack provenance so the
// record header's snapshot + capture timestamp come from the SAME read that
// served the body (no second `latest` lookup that could race a crawl publish).
export type CapabilityRecord = {
  snapshot_version: string;
  generated_at: string;
  capability: Capability;
};
// Lightweight per-capability projection (name + roles + domain, no PRD/Figma
// body) so the Library browse page can group by role or domain from a single
// fetch. Hand-mirrored like Capability above; collapse to components["schemas"]
// when api-types.ts is regenerated. `domain` is null when the capability is
// ungrouped (pack predates sidira-crawler#18, or its domain pass degraded).
export type CapabilitySummary = {
  name: string;
  roles: string[];
  domain?: string | null;
};
export type FeaturePackSummary = {
  customer_id: string;
  snapshot_version: string;
  generated_at: string;
  schema_version: "1.0";
  capabilities: CapabilitySummary[];
};
export type PersonaSummary = components["schemas"]["PersonaSummary"];
export type ActivePersonasResponse = components["schemas"]["ActivePersonasResponse"];
// Full persona-pack detail shapes for the Library's pack detail page (#207).
// `GET /personas` returns the wizard-shaped PersonaSummary (id/name/weight only);
// the detail page needs the full bodies — description, JTBD, behavioral snapshot —
// which only `GET /persona-packs/{id}` carries. Hand-mirrored like Capability
// above (api-types.ts is stale); collapse to components["schemas"] when it's
// regenerated.
export type WeightSchemes = {
  head_count: Record<string, number>;
  order_weighted?: Record<string, number> | null;
  revenue_weighted?: Record<string, number> | null;
};
export type Persona = {
  id: string;
  name: string;
  description: string;
  jtbd?: string | null;
  behavioral_snapshot: Record<string, number | string>;
  centroid_features: Record<string, number>;
};
export type PersonaPack = {
  version: string;
  customer_id: string;
  generated_at: string;
  schema_version: "1.0" | "1.1";
  personas: Persona[];
  weights: WeightSchemes;
  stability_score: number;
  is_starter: boolean;
};

// #25 / persona-pack-ui: the read-only RENDERED view of a pack (the
// `/persona-packs/{id}/detail` endpoint). Distinct from the raw PersonaPack
// above: the backend renders the behavioral-comparison blocks through the
// single-sourced honesty logic in behavioral_profile.py rather than shipping the
// bulky raw v1.1 arrays for the client to interpret. Hand-mirrored like the rest
// of this block.
export type DeltaView = {
  label: string;
  direction: "higher" | "lower";
  magnitude: "somewhat" | "much" | "dramatically";
};
export type ProfileBlockView = {
  heading: string;
  intro: string;
  deltas: DeltaView[];
  tail_count: number;
  suppressed_count: number;
  grounded: boolean;
  source_tier: string;
  note: string;
};
export type WeightSchemeView = {
  key: "head_count" | "order_weighted" | "revenue_weighted";
  label: string;
  available: boolean;
  note?: string | null;
};
export type PersonaProfileView = {
  id: string;
  name: string;
  description: string;
  jtbd?: string | null;
  behavioral_snapshot: Record<string, number | string>;
  shares: Record<string, number>;
  how_you_compare?: ProfileBlockView | null;
  distinctive?: ProfileBlockView | null;
};
export type PersonaPackDetail = {
  version: string;
  customer_id: string;
  generated_at: string;
  schema_version: "1.0" | "1.1";
  is_starter: boolean;
  stability_score: number;
  persona_count: number;
  has_individual_rows: boolean;
  weight_schemes: WeightSchemeView[];
  personas: PersonaProfileView[];
};
export type Hypothesis = components["schemas"]["Hypothesis"];
// #215/#245 PR 3a/3b: the backend Simulation + SimulationRequest now carry a
// `setup_id` (which crawl setup's Feature Pack the sim resolves against), but
// the checked-in api-types.ts predates it — same stale-generated caveat as
// FeaturePackManifest.archived above. Optional on the response so a legacy row
// (or an older backend) reads as the "default" anchor; optional on the request
// so omitting it stays byte-identical to a pre-#215 create. Collapse to the
// bare generated type once api-types.ts is regenerated.
export type Simulation = components["schemas"]["Simulation"] & {
  setup_id?: string;
  // Phase 8 refinement loop (#479, merged to main). The backend Simulation read
  // now carries its iteration lineage. `api-types.ts` predates these fields
  // (the generated file is refreshed via `npm run gen-types` against a running
  // backend); hand-augmented here, same stale-generated caveat as setup_id
  // above. `lineage` is NEAREST-ANCESTOR-FIRST (lineage[0] = immediate parent,
  // last = root), empty for un-parented runs, depth-capped at 10, cycle-safe,
  // customer-scoped. Collapse to the bare generated types once regenerated.
  parent_simulation_id?: string | null;
  lineage?: LineageEntry[];
};
export type SimulationRequest = components["schemas"]["SimulationRequest"] & {
  setup_id?: string;
  // Phase 8 (#479): create a run LINKED to a parent so the lineage walk can
  // reconstruct the iteration chain. Optional — omitting it keeps the payload
  // byte-identical to a pre-#479 create.
  parent_simulation_id?: string | null;
};

// ── Phase 8 refinement loop types (#479) ────────────────────────────────────
// Hand-authored mirrors of the backend response shapes (lineage + compare).
// These are NOT yet in the generated api-types.ts; keep them in lockstep with
// backend/sidira_simulator/schemas until `gen-types` is rerun against a live
// backend, at which point they collapse to components["schemas"][…].

export type WeaknessCategory = Weakness["category"];

export interface LineageEntry {
  id: string;
  parent_simulation_id: string | null;
  status: SimulationStatus;
  confidence_score: number | null;
  hypothesis_label: string;
}

export interface SimulationRef {
  id: string;
  status: SimulationStatus;
  confidence_score: number | null;
  hypothesis_label: string;
}

export type WeaknessChange =
  | "appeared"
  | "disappeared"
  | "changed"
  | "unchanged";

export interface WeaknessCategoryDiff {
  category: WeaknessCategory;
  change: WeaknessChange;
  old_agent_count: number;
  new_agent_count: number;
  agent_count_delta: number;
  old_frequency: number;
  new_frequency: number;
}

export interface SimulationComparison {
  old: SimulationRef;
  new: SimulationRef;
  old_confidence_score: number | null;
  new_confidence_score: number | null;
  confidence_score_delta: number | null;
  weakness_category_diffs: WeaknessCategoryDiff[];
  weakness_categories_appeared: string[];
  weakness_categories_disappeared: string[];
  weakness_categories_changed: string[];
  old_refinement_suggestions: string[];
  new_refinement_suggestions: string[];
  refinement_suggestions_added: string[];
  refinement_suggestions_resolved: string[];
  old_sentiment_positive_share: number | null;
  new_sentiment_positive_share: number | null;
  sentiment_positive_share_delta: number | null;
}
export type SimulationResult = components["schemas"]["SimulationResult"];
export type InputFlags = components["schemas"]["InputFlags"];
export type SimulationStatus = components["schemas"]["SimulationStatus"];
export type ModelInfo = components["schemas"]["ModelInfo"];
export type ListModelsResponse = components["schemas"]["ListModelsResponse"];
export type SimulationLimitsResponse =
  components["schemas"]["SimulationLimitsResponse"];
export type ArmSplit = components["schemas"]["ArmSplit"];
export type Weakness = components["schemas"]["Weakness"];
export type EvidenceGraph = components["schemas"]["EvidenceGraph"];
export type EvidenceEdge = components["schemas"]["EvidenceEdge"];
export type EvidenceNode = components["schemas"]["EvidenceNode"];
export type AgentInstance = components["schemas"]["AgentInstance"];
export type AgentSummary = components["schemas"]["AgentSummary"];
export type AgentChatRequest = components["schemas"]["AgentChatRequest"];
export type AgentChatResponse = components["schemas"]["AgentChatResponse"];
export type AgentChatTurn = components["schemas"]["AgentChatTurn"];
export type PersonaGroupChatRequest = components["schemas"]["PersonaGroupChatRequest"];
export type PersonaGroupChatResponse = components["schemas"]["PersonaGroupChatResponse"];
export type PersonaGroupTurn = components["schemas"]["PersonaGroupTurn"];
export type PersonaGroupRole = components["schemas"]["PersonaGroupRole"];
export type PerAgentReply = components["schemas"]["PerAgentReply"];
export type AgentReference = components["schemas"]["AgentReference"];
export type UnavailableAgent = components["schemas"]["UnavailableAgent"];
export type PersonaGroupMode = "collective" | "individual";
export type PersonaGroupArm = "treatment" | "control";
export type FeedbackRequest = components["schemas"]["FeedbackRequest"];
export type FeedbackResponse = components["schemas"]["FeedbackResponse"];
export type SimulationRunState = components["schemas"]["SimulationRunState"];
export type RunPhase = components["schemas"]["RunPhase"];
export type RunEvent = components["schemas"]["RunEvent"];

// CreateSimulationResponse isn't surfaced via components/schemas in some
// codegen flows, so we declare it inline.
export interface CreateSimulationResponse {
  id: string;
  status: SimulationStatus;
  poll_url: string;
}

// ── Low-level helpers ───────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`HTTP ${status}: ${body}`);
  }
}

async function _req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  // 204 No Content / empty bodies
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as unknown as T);
}

export const apiGet = <T>(path: string) => _req<T>(path);
export const apiPost = <T, U>(path: string, body: T) =>
  _req<U>(path, { method: "POST", body: JSON.stringify(body) });
export const apiPut = <T, U>(path: string, body: T) =>
  _req<U>(path, { method: "PUT", body: JSON.stringify(body) });
// DELETE with no body — 204 No Content resolves to undefined (see _req). Throws
// ApiError on a non-2xx (e.g. 404 when the row isn't the caller's).
export const apiDelete = (path: string) => _req<void>(path, { method: "DELETE" });

// ── Endpoint-specific typed wrappers ────────────────────────────────────

// #214: the Library hides any pack VERSION the customer archived (soft-delete).
// By default GET /capabilities 404s when the latest pack is archived (reads as an
// empty tenant); ?include_archived=true is the "Show archived" opt-in. Archiving
// never deletes the pack — a historical sim that froze the version still resolves
// it, because the loader never consults the archive marker.
// #215/#245 PR 3b: `setupId` selects which crawl setup's pack to read. Omitted
// (the default) → `"default"` so the call is byte-identical to pre-#215 prod —
// same R2 prefix, same pointer (the backend defaults the query param to
// "default"). We only append `?setup_id=` for a non-default setup so a
// default-only org's request stays exactly as it was before this PR.
const setupQuery = (setupId?: string): string =>
  setupId && setupId !== DEFAULT_SETUP_ID
    ? `setup_id=${encodeURIComponent(setupId)}`
    : "";

const joinQuery = (...parts: string[]): string => {
  const q = parts.filter(Boolean).join("&");
  return q ? `?${q}` : "";
};

export const getCapabilities = (includeArchived = false, setupId?: string) =>
  apiGet<FeaturePackManifest>(
    `/capabilities${joinQuery(
      includeArchived ? "include_archived=true" : "",
      setupQuery(setupId),
    )}`,
  );

export const getCapabilitySummary = (includeArchived = false, setupId?: string) =>
  apiGet<FeaturePackSummary>(
    `/feature-pack/summary${joinQuery(
      includeArchived ? "include_archived=true" : "",
      setupQuery(setupId),
    )}`,
  );

// #214: archive (hide from Library) / unarchive a Feature Pack version. SOFT-DELETE
// — the version stays resolvable for any historical simulation that froze it; this
// is distinct from the forbidden hand-edit / hard-delete of pack contents. Inline
// type, same codegen caveat as CrawlSummary (api-types.ts predates this route).
export interface FeaturePackArchiveState {
  customer_id: string;
  pack_version: string;
  archived: boolean;
}

export const archiveFeaturePack = (version: string) =>
  apiPost<Record<string, never>, FeaturePackArchiveState>(
    `/featurepacks/${encodeURIComponent(version)}/archive`,
    {},
  );

export const unarchiveFeaturePack = (version: string) =>
  apiPost<Record<string, never>, FeaturePackArchiveState>(
    `/featurepacks/${encodeURIComponent(version)}/unarchive`,
    {},
  );

export const getCapability = (name: string) =>
  apiGet<CapabilityRecord>(`/capabilities/${encodeURIComponent(name)}`);

export const listSupportedModels = () =>
  apiGet<ListModelsResponse>("/models");

export const getSimulationLimits = () =>
  apiGet<SimulationLimitsResponse>("/config/limits");

// Phase 5 #101: list the active Persona Pack's personas for the wizard's
// persona-filter checkbox list.
export const getActivePersonas = () =>
  apiGet<ActivePersonasResponse>("/personas");

// #207: full pack contents for the Library's pack detail page. `id="latest"`
// resolves the active pack (with the #212 starter fallback for empty tenants);
// an explicit version loads that snapshot and 404s when genuinely missing.
export const getPersonaPack = (id: string) =>
  apiGet<PersonaPack>(`/persona-packs/${encodeURIComponent(id)}`);

// #25: the rendered detail view (behavioral-comparison blocks, all weight
// schemes with drop reasons, honesty flags) for the Library detail page. Same
// `latest`/starter/404 semantics as getPersonaPack.
export const getPersonaPackDetail = (id: string) =>
  apiGet<PersonaPackDetail>(`/persona-packs/${encodeURIComponent(id)}/detail`);

// Sample-workspace seeding (sessions/sample-workspace): clone the Streamly
// sample persona + feature packs into the caller's own tenant. Backend 409s
// if the workspace already has data. Inline type — same codegen caveat as
// CreateSimulationResponse.
export interface SampleWorkspaceResponse {
  source: string;
  persona_pack_version: string;
  persona_count: number;
  feature_pack_version: string;
  capabilities: string[];
}

export const generateSampleWorkspace = () =>
  apiPost<Record<string, never>, SampleWorkspaceResponse>(
    "/sample-workspace",
    {},
  );

// #171 crawl setup — the saved config the walker will read. Inline types,
// same codegen caveat as CreateSimulationResponse. The setup names WHAT to
// crawl (capabilities, entry URLs, sandbox logins); it never carries pack
// content — the pack stays generated, never authored.
export interface CrawlCapability {
  name: string;
  entry_urls: string[];
}

// The password-FREE projection — what GET /crawl-setup returns and what the
// dispatch payload names. Passwords go in on save but never come back out
// (#206 Slice C): they're encrypted at rest and delivered to CI only via an
// authenticated pull.
export interface CrawlRoleCredential {
  role: string;
  username: string;
}

// The PUT-only login that also carries the secret password.
export interface CrawlRoleCredentialInput extends CrawlRoleCredential {
  password: string;
}

export type CrawlCadence = "weekly" | "on_demand";

export interface CrawlSetup {
  capabilities: CrawlCapability[];
  sandbox_url: string;
  test_users: CrawlRoleCredential[];
  ip_allowlist_note: string;
  cadence: CrawlCadence;
  walk_depth: number;
}

// The PUT request body: a CrawlSetup whose logins carry passwords. GET still
// returns the password-free CrawlSetup, so the page must re-collect passwords
// to re-save an existing setup.
export interface CrawlSetupInput extends Omit<CrawlSetup, "test_users"> {
  test_users: CrawlRoleCredentialInput[];
}

export interface CrawlSetupEnvelope {
  customer_id: string;
  setup: CrawlSetup | null;
  updated_at: string | null;
}

// The reserved setup id for the org's primary/legacy crawl target. Mirrors the
// backend's schemas.crawl.DEFAULT_SETUP_ID — every org always has it, the
// singular /crawl-setup endpoints anchor on it, and DELETE refuses it (409).
export const DEFAULT_SETUP_ID = "default";

export const getCrawlSetup = () => apiGet<CrawlSetupEnvelope>("/crawl-setup");

export const saveCrawlSetup = (setup: CrawlSetupInput) =>
  apiPut<CrawlSetupInput, CrawlSetupEnvelope>("/crawl-setup", setup);

// ── Multi-setup CRUD (#215/#245 PR 3b) ─────────────────────────────────────
// Multiple crawl setups per org, each keyed by a server-minted `setup_id`. The
// singular endpoints above keep operating on the "default" anchor unchanged;
// these sit alongside for the named setups. Inline types mirror the backend
// schemas.crawl.CrawlSetupListItem / CrawlSetupSummary / CrawlSetupCreateInput
// exactly (same stale-codegen caveat as CrawlSummary). NO GET ever returns a
// credential — the #206 pull model: passwords go in on create/save, are
// encrypted at rest, and are delivered only over the authenticated CI pull.

// The lighter list row: identity + label + non-secret provenance, no full
// config body. `cadence` is a free string here (the backend list item types it
// as str), but in practice carries a CrawlCadence value.
export interface CrawlSetupListItem {
  setup_id: string;
  name: string | null;
  sandbox_url: string;
  capability_count: number;
  cadence: string;
  updated_at: string | null;
}

// One setup as the detail view shows it: identity + label + the password-free
// config. NEVER carries credentials.
export interface CrawlSetupSummary {
  setup_id: string;
  name: string | null;
  setup: CrawlSetup;
  updated_at: string | null;
}

// POST body: a full CrawlSetupInput (with passwords, per the pull model) plus a
// human `name` the server slugifies into the setup_id.
export interface CrawlSetupCreateInput extends CrawlSetupInput {
  name: string;
}

export const listCrawlSetups = () =>
  apiGet<CrawlSetupListItem[]>("/crawl-setups");

// 201 with the password-free summary. The server mints the setup_id from the
// name; the client never picks the raw id.
export const createCrawlSetup = (payload: CrawlSetupCreateInput) =>
  apiPost<CrawlSetupCreateInput, CrawlSetupSummary>("/crawl-setups", payload);

// One setup by id, secret-free. `"default"` works too (the legacy anchor).
// Throws ApiError(404) when the id doesn't exist for this org.
export const getCrawlSetupById = (setupId: string) =>
  apiGet<CrawlSetupSummary>(`/crawl-setups/${encodeURIComponent(setupId)}`);

// PUT updates an existing setup's config; the optional `?name=` relabels it.
// 404 if the id doesn't exist (PUT updates, it never creates — creation is
// POST). Credentials follow the pull model: re-entered on each save.
export const updateCrawlSetup = (
  setupId: string,
  setup: CrawlSetupInput,
  name?: string,
) =>
  apiPut<CrawlSetupInput, CrawlSetupSummary>(
    `/crawl-setups/${encodeURIComponent(setupId)}${
      name != null ? `?name=${encodeURIComponent(name)}` : ""
    }`,
    setup,
  );

// 204 on success. Deleting the reserved "default" setup → 409 (the UI hides the
// delete affordance for it; the 409 is still handled if it ever fires). 404 if
// the id doesn't exist. CONFIG-ONLY: never touches R2, so a historical sim that
// froze a pack from this setup still resolves.
export const deleteCrawlSetup = (setupId: string) =>
  apiDelete(`/crawl-setups/${encodeURIComponent(setupId)}`);

// #193 fire-and-watch crawl trigger. POST dispatches the crawler's CI
// workflow and returns immediately; the browser is never load-bearing — the
// workflow itself publishes the pack by flipping the latest pointer. GET
// /crawls/{id} is the poll; GET /crawls rediscovers an in-flight crawl
// after tab close/reopen. Inline types, same codegen caveat as above.
export type CrawlRunStatus = "pending" | "running" | "complete" | "failed";

export interface CrawlSummary {
  id: string;
  customer_id: string;
  status: CrawlRunStatus;
  phase: string | null; // walking | synthesizing while running
  snapshot_version: string | null;
  capabilities_walked: string[] | null;
  run_url: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

// #215/#245 PR 3b: `setupId` selects which saved crawl setup the run uses. An
// empty body (the default) is byte-identical to today's single-setup dispatch;
// only a non-default id is sent so a default-only org's POST is unchanged.
export const startCrawl = (setupId?: string) =>
  apiPost<{ setup_id?: string }, CrawlSummary>(
    "/crawls",
    setupId && setupId !== DEFAULT_SETUP_ID ? { setup_id: setupId } : {},
  );

export const getCrawl = (id: string) => apiGet<CrawlSummary>(`/crawls/${id}`);

export const listCrawls = () => apiGet<CrawlSummary[]>("/crawls");

export const createSimulation = (req: SimulationRequest) =>
  apiPost<SimulationRequest, CreateSimulationResponse>("/simulations", req);

// ── #313 / T4: deterministic pre-flight answerability preview ────────────────
// Mirrors the POST /simulations needs_input 422 payload so the wizard reuses a
// single override affordance. The verdict is the SAME `assess_answerability`
// (T1) gate the POST path routes on, plus the separable deterministic
// leading-framing lint — zero-LLM, never runs the simulation, never touches
// confidence_score. Inline type (same codegen caveat as CreateSimulationResponse:
// the checked-in api-types.ts predates this route).
export type AnswerabilityState = "answerable" | "needs_input" | "out_of_scope";

export interface PreflightRequest {
  hypothesis: Hypothesis;
  run_as_generic_reception?: boolean;
}

export interface PreflightResponse {
  state: AnswerabilityState;
  reasons: string[];
  fixes: string[];
  reason_codes: string[];
  allow_override: boolean;
  override_field: string;
  leading_framing_reasons: string[];
  leading_framing_fixes: string[];
}

export const preflightSimulation = (req: PreflightRequest) =>
  apiPost<PreflightRequest, PreflightResponse>("/simulations/preflight", req);

// The structured shape of the POST /simulations needs_input 422 detail body
// (T1). `createSimulation` throws an ApiError whose `.body` is the JSON; the
// wizard parses it through this type to render reasons/fixes + the override.
export interface NeedsInputDetail {
  error: "needs_input";
  reasons: string[];
  fixes: string[];
  reason_codes: string[];
  allow_override: boolean;
  override_field: string;
}

// Best-effort parse of an ApiError body into the needs_input detail. Returns
// null when the body isn't the needs_input shape (e.g. a 409/400), so the
// caller falls back to the generic error banner.
export function parseNeedsInput(body: string): NeedsInputDetail | null {
  try {
    const parsed = JSON.parse(body);
    const detail = parsed?.detail ?? parsed;
    if (detail && detail.error === "needs_input") {
      return detail as NeedsInputDetail;
    }
  } catch {
    // not JSON — fall through
  }
  return null;
}

export interface SimulationListItem {
  id: string;
  status: SimulationStatus;
  created_at: string;
  completed_at: string | null;
  hypothesis_prose: string;
  capability_name: string;
  confidence_score: number | null;
}

export const listSimulations = (limit = 50) =>
  apiGet<SimulationListItem[]>(`/simulations?limit=${limit}`);

export const getSimulation = (id: string) =>
  apiGet<Simulation>(`/simulations/${id}`);

// Phase 8 (#479): side-by-side diff of two COMPLETE, owned simulations. 404s
// if either is missing, not-owned, or not yet complete — the caller renders a
// clean empty/error state for that.
export const compareSimulations = (oldId: string, newId: string) =>
  apiGet<SimulationComparison>(
    `/simulations/compare?old=${encodeURIComponent(oldId)}&new=${encodeURIComponent(newId)}`,
  );

export const getSimulationState = (id: string) =>
  apiGet<SimulationRunState>(`/simulations/${id}/state`);

export const listSimulationAgents = (id: string) =>
  apiGet<AgentSummary[]>(`/simulations/${id}/agents`);

export const sendAgentMessage = (id: string, message: string) =>
  apiPost<AgentChatRequest, AgentChatResponse>(
    `/agents/${id}/messages`,
    { message },
  );

export const getAgent = (id: string) =>
  apiGet<AgentInstance>(`/agents/${id}`);

const personaGroupArmQuery = (arm?: PersonaGroupArm | null) =>
  arm ? `?arm=${arm}` : "";

export const getPersonaGroupTurns = (
  simId: string,
  personaId: string,
  arm?: PersonaGroupArm | null,
) =>
  apiGet<PersonaGroupTurn[]>(
    `/simulations/${simId}/personas/${personaId}/turns${personaGroupArmQuery(arm)}`,
  );

export const sendPersonaGroupMessage = (
  simId: string,
  personaId: string,
  message: string,
  mode: PersonaGroupMode = "collective",
  arm?: PersonaGroupArm | null,
) =>
  apiPost<PersonaGroupChatRequest, PersonaGroupChatResponse>(
    `/simulations/${simId}/personas/${personaId}/messages${personaGroupArmQuery(arm)}`,
    { message, mode },
  );

// #56: calibration feedback. realistic_flag is True (👍) / False (👎) /
// null (clear). The backend latest-wins per (target, turn_index); the
// clear path is what powers the third-state toggle UX.
export const sendAgentTurnFeedback = (
  agentId: string,
  turnIndex: number,
  realisticFlag: boolean | null,
) =>
  apiPost<FeedbackRequest, FeedbackResponse>(
    `/agents/${agentId}/turns/${turnIndex}/feedback`,
    { realistic_flag: realisticFlag },
  );

export const sendPersonaGroupTurnFeedback = (
  simId: string,
  personaId: string,
  turnIndex: number,
  realisticFlag: boolean | null,
  arm?: PersonaGroupArm | null,
) =>
  apiPost<FeedbackRequest, FeedbackResponse>(
    `/simulations/${simId}/personas/${personaId}/turns/${turnIndex}/feedback${personaGroupArmQuery(arm)}`,
    { realistic_flag: realisticFlag },
  );

// ── Phase 4.5 · Persona Builder (#21–#28) ────────────────────────────────
// The self-serve wizard: connect a Snowflake feature store, map its columns
// onto the 7 fixed feature groups, trigger a build, watch it, promote the
// resulting pack. Inline types (same codegen caveat as CrawlSummary above —
// api-types.ts predates these routes); collapse to components["schemas"] when
// it's regenerated. Field shapes mirror the backend exactly:
//   feature_stores.py · persona_builds.py · persona_packs.py · column_mapper.py

export type FeatureStoreKind = "snowflake";

// POST body. `schema` is optional (Snowflake default schema otherwise). The
// password goes in here but never comes back out — ConnectionSummary omits it.
export interface SnowflakeConnectionRequest {
  name: string;
  kind: "snowflake";
  account: string;
  user: string;
  password: string;
  warehouse: string;
  role: string;
  database: string;
  schema?: string | null;
}

// Last connectivity-test outcome persisted on a connection (#328). Null on a
// row that has never been tested (the register renders that as UNTESTED).
export type ConnectionTestStatus = "ok" | "failed";

// Sanitized connection row — never carries the password.
export interface ConnectionSummary {
  id: string;
  name: string;
  kind: FeatureStoreKind;
  account: string;
  user: string;
  warehouse: string;
  role: string;
  database: string;
  schema?: string | null;
  // Per-connection HEALTH (#328) — the persisted outcome of the last test, so
  // the saved-connections register can show a last-known state in words without
  // re-testing. All null on a never-tested row. The password is still never
  // returned.
  last_tested_at?: string | null;
  last_test_status?: ConnectionTestStatus | null;
  last_error_kind?: string | null;
  last_error_message?: string | null;
}

// Per-column profile from a preview sample (dtype/nulls/sample values).
export interface ColumnProfile {
  name: string;
  dtype: string;
  non_null_count: number;
  null_fraction: number;
  distinct_count?: number | null;
  sample_values?: (string | number | boolean | null)[] | null;
}

export interface PreviewRequest {
  table_fqn?: string | null;
  sql?: string | null;
  sample_size?: number;
}

export interface PreviewResponse {
  row_count: number;
  columns: ColumnProfile[];
}

// ── #3 document feeder ──────────────────────────────────────────────────────
// The closed set of metric types the persona adapter accepts (mirrors the
// backend METRIC_TYPES). An extraction field MUST declare one of these so the
// column it produces is normalizable by the existing build pipeline.
export const METRIC_TYPES = [
  "count",
  "score",
  "ratio",
  "flag",
  "categorical",
  "json_ratios",
  "json_counts",
  "tenure_days",
] as const;
export type MetricType = (typeof METRIC_TYPES)[number];

// One bounded column to pull from each entity's documents. `description` is the
// extraction instruction shown to the model; it never widens the field set.
export interface ExtractionField {
  name: string;
  type: MetricType;
  description?: string;
}

// The CLOSED schema extraction may emit — anything else is dropped.
export interface ExtractionSchema {
  fields: ExtractionField[];
  entity_key?: string; // defaults to "entity_id" backend-side
}

// All document text for a single entity (one persona-pipeline row).
export interface EntityDocument {
  entity_id: string;
  text: string;
}

export interface ExtractDocumentsRequest {
  documents: EntityDocument[];
  extraction_schema: ExtractionSchema;
}

// Same (row_count, columns) shape as PreviewResponse so doc-fed columns flow
// straight into the existing Map step; `rows` rides back for the build step.
export interface ExtractDocumentsResponse {
  row_count: number;
  columns: ColumnProfile[];
  rows: Array<Record<string, unknown>>;
}

// The 7 canonical feature groups (column_mapper.FeatureGroup) — do NOT rename;
// these exact ids are what the build's column_mapping is keyed on.
export type FeatureGroup =
  | "demographic_identity"
  | "behavioral_patterns"
  | "motivations_jtbd"
  | "pain_points_friction"
  | "value_sensitivity"
  | "channel_tech_behavior"
  | "loyalty_lifecycle";

export const FEATURE_GROUPS: FeatureGroup[] = [
  "demographic_identity",
  "behavioral_patterns",
  "motivations_jtbd",
  "pain_points_friction",
  "value_sensitivity",
  "channel_tech_behavior",
  "loyalty_lifecycle",
];

export type MappingConfidence = "high" | "med" | "low";

export interface ColumnAssignment {
  column: string;
  confidence: MappingConfidence;
  rationale: string;
}

// Wizard-facing grouped suggestion: each canonical group + `unmapped`, every
// input column appears in exactly one bucket.
export type MappingSuggestion = Record<FeatureGroup, ColumnAssignment[]> & {
  unmapped: ColumnAssignment[];
};

// Build config — the POST /persona-builds body. `column_mapping` maps each
// column name to a group id, or null to ignore it. `k` is the persona target
// (a number, or "auto" to let the pipeline choose).
export type BuildK = number | "auto";
export type LlmProvider = "groq" | "anthropic";
export type WeightScheme = "head_count" | "order_weighted" | "revenue_weighted";

export interface BuildConfig {
  connection_id: string;
  source_query: string;
  column_mapping: Record<string, FeatureGroup | null>;
  k?: BuildK;
  stability_threshold?: number;
  llm_provider?: LlmProvider;
  weight_schemes?: WeightScheme[];
}

export type BuildStatus = "pending" | "running" | "complete" | "failed";

export interface BuildSummary {
  id: string;
  customer_id: string;
  connection_id: string;
  status: BuildStatus;
  pack_version: string | null;
  stability_score: number | null;
  persona_count: number | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

// One line of the build's events.jsonl (RunEvent shape, reused from the
// simulation runner). `payload` carries event-specific fields (row_count,
// stability_score, persona_count, pack_version, error).
export type BuildEventType =
  | "run.started"
  | "packs.loaded"
  | "score.updated"
  | "run.complete"
  | "run.failed";

export interface BuildEvent {
  type: BuildEventType | string;
  at: string;
  payload: Record<string, string | number | null>;
}

export type PackStatus = "draft" | "promoted" | "retired";

export interface PackSummary {
  id: string;
  version: string;
  status: PackStatus;
  stability_score: number;
  persona_count: number;
  created_at: string;
  promoted_at: string | null;
  is_latest: boolean;
}

// ── feature-store connections ──
export const createFeatureStore = (req: SnowflakeConnectionRequest) =>
  apiPost<SnowflakeConnectionRequest, ConnectionSummary>("/feature-stores", req);

export const listFeatureStores = () =>
  apiGet<ConnectionSummary[]>("/feature-stores");

// #327: delete a saved connection (customer-scoped server-side; 404 if it isn't
// yours, so existence never leaks across customers). 204 on success. Existing
// persona builds keep their records — this only removes the credential future
// builds could reuse.
export const deleteFeatureStore = (id: string) =>
  apiDelete(`/feature-stores/${encodeURIComponent(id)}`);

// 204 on success; throws ApiError with a structured {error_kind, message}
// detail body on failure (400 auth/permission, 502 network/unknown).
export const testFeatureStore = (id: string) =>
  apiPost<Record<string, never>, void>(
    `/feature-stores/${encodeURIComponent(id)}/test`,
    {},
  );

export const previewFeatureStore = (id: string, body: PreviewRequest) =>
  apiPost<PreviewRequest, PreviewResponse>(
    `/feature-stores/${encodeURIComponent(id)}/preview`,
    body,
  );

export const suggestMapping = (id: string, columns: ColumnProfile[]) =>
  apiPost<{ columns: ColumnProfile[] }, MappingSuggestion>(
    `/feature-stores/${encodeURIComponent(id)}/suggest-mapping`,
    { columns },
  );

// Connection-agnostic mapping — for columns that don't come from a saved
// connection (the #3 document feeder). Same stateless suggestion.
export const suggestMappingForColumns = (columns: ColumnProfile[]) =>
  apiPost<{ columns: ColumnProfile[] }, MappingSuggestion>(
    "/feature-stores/suggest-mapping",
    { columns },
  );

// #3 doc feeder — extract bounded, fixed-schema feature rows from documents,
// returned in the same (row_count, columns) shape as a feature-store preview.
export const extractDocuments = (req: ExtractDocumentsRequest) =>
  apiPost<ExtractDocumentsRequest, ExtractDocumentsResponse>(
    "/feature-stores/extract-documents",
    req,
  );

// ── persona builds ──
export const createPersonaBuild = (config: BuildConfig) =>
  apiPost<BuildConfig, BuildSummary>("/persona-builds", config);

export const getPersonaBuild = (id: string) =>
  apiGet<BuildSummary>(`/persona-builds/${encodeURIComponent(id)}`);

export const listPersonaBuilds = () =>
  apiGet<BuildSummary[]>("/persona-builds");

// The events endpoint streams NDJSON (one RunEvent per line), not a JSON array,
// so it bypasses the JSON-parsing _req helper: fetch raw text and split lines.
export const getPersonaBuildEvents = async (id: string): Promise<BuildEvent[]> => {
  const res = await fetch(
    `${API_BASE}/persona-builds/${encodeURIComponent(id)}/events`,
  );
  if (!res.ok) throw new ApiError(res.status, await res.text());
  const text = await res.text();
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as BuildEvent);
};

// ── persona packs (list + promote; reads live in getPersonaPack[Detail]) ──
export const listPersonaPacks = () => apiGet<PackSummary[]>("/persona-packs");

export const promotePersonaPack = (version: string) =>
  apiPost<Record<string, never>, PackSummary>(
    `/persona-packs/${encodeURIComponent(version)}/promote`,
    {},
  );

// ── UX helpers ─────────────────────────────────────────────────────────

export const isTerminalStatus = (s: SimulationStatus | undefined | null) =>
  s === "complete" || s === "failed";

export const isBuildTerminal = (s: BuildStatus | undefined | null) =>
  s === "complete" || s === "failed";

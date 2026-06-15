/**
 * Typed API client.
 *
 * Run `npm run gen-types` against a running backend to refresh `./api-types.ts`
 * from the FastAPI OpenAPI export. Types here import from `./api-types`.
 */

import type { components } from "./api-types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

// ── Re-exported schema types for page imports ──────────────────────────

export type FeaturePackManifest = components["schemas"]["FeaturePackManifest"];
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
// Lightweight per-capability projection (name + roles, no PRD/Figma body) so the
// Library browse page can group by role from a single fetch. Hand-mirrored like
// Capability above; collapse to components["schemas"] when api-types.ts is
// regenerated.
export type CapabilitySummary = {
  name: string;
  roles: string[];
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
export type Hypothesis = components["schemas"]["Hypothesis"];
export type Simulation = components["schemas"]["Simulation"];
export type SimulationRequest = components["schemas"]["SimulationRequest"];
export type SimulationResult = components["schemas"]["SimulationResult"];
export type SimulationStatus = components["schemas"]["SimulationStatus"];
export type ModelInfo = components["schemas"]["ModelInfo"];
export type ListModelsResponse = components["schemas"]["ListModelsResponse"];
export type SimulationLimitsResponse =
  components["schemas"]["SimulationLimitsResponse"];
export type ArmSplit = components["schemas"]["ArmSplit"];
export type Weakness = components["schemas"]["Weakness"];
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

// ── Endpoint-specific typed wrappers ────────────────────────────────────

export const getCapabilities = () => apiGet<FeaturePackManifest>("/capabilities");

export const getCapabilitySummary = () =>
  apiGet<FeaturePackSummary>("/feature-pack/summary");

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

export const getCrawlSetup = () => apiGet<CrawlSetupEnvelope>("/crawl-setup");

export const saveCrawlSetup = (setup: CrawlSetupInput) =>
  apiPut<CrawlSetupInput, CrawlSetupEnvelope>("/crawl-setup", setup);

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

export const startCrawl = () =>
  apiPost<Record<string, never>, CrawlSummary>("/crawls", {});

export const getCrawl = (id: string) => apiGet<CrawlSummary>(`/crawls/${id}`);

export const listCrawls = () => apiGet<CrawlSummary[]>("/crawls");

export const createSimulation = (req: SimulationRequest) =>
  apiPost<SimulationRequest, CreateSimulationResponse>("/simulations", req);

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

// ── UX helpers ─────────────────────────────────────────────────────────

export const isTerminalStatus = (s: SimulationStatus | undefined | null) =>
  s === "complete" || s === "failed";

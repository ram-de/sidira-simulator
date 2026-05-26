/**
 * Typed API client.
 *
 * Run `npm run gen-types` against a running backend to refresh `./api-types.ts`
 * from the FastAPI OpenAPI export. Types here import from `./api-types`.
 */

import type { components } from "./api-types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

// ── Re-exported schema types for page imports ──────────────────────────

export type FeaturePackManifest = components["schemas"]["FeaturePackManifest"];
export type Hypothesis = components["schemas"]["Hypothesis"];
export type Simulation = components["schemas"]["Simulation"];
export type SimulationRequest = components["schemas"]["SimulationRequest"];
export type SimulationResult = components["schemas"]["SimulationResult"];
export type SimulationStatus = components["schemas"]["SimulationStatus"];
export type Weakness = components["schemas"]["Weakness"];
export type AgentInstance = components["schemas"]["AgentInstance"];
export type AgentSummary = components["schemas"]["AgentSummary"];
export type AgentChatRequest = components["schemas"]["AgentChatRequest"];
export type AgentChatResponse = components["schemas"]["AgentChatResponse"];
export type AgentChatTurn = components["schemas"]["AgentChatTurn"];
export type PersonaGroupChatRequest = components["schemas"]["PersonaGroupChatRequest"];
export type PersonaGroupChatResponse = components["schemas"]["PersonaGroupChatResponse"];
export type PersonaGroupTurn = components["schemas"]["PersonaGroupTurn"];
export type PerAgentReply = components["schemas"]["PerAgentReply"];
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

// ── Endpoint-specific typed wrappers ────────────────────────────────────

export const getCapabilities = () => apiGet<FeaturePackManifest>("/capabilities");

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

export const getPersonaGroupTurns = (simId: string, personaId: string) =>
  apiGet<PersonaGroupTurn[]>(
    `/simulations/${simId}/personas/${personaId}/turns`,
  );

export const sendPersonaGroupMessage = (
  simId: string,
  personaId: string,
  message: string,
) =>
  apiPost<PersonaGroupChatRequest, PersonaGroupChatResponse>(
    `/simulations/${simId}/personas/${personaId}/messages`,
    { message },
  );

// ── UX helpers ─────────────────────────────────────────────────────────

export const isTerminalStatus = (s: SimulationStatus | undefined | null) =>
  s === "complete" || s === "failed";

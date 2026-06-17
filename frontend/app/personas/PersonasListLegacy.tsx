"use client";

// Library — the instrument's consumables (R2 epic #156, PR 6 / #168).
//
// Three entity sections per DESIGN.md §7.6: the feature pack (as-built
// product — GENERATED, never authored), persona packs (who reacts), and
// stimuli (the change under test). Everything here is a record on paper —
// no glass, no live readings (§4.2, §10).
//
// Honest data sources only:
//   · Feature pack   — GET /capabilities (manifest: version, generated_at,
//     capability names, crawl metadata). Each capability card links to its
//     reverse PRD + reverse-Figma record via GET /capabilities/{name} (#207).
//   · Persona packs  — GET /personas (active pack version + personas).
//     GET /persona-packs is still a stub upstream, so only the active pack
//     renders; drafts aren't listable yet.
//   · Stimuli        — derived from past runs' hypotheses (list + a bounded
//     fan-out of run details for arms / attachments). First-class stimuli
//     are #169; this view is read-only.

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiError,
  getActivePersonas,
  getCapabilities,
  getSimulation,
  listSimulations,
  type ActivePersonasResponse,
  type FeaturePackManifest,
  type SimulationStatus,
} from "@/lib/api";
import SampleWorkspaceCard from "@/components/SampleWorkspaceCard";
import { TOKENS, FONT_SANS, FONT_MONO } from "@/lib/design";
import {
  BodyNote,
  Card,
  CardGrid,
  CardHead,
  CardLink,
  CardNote,
  Chip,
  EmptyState,
  ErrorNote,
  isoDate,
  LibraryStyles,
  PendingNote,
  Rows,
  Section,
} from "@/components/library/furniture";

// How many capability cards the landing shows before deferring the rest to the
// dedicated browse page (#207 — the landing stays bounded regardless of scale).
const LANDING_CAPABILITY_CAP = 6;

// ── derived stimuli ─────────────────────────────────────────────────────

interface StimulusRun {
  id: string;
  status: SimulationStatus;
  created_at: string;
}

interface DerivedStimulus {
  key: string;
  capability: string;
  prose: string;
  /** null = run detail fetch failed; arm count unknown. */
  arms: number | null;
  hasPrd: boolean;
  figmaScreens: number;
  runs: StimulusRun[]; // newest first
}

const STIMULUS_DETAIL_FAN_OUT = 8;
const STIMULUS_CARD_CAP = 6;

type Fetchable<T> =
  | { state: "loading" }
  | { state: "ready"; data: T }
  | { state: "empty" }
  | { state: "error"; message: string };

const runDesignator = (id: string) => `RUN ${id.slice(0, 8).toUpperCase()}`;

// ── page ────────────────────────────────────────────────────────────────

export default function LibraryPage() {
  const [pack, setPack] = useState<Fetchable<FeaturePackManifest>>({ state: "loading" });
  const [personas, setPersonas] = useState<Fetchable<ActivePersonasResponse>>({
    state: "loading",
  });
  const [stimuli, setStimuli] = useState<Fetchable<DerivedStimulus[]>>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    const settle = <T,>(
      set: (v: Fetchable<T>) => void,
      promise: Promise<T>,
      isEmpty: (data: T) => boolean = () => false,
    ) =>
      promise
        .then((data) => {
          if (cancelled) return;
          set(isEmpty(data) ? { state: "empty" } : { state: "ready", data });
        })
        .catch((e) => {
          if (cancelled) return;
          if (e instanceof ApiError && e.status === 404) set({ state: "empty" });
          else set({ state: "error", message: e?.message ?? "request failed" });
        });

    settle(setPack, getCapabilities());
    settle(setPersonas, getActivePersonas());
    settle(setStimuli, deriveStimuli(), (rows) => rows.length === 0);

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
      <LibraryStyles />

      <header
        style={{
          padding: "20px 24px 16px",
          borderBottom: `1px solid ${TOKENS.rule}`,
          display: "flex",
          alignItems: "baseline",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>
          Library
        </h1>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: TOKENS.inkMuted,
            letterSpacing: "0.06em",
          }}
        >
          FEATURE PACK + PERSONA PACKS + STIMULI
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontFamily: FONT_MONO,
            fontSize: 10,
            letterSpacing: "0.08em",
            color: TOKENS.inkMuted,
            border: `1px solid ${TOKENS.rule}`,
            borderRadius: 2,
            padding: "3px 8px",
            whiteSpace: "nowrap",
          }}
        >
          UNVALIDATED PACKS CANNOT PRINT SHIP CANDIDATES
        </span>
      </header>

      <div style={{ padding: 24 }}>
        <FeaturePackSection pack={pack} />
        <PersonaPacksSection personas={personas} />
        <StimuliSection stimuli={stimuli} />

        {/* sessions/sample-workspace: probes GET /personas + GET /capabilities
            and renders only when the tenant is truly empty. */}
        <SampleWorkspaceCard detectEmpty />
      </div>
    </main>
  );
}

async function deriveStimuli(): Promise<DerivedStimulus[]> {
  const list = await listSimulations(50);
  // Detail fan-out stays bounded to the newest rows, but grouping runs over
  // the full fetched list so duplicate recent runs can't crowd out older
  // distinct stimuli (codex P2).
  const recent = list.slice(0, STIMULUS_DETAIL_FAN_OUT);
  const settledDetails = await Promise.allSettled(
    recent.map((row) => getSimulation(row.id)),
  );
  const detailById = new Map(
    recent.map((row, i) => {
      const settled = settledDetails[i];
      return [row.id, settled.status === "fulfilled" ? settled.value : null] as const;
    }),
  );

  const byKey = new Map<string, DerivedStimulus>();
  list.forEach((row) => {
    const detail = detailById.get(row.id) ?? null;
    const prose = (detail?.hypothesis.prose ?? row.hypothesis_prose).trim();
    const capability = detail?.hypothesis.capability_name ?? row.capability_name;
    const key = `${capability}::${prose}`;
    const run: StimulusRun = { id: row.id, status: row.status, created_at: row.created_at };

    const existing = byKey.get(key);
    if (existing) {
      existing.runs.push(run);
      return;
    }
    byKey.set(key, {
      key,
      capability,
      prose,
      arms: detail ? (detail.arm_split ? 2 : 1) : null,
      hasPrd: Boolean(detail?.hypothesis.proposed_prd),
      figmaScreens: detail?.hypothesis.proposed_figma?.screens?.length ?? 0,
      runs: [run],
    });
  });

  return Array.from(byKey.values()).slice(0, STIMULUS_CARD_CAP);
}

// ── sections ────────────────────────────────────────────────────────────

function FeaturePackSection({ pack }: { pack: Fetchable<FeaturePackManifest> }) {
  return (
    <Section label="Feature pack — as-built product">
      {pack.state === "loading" && <PendingNote>Loading the feature pack…</PendingNote>}
      {pack.state === "error" && (
        <ErrorNote>The feature pack could not be loaded: {pack.message}</ErrorNote>
      )}
      {pack.state === "empty" && (
        <EmptyState>
          No feature pack yet — the pack is a generated snapshot of your as-built product,
          written by Sidira&apos;s crawler and never authored by hand. Point the walker at
          your product in{" "}
          <Link href="/personas/crawl-setup" className="lib-link">
            crawl setup
          </Link>{" "}
          to start the first crawl; the latest pointer flips once a clean crawl lands.
        </EmptyState>
      )}
      <CardGrid>
        {pack.state === "ready" && (
          <Card>
            <CardHead name="As-built product">
              <Chip strong>SNAPSHOT {pack.data.snapshot_version}</Chip>
            </CardHead>
            <Rows
              rows={[
                ["Capabilities", String(pack.data.capabilities.length)],
                ["Generated", isoDate(pack.data.generated_at)],
                ["Schema", `v${pack.data.schema_version}`],
                ...Object.entries(pack.data.crawl_metadata ?? {})
                  .slice(0, 3)
                  .map(
                    ([k, v]) => [k.replace(/_/g, " "), v.toUpperCase()] as [string, string],
                  ),
              ]}
            />
            <CardNote>
              Each run freezes its own slice of this snapshot, so readings stay reproducible.
            </CardNote>
          </Card>
        )}
        {pack.state === "ready" &&
          pack.data.capabilities.slice(0, LANDING_CAPABILITY_CAP).map((name) => (
            <Card key={name}>
              <CardHead name={name}>
                <Chip>CAPABILITY</Chip>
              </CardHead>
              <Rows
                rows={[
                  ["Snapshot", pack.data.snapshot_version],
                  ["Artifacts", "REVERSE PRD + REVERSE FIGMA"],
                ]}
              />
              <CardLink href={`/personas/capability/${encodeURIComponent(name)}`}>
                OPEN CAPABILITY →
              </CardLink>
            </Card>
          ))}
        {/* Bounded landing: the full pack — searchable, groupable, paginated —
            lives on its own page so the grid can't fall over at scale (#207). */}
        {pack.state === "ready" &&
          pack.data.capabilities.length > LANDING_CAPABILITY_CAP && (
            <Card>
              <CardHead name="All capabilities">
                <Chip strong>{pack.data.capabilities.length} TOTAL</Chip>
              </CardHead>
              <Rows
                rows={[
                  [
                    "Previewing",
                    `${LANDING_CAPABILITY_CAP} OF ${pack.data.capabilities.length}`,
                  ],
                  ["Browse", "SEARCH · GROUP A–Z · PAGINATE"],
                ]}
              />
              <CardNote>
                The landing previews a handful; the full pack lives on its own page so it
                stays readable as the crawler finds more.
              </CardNote>
              <CardLink
                href={`/personas/feature-pack/${encodeURIComponent(pack.data.snapshot_version)}`}
              >
                EXPLORE ALL {pack.data.capabilities.length} →
              </CardLink>
            </Card>
          )}
        <Card ghost>
          <CardHead name="New snapshot">
            <Chip>GENERATED — NEVER AUTHORED</Chip>
          </CardHead>
          <Rows
            rows={[
              ["Source", "CRAWL OF THE AS-BUILT PRODUCT"],
              ["Setup", "CAPABILITIES · ENTRY URLS · ROLE LOGINS"],
              ["Versioning", "LATEST POINTER FLIPS AFTER A CLEAN CRAWL"],
            ]}
          />
          <CardNote>
            The as-built pack is the control arm — hand-editing it would corrupt every
            reading. Configure what the walker crawls; the crawl itself waits on the
            walker.
          </CardNote>
          <CardLink href="/personas/crawl-setup">CRAWL SETUP + RE-CRAWL →</CardLink>
        </Card>
      </CardGrid>
    </Section>
  );
}

function PersonaPacksSection({ personas }: { personas: Fetchable<ActivePersonasResponse> }) {
  const leading =
    personas.state === "ready"
      ? [...personas.data.personas]
          .sort((a, b) => b.weight - a.weight)
          .slice(0, 2)
          .map((p) => p.name.toUpperCase())
          .join(" · ")
      : "";

  return (
    <Section label="Persona packs">
      {personas.state === "loading" && <PendingNote>Loading persona packs…</PendingNote>}
      {personas.state === "error" && (
        <ErrorNote>Persona packs could not be loaded: {personas.message}</ErrorNote>
      )}
      {personas.state === "empty" && (
        <BodyNote>
          No persona pack yet. Build one from your own data, or seed the sample workspace
          below to try Sidira right away.
        </BodyNote>
      )}
      <CardGrid>
        {personas.state === "ready" && personas.data.is_starter && (
          <Card>
            <CardHead name="Starter pack">
              <Chip>STARTER · PLACEHOLDER</Chip>
            </CardHead>
            <Rows
              rows={[
                ["Personas", String(personas.data.personas.length)],
                ["Status", "GENERIC PLACEHOLDER — NOT FROM YOUR DATA"],
                ...(leading ? ([["Leading", leading]] as [string, string][]) : []),
                ["Next", "BUILD A REAL PACK OR SEED THE SAMPLE"],
              ]}
            />
            <CardNote>
              These generic personas let you click through Sidira right away, but they
              aren&apos;t built from your data — build a real pack, or seed the sample
              workspace below, before trusting any reading.
            </CardNote>
            <CardLink href="/personas/latest">BROWSE PERSONAS →</CardLink>
          </Card>
        )}
        {personas.state === "ready" && !personas.data.is_starter && (
          <Card>
            <CardHead name="Active pack">
              <Chip strong>{personas.data.pack_version}</Chip>
            </CardHead>
            <Rows
              rows={[
                ["Personas", String(personas.data.personas.length)],
                ["Status", "PROMOTED · USED BY NEW RUNS"],
                ...(leading ? ([["Leading", leading]] as [string, string][]) : []),
                ["Graded", "UNGRADED — CALIBRATION LEDGER EMPTY"],
              ]}
            />
            <CardLink href="/personas/latest">BROWSE PERSONAS →</CardLink>
          </Card>
        )}
        <Card ghost>
          <CardHead name="Build a new pack">
            <Chip>BUILDER</Chip>
          </CardHead>
          <Rows
            rows={[
              ["Source", "SNOWFLAKE → COLUMN MAP → CLUSTER → COMPILE"],
              ["Steps", "7 — LLM-ASSISTED COLUMN MAPPING"],
              ["Output", "VERSIONED PACK · ELIGIBLE AFTER VALIDATION"],
            ]}
          />
          <CardLink href="/personas/new">BUILD A NEW PACK →</CardLink>
        </Card>
      </CardGrid>
    </Section>
  );
}

function StimuliSection({ stimuli }: { stimuli: Fetchable<DerivedStimulus[]> }) {
  return (
    <Section label="Stimuli">
      <BodyNote>
        Derived from past runs — in the MVP a stimulus is authored inside its hypothesis,
        not in the Library.
      </BodyNote>
      {stimuli.state === "loading" && <PendingNote>Deriving stimuli from past runs…</PendingNote>}
      {stimuli.state === "error" && (
        <ErrorNote>Stimuli could not be derived: {stimuli.message}</ErrorNote>
      )}
      {stimuli.state === "empty" && (
        <BodyNote>No runs yet, so nothing to derive — author the first stimulus below.</BodyNote>
      )}
      <CardGrid>
        {stimuli.state === "ready" &&
          stimuli.data.map((s) => <StimulusCard key={s.key} stimulus={s} />)}
        <Card ghost>
          <CardHead name="New stimulus">
            <Chip>AUTHORED IN WIZARD</Chip>
          </CardHead>
          <Rows
            rows={[
              ["Control", "ALWAYS THE AS-BUILT SLICE — NEVER AUTHORED"],
              ["Treatment", "PROSE + PROPOSED PRD + SCREENS (OPTIONAL)"],
              ["Today", "LIVES INSIDE THE HYPOTHESIS — WIZARD · 02 SUBJECT"],
            ]}
          />
          <CardLink href="/simulations/new">AUTHOR INSIDE A NEW HYPOTHESIS →</CardLink>
        </Card>
      </CardGrid>
    </Section>
  );
}

function StimulusCard({ stimulus }: { stimulus: DerivedStimulus }) {
  const attachments = [
    "PROSE",
    ...(stimulus.hasPrd ? ["PROPOSED PRD"] : []),
    ...(stimulus.figmaScreens > 0 ? [`FIGMA · ${stimulus.figmaScreens} SCREENS`] : []),
  ].join(" + ");

  const shownRuns = stimulus.runs.slice(0, 2);
  const moreRuns = stimulus.runs.length - shownRuns.length;
  const newestRun = stimulus.runs[0];

  return (
    <Card>
      <CardHead name={stimulus.capability}>
        <Chip>DERIVED FROM RUNS</Chip>
      </CardHead>
      <p
        style={{
          margin: "0 0 10px",
          fontSize: 13,
          lineHeight: 1.5,
          color: TOKENS.ink,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {stimulus.prose}
      </p>
      <Rows
        rows={[
          ...(stimulus.arms !== null
            ? ([
                ["Arms", stimulus.arms === 2 ? "2 — TREATMENT / CONTROL" : "1 — SINGLE ARM"],
                ["Carries", attachments],
              ] as [string, string][])
            : []),
          [
            "Used in",
            <span key="runs">
              {shownRuns.map((run) => (
                <span key={run.id} style={{ display: "block" }}>
                  <span className={run.status === "running" ? "lib-carrier" : undefined}>
                    {runDesignator(run.id)} · {run.status.toUpperCase()}
                  </span>
                </span>
              ))}
              {moreRuns > 0 && <span style={{ display: "block" }}>+{moreRuns} MORE</span>}
            </span>,
          ],
        ]}
      />
      <CardLink href={`/simulations/${newestRun.id}`}>OPEN RUN →</CardLink>
    </Card>
  );
}

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
//     capability names, crawl metadata). Per-capability reverse PRDs exist
//     in the pack but no endpoint exposes them yet, so cards say so.
//   · Persona packs  — GET /personas (active pack version + personas).
//     GET /persona-packs is still a stub upstream, so only the active pack
//     renders; drafts aren't listable yet.
//   · Stimuli        — derived from past runs' hypotheses (list + a bounded
//     fan-out of run details for arms / attachments). First-class stimuli
//     are #169; this view is read-only.

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
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
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";

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

function isoDate(iso: string): string {
  const t = new Date(iso);
  return Number.isNaN(t.getTime()) ? iso : t.toISOString().slice(0, 10);
}

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
      {/* Hover + §9.5 live carrier. The carrier is the single sanctioned
          pulse; reduced motion renders the static underline. */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
            .lib-card { transition: border-color 80ms ease-out; }
            .lib-card:hover { border-color: ${TOKENS.inkMuted}; }
            .lib-link { color: ${TOKENS.ink}; text-decoration: none; border-bottom: 1px dotted ${TOKENS.inkMuted}; transition: border-color 80ms ease-out; }
            .lib-link:hover { border-bottom-color: ${TOKENS.ink}; }
            .lib-carrier { position: relative; }
            .lib-carrier::after { content: ""; position: absolute; left: 0; right: 0; bottom: -3px; height: 2px; background: ${TOKENS.signal}; animation: lib-carrier 3.4s ease-in-out infinite; }
            @keyframes lib-carrier { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
            @media (prefers-reduced-motion: reduce) { .lib-carrier::after { animation: none; } }
          `,
        }}
      />

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
          pack.data.capabilities.map((name) => (
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
              <CardNote>
                The reverse PRD and reverse-Figma spec live in the pack; they aren&apos;t
                browsable from the Library yet.
              </CardNote>
            </Card>
          ))}
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
            <CardNote>
              Persona descriptions aren&apos;t browsable from the Library yet — runs sample
              this pack directly.
            </CardNote>
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

// ── furniture ───────────────────────────────────────────────────────────

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <span
        style={{
          display: "block",
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: TOKENS.inkMuted,
          paddingBottom: 10,
          borderBottom: `1px solid ${TOKENS.rule}`,
        }}
      >
        {label}
      </span>
      {children}
    </section>
  );
}

function CardGrid({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(290px, 1fr))",
        gap: 16,
        marginTop: 14,
      }}
    >
      {children}
    </div>
  );
}

function Card({ ghost = false, children }: { ghost?: boolean; children: React.ReactNode }) {
  return (
    <article
      className="lib-card"
      style={{
        background: ghost ? TOKENS.paper : TOKENS.paperElevated,
        border: `1px ${ghost ? "dashed" : "solid"} ${TOKENS.rule}`,
        borderRadius: 4,
        // §4.2 elevated top highlight, token-derived (paper-elevated, no raw hex).
        boxShadow: ghost ? "none" : `inset 0 1px 0 ${TOKENS.paperElevated}`,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
      }}
    >
      {children}
    </article>
  );
}

function CardHead({ name, children }: { name: string; children?: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: 10,
        marginBottom: 10,
        width: "100%",
      }}
    >
      <span style={{ fontSize: 15, fontWeight: 600, flex: 1, minWidth: 0 }}>{name}</span>
      {children}
    </div>
  );
}

function Rows({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl
      style={{
        margin: 0,
        display: "grid",
        gridTemplateColumns: "auto 1fr",
        gap: "3px 14px",
        width: "100%",
      }}
    >
      {rows.map(([dt, dd]) => (
        <Fragment key={dt}>
          <dt
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: TOKENS.inkMuted,
              paddingTop: 2,
            }}
          >
            {dt}
          </dt>
          <dd style={{ margin: 0, fontFamily: FONT_MONO, fontSize: 11.5, ...TNUM }}>{dd}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

function Chip({ strong = false, children }: { strong?: boolean; children: React.ReactNode }) {
  // Designators carry ink weight, never color (§4.3).
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10.5,
        letterSpacing: "0.06em",
        border: `1px solid ${strong ? TOKENS.ink : TOKENS.rule}`,
        color: strong ? TOKENS.ink : TOKENS.inkMuted,
        borderRadius: 2,
        padding: "2px 7px",
        whiteSpace: "nowrap",
        ...TNUM,
      }}
    >
      {children}
    </span>
  );
}

// Sentence-case helper copy inside a card — body font, never mono caps (§5.4).
function CardNote({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ margin: "10px 0 0", fontSize: 12, lineHeight: 1.5, color: TOKENS.inkMuted }}>
      {children}
    </p>
  );
}

function CardLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="lib-link"
      style={{ display: "inline-block", marginTop: 12, fontSize: 12.5, fontWeight: 500 }}
    >
      {children}
    </Link>
  );
}

function BodyNote({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ margin: "12px 0 0", fontSize: 13, lineHeight: 1.5, color: TOKENS.inkMuted }}>
      {children}
    </p>
  );
}

// A designed empty-state — §7.7 note anatomy (paper-recessed surface) carrying
// the next action. Empty is not an error: it takes the neutral `rule` border,
// never `alert`/`warn` (§4.3, color never carries state alone), and reads in
// sentence-case body font (§5.4).
function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        marginTop: 12,
        padding: 16,
        border: `1px solid ${TOKENS.rule}`,
        borderRadius: 4,
        background: TOKENS.paperRecessed,
        color: TOKENS.ink,
        fontSize: 13,
        lineHeight: 1.5,
      }}
    >
      {children}
    </div>
  );
}

function PendingNote({ children }: { children: React.ReactNode }) {
  // §8.6 — pending states are honest text, never skeletons or spinners.
  return (
    <p style={{ margin: "12px 0 0", fontSize: 13, color: TOKENS.inkMuted }}>{children}</p>
  );
}

function ErrorNote({ children }: { children: React.ReactNode }) {
  // §7.7 note anatomy — the alert border carries severity; the message
  // reads in ink (§4.3).
  return (
    <div
      role="alert"
      style={{
        marginTop: 12,
        padding: 12,
        border: `0.75px solid ${TOKENS.alert}`,
        borderRadius: 2,
        background: TOKENS.paperRecessed,
        color: TOKENS.ink,
        fontSize: 13,
      }}
    >
      {children}
    </div>
  );
}

"use client";

// ───────────────────────────────────────────────────────────────────────────
// /personas — the Library, v2 "Reading Console" reskin (mirrors /simulations,
// #372).
//
// A faithful port of PersonasListLegacy onto the v2 Console surface: SAME data
// sources (getCapabilities · getActivePersonas · derived stimuli from
// listSimulations + bounded getSimulation fan-out), SAME three-entity IA
// (DESIGN.md §7.6: feature pack · persona packs · stimuli), SAME states
// (loading · error · empty · ready), and the SAME §7.6 / §8 HONESTY LAW —
// every candor string is carried over verbatim ("UNVALIDATED PACKS CANNOT
// PRINT SHIP CANDIDATES", "GENERATED — NEVER AUTHORED", "GENERIC PLACEHOLDER —
// NOT FROM YOUR DATA", "UNGRADED — CALIBRATION LEDGER EMPTY", …). No fabricated
// columns, no invented data — the static /v2/personas-list mock is visual
// reference only; behaviour comes from the REAL page.
//
// Token-driven only; the Library table/card layout lives in styles/v2-theme.css
// (.v2-lib-*), so this island ships no inline <style> (no hydration risk). The
// whole subtree sits under AppShellV2 → ConsoleShell's `.v2-console`.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useEffect, useState, Fragment, type ReactNode } from "react";

import {
  ApiError,
  archiveFeaturePack,
  generateSampleWorkspace,
  getActivePersonas,
  getCapabilities,
  getSimulation,
  listPersonaPacks,
  listSimulations,
  unarchiveFeaturePack,
  type ActivePersonasResponse,
  type FeaturePackManifest,
  type SampleWorkspaceResponse,
  type SimulationStatus,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";
import { Panel, Button } from "@/components/v2";

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

// #47 persona-age nudge: a soft, never-blocking note suggesting a rebuild once
// the active persona pack is older than this. Display-only — it triggers no
// auto-action, and it reads the build date the pack already records. 3 months
// is a sensible default for "behavior may have drifted; consider a refresh".
const PERSONA_PACK_STALE_MONTHS = 3;
const APPROX_DAYS_PER_MONTH = 30.44;

// Whole months elapsed since `iso`, floored. null when the date is unparseable
// (so the nudge stays off rather than firing on a bad value).
function monthsSince(iso: string): number | null {
  const built = new Date(iso).getTime();
  if (Number.isNaN(built)) return null;
  const days = (Date.now() - built) / 86_400_000;
  return Math.floor(days / APPROX_DAYS_PER_MONTH);
}

type Fetchable<T> =
  | { state: "loading" }
  | { state: "ready"; data: T }
  | { state: "empty" }
  | { state: "error"; message: string };

const runDesignator = (id: string) => `RUN ${id.slice(0, 8).toUpperCase()}`;

function isoDate(iso: string): string {
  const t = new Date(iso);
  return Number.isNaN(t.getTime()) ? iso : t.toISOString().slice(0, 10);
}

// ── page ────────────────────────────────────────────────────────────────

export default function PersonasListV2() {
  const [pack, setPack] = useState<Fetchable<FeaturePackManifest>>({ state: "loading" });
  const [personas, setPersonas] = useState<Fetchable<ActivePersonasResponse>>({
    state: "loading",
  });
  const [stimuli, setStimuli] = useState<Fetchable<DerivedStimulus[]>>({ state: "loading" });
  // #47 persona-age nudge: ISO build date of the active (latest promoted) pack.
  // `getActivePersonas` (GET /personas) carries no build date, so we read it
  // from the pack list (GET /persona-packs · PackSummary.created_at). null until
  // loaded / when no promoted pack exists — the nudge simply doesn't render.
  const [activePackBuiltAt, setActivePackBuiltAt] = useState<string | null>(null);

  // #214 — the Library hides archived pack versions by default. The toggle
  // re-fetches with ?include_archived so a retired pack can be reviewed and
  // restored; `archiving` carries the in-flight archive/unarchive action.
  const [showArchived, setShowArchived] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);
  // True when a hidden (archived) latest pack exists but is filtered out of the
  // default view — so the toggle stays reachable even when the default view is
  // empty, letting the PM switch on "show archived" and unarchive it.
  const [hasHiddenPack, setHasHiddenPack] = useState(false);

  // Refetch the feature pack whenever the archived toggle flips. Persona packs +
  // stimuli are unaffected, so they load once below. When the default view comes
  // back empty, probe ?include_archived to tell "no pack yet" from "latest is
  // hidden" — the latter must still expose the toggle (codex P2).
  useEffect(() => {
    let cancelled = false;
    setPack({ state: "loading" });
    getCapabilities(showArchived)
      .then((data) => {
        if (cancelled) return;
        setPack({ state: "ready", data });
        if (!showArchived) setHasHiddenPack(false);
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          setPack({ state: "empty" });
          // Only the default view can hide a pack; probe to surface the toggle.
          if (!showArchived) {
            getCapabilities(true)
              .then(() => !cancelled && setHasHiddenPack(true))
              .catch(() => !cancelled && setHasHiddenPack(false));
          }
        } else {
          setPack({ state: "error", message: e?.message ?? "request failed" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [showArchived]);

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

    settle(setPersonas, getActivePersonas());
    settle(setStimuli, deriveStimuli(), (rows) => rows.length === 0);

    // #47 persona-age nudge: best-effort read of the active pack's build date.
    // Never blocks the page or surfaces an error — on any failure the nudge just
    // stays hidden. The active pack is the latest promoted version.
    listPersonaPacks()
      .then((packs) => {
        if (cancelled) return;
        const active =
          packs.find((p) => p.is_latest && p.status === "promoted") ??
          packs.find((p) => p.status === "promoted") ??
          null;
        setActivePackBuiltAt(active?.created_at ?? null);
      })
      .catch(() => {
        if (!cancelled) setActivePackBuiltAt(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Archive / unarchive a pack VERSION. Soft-delete: this hides the version from
  // the Library (or restores it); it never edits or deletes pack content, and a
  // historical sim that froze the version still resolves it. On success we re-read
  // the pack under the current toggle so the list reflects the new state.
  async function handleArchive(version: string, archived: boolean) {
    setArchiving(true);
    setArchiveError(null);
    try {
      if (archived) await archiveFeaturePack(version);
      else await unarchiveFeaturePack(version);
      const data = await getCapabilities(showArchived).catch((e) => {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      });
      if (data) {
        setPack({ state: "ready", data });
      } else {
        setPack({ state: "empty" });
        // Just archived the latest pack while in the default view: it now exists
        // but is hidden — keep the toggle reachable so it can be restored.
        if (!showArchived && archived) setHasHiddenPack(true);
      }
    } catch (e) {
      setArchiveError(
        e instanceof Error ? e.message : "could not change the archive state",
      );
    } finally {
      setArchiving(false);
    }
  }

  return (
    <AppShellV2
      activeNav="personas"
      title="Library"
      provenance={{ label: "FEATURE PACK + PERSONA PACKS + STIMULI", calibrated: false }}
    >
      <div className="v2-lib">
        <div className="v2-lib-head">
          <span className="v2-lib-kicker v2-mono">
            FEATURE PACK + PERSONA PACKS + STIMULI
          </span>
          <span className="v2-lib-law v2-mono">
            UNVALIDATED PACKS CANNOT PRINT SHIP CANDIDATES
          </span>
        </div>

        <FeaturePackSection
          pack={pack}
          showArchived={showArchived}
          hasHiddenPack={hasHiddenPack}
          onToggleArchived={() => setShowArchived((v) => !v)}
          onArchive={handleArchive}
          archiving={archiving}
          archiveError={archiveError}
        />
        <PersonaPacksSection personas={personas} builtAt={activePackBuiltAt} />
        <StimuliSection stimuli={stimuli} />

        {/* sessions/sample-workspace: probes GET /personas + GET /capabilities
            and renders only when the tenant is truly empty. */}
        <SampleWorkspaceCardV2 />
      </div>
    </AppShellV2>
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

// ── Console furniture (token-driven, .v2-lib-* classes) ─────────────────────

function Section({
  label,
  action,
  children,
}: {
  label: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  // When the section carries a header action (#214 archived toggle), the label +
  // action share a header row that owns the bottom rule; otherwise the label
  // keeps its own rule (unchanged for every other section).
  if (action) {
    return (
      <section className="v2-lib-section">
        <div className="v2-lib-section-head">
          <span className="v2-lib-section-label v2-desig">{label}</span>
          {action}
        </div>
        {children}
      </section>
    );
  }
  return (
    <section className="v2-lib-section">
      <span className="v2-lib-section-label v2-desig">{label}</span>
      {children}
    </section>
  );
}

function CardGrid({ children }: { children: ReactNode }) {
  return <div className="v2-lib-grid">{children}</div>;
}

function Card({ ghost = false, children }: { ghost?: boolean; children: ReactNode }) {
  if (ghost) {
    return <article className="v2-lib-card v2-lib-card--ghost">{children}</article>;
  }
  return (
    <Panel className="v2-lib-card" elevated>
      {children}
    </Panel>
  );
}

function CardHead({ name, children }: { name: string; children?: ReactNode }) {
  return (
    <div className="v2-lib-cardhead">
      <span className="v2-lib-cardname">{name}</span>
      {children}
    </div>
  );
}

// Designators carry ink weight, never color (§4.3). `strong` lifts to --text-hi.
function LibChip({ strong = false, children }: { strong?: boolean; children: ReactNode }) {
  return (
    <span className={strong ? "v2-chip v2-lib-chip--strong v2-tnum" : "v2-chip v2-tnum"}>
      {children}
    </span>
  );
}

function Rows({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="v2-lib-rows">
      {rows.map(([dt, dd]) => (
        <Fragment key={dt}>
          <dt className="v2-lib-rows-dt">{dt}</dt>
          <dd className="v2-lib-rows-dd v2-mono v2-tnum">{dd}</dd>
        </Fragment>
      ))}
    </dl>
  );
}

function CardNote({ children }: { children: ReactNode }) {
  return <p className="v2-lib-cardnote">{children}</p>;
}

function CardLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="v2-lib-cardlink">
      {children}
    </Link>
  );
}

function BodyNote({ children }: { children: ReactNode }) {
  return <p className="v2-lib-bodynote">{children}</p>;
}

// Empty is not an error: neutral note surface, sentence-case body (§4.3, §5.4).
function EmptyState({ children }: { children: ReactNode }) {
  return <div className="v2-lib-empty">{children}</div>;
}

function PendingNote({ children }: { children: ReactNode }) {
  // §8.6 — pending states are honest text, never skeletons or spinners.
  return <p className="v2-lib-pending">{children}</p>;
}

function ErrorNote({ children }: { children: ReactNode }) {
  // §7.7 note anatomy — the alert border carries severity; message reads in ink.
  return (
    <div role="alert" className="v2-lib-error">
      {children}
    </div>
  );
}

// ── sections ────────────────────────────────────────────────────────────

function FeaturePackSection({
  pack,
  showArchived,
  hasHiddenPack,
  onToggleArchived,
  onArchive,
  archiving,
  archiveError,
}: {
  pack: Fetchable<FeaturePackManifest>;
  showArchived: boolean;
  hasHiddenPack: boolean;
  onToggleArchived: () => void;
  onArchive: (version: string, archived: boolean) => void;
  archiving: boolean;
  archiveError: string | null;
}) {
  // Whether THIS pack is archived is a backend FACT (manifest.archived), never
  // inferred from the toggle: the toggle only means "include archived in results".
  const isArchived = pack.state === "ready" ? pack.data.archived === true : false;
  // Keep the toggle reachable whenever it can do something: a pack is shown, the
  // user is already viewing archived (so they can flip back), or a hidden pack
  // exists behind an empty default view (codex P2 — otherwise it's unrecoverable).
  const showToggle = pack.state === "ready" || showArchived || hasHiddenPack;
  const toggle = showToggle ? (
    <button
      type="button"
      className="v2-lib-archived-toggle v2-mono"
      onClick={onToggleArchived}
      aria-pressed={showArchived}
    >
      {showArchived ? "HIDE ARCHIVED" : "SHOW ARCHIVED"}
    </button>
  ) : undefined;
  return (
    <Section label="Feature pack — as-built product" action={toggle}>
      {pack.state === "loading" && <PendingNote>Loading the feature pack…</PendingNote>}
      {pack.state === "error" && (
        <ErrorNote>The feature pack could not be loaded: {pack.message}</ErrorNote>
      )}
      {archiveError && <ErrorNote>{archiveError}</ErrorNote>}
      {pack.state === "empty" && showArchived && (
        <EmptyState>
          No archived feature pack — nothing has been hidden from the Library. Turn
          this off to see the live snapshot.
        </EmptyState>
      )}
      {pack.state === "empty" && !showArchived && hasHiddenPack && (
        <EmptyState>
          The latest snapshot is archived, so it&apos;s hidden from the Library. Choose{" "}
          <strong>Show archived</strong> to review it or restore it — archiving only
          hides a version, it never deletes or edits the pack.
        </EmptyState>
      )}
      {pack.state === "empty" && !showArchived && !hasHiddenPack && (
        <EmptyState>
          No feature pack yet — the pack is a generated snapshot of your as-built product,
          written by Sidira&apos;s crawler and never authored by hand. Point the walker at
          your product in{" "}
          <Link href="/personas/crawl-setup" className="v2-lib-inline-link">
            crawl setup
          </Link>{" "}
          to start the first crawl; the latest pointer flips once a clean crawl lands.
        </EmptyState>
      )}
      <CardGrid>
        {pack.state === "ready" && (
          <Card>
            <CardHead name="As-built product">
              <LibChip strong>
                {isArchived ? "ARCHIVED " : "SNAPSHOT "}
                {pack.data.snapshot_version}
              </LibChip>
            </CardHead>
            <Rows
              rows={[
                ["Capabilities", String(pack.data.capabilities.length)],
                ["Generated", isoDate(pack.data.generated_at)],
                ["Schema", `v${pack.data.schema_version}`],
                ...(isArchived
                  ? ([["Visibility", "ARCHIVED — HIDDEN FROM LIBRARY"]] as [
                      string,
                      string,
                    ][])
                  : []),
                ...Object.entries(pack.data.crawl_metadata ?? {})
                  .slice(0, 3)
                  .map(
                    ([k, v]) => [k.replace(/_/g, " "), v.toUpperCase()] as [string, string],
                  ),
              ]}
            />
            <CardNote>
              {isArchived
                ? "Archived hides this version from the Library — it is NOT deleted or edited. Any run that froze this snapshot still resolves it, so historical readings replay unchanged."
                : "Each run freezes its own slice of this snapshot, so readings stay reproducible. Archiving hides a version from the Library without editing or deleting it — distinct from a crawl, which re-generates a fresh pack."}
            </CardNote>
            <button
              type="button"
              className="v2-lib-cardact v2-mono"
              onClick={() => onArchive(pack.data.snapshot_version, !isArchived)}
              disabled={archiving}
            >
              {archiving
                ? "WORKING…"
                : isArchived
                  ? "UNARCHIVE — SHOW IN LIBRARY"
                  : "ARCHIVE — HIDE FROM LIBRARY"}
            </button>
          </Card>
        )}
        {pack.state === "ready" &&
          pack.data.capabilities.slice(0, LANDING_CAPABILITY_CAP).map((name) => (
            <Card key={name}>
              <CardHead name={name}>
                <LibChip>CAPABILITY</LibChip>
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
                <LibChip strong>{pack.data.capabilities.length} TOTAL</LibChip>
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
            <LibChip>GENERATED — NEVER AUTHORED</LibChip>
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
            reading. To drop a capability, remove it from the crawl setup and re-crawl;
            the next snapshot is a fresh pack without it. (Archiving a whole version
            only hides it from the Library — it never edits pack contents.) The crawl
            itself waits on the walker.
          </CardNote>
          <CardLink href="/personas/crawl-setup">CRAWL SETUP + RE-CRAWL →</CardLink>
        </Card>
      </CardGrid>
    </Section>
  );
}

function PersonaPacksSection({
  personas,
  builtAt,
}: {
  personas: Fetchable<ActivePersonasResponse>;
  // ISO build date of the active pack, or null when unknown — see #47 above.
  builtAt: string | null;
}) {
  // #47 persona-age nudge: whole months since the active pack was built, and
  // whether that crosses the soft staleness threshold. Display-only.
  const ageMonths = builtAt != null ? monthsSince(builtAt) : null;
  const isStale = ageMonths != null && ageMonths >= PERSONA_PACK_STALE_MONTHS;
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
              <LibChip>STARTER · PLACEHOLDER</LibChip>
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
              <LibChip strong>{personas.data.pack_version}</LibChip>
            </CardHead>
            <Rows
              rows={[
                ["Personas", String(personas.data.personas.length)],
                ["Status", "PROMOTED · USED BY NEW RUNS"],
                ...(leading ? ([["Leading", leading]] as [string, string][]) : []),
                ...(builtAt
                  ? ([["Built", isoDate(builtAt)]] as [string, string][])
                  : []),
                ["Graded", "UNGRADED — CALIBRATION LEDGER EMPTY"],
              ]}
            />
            {/* #47 persona-age nudge: soft, non-blocking rebuild suggestion once
                the pack passes the staleness threshold. No auto-action. */}
            {isStale && ageMonths != null && (
              <CardNote>
                These personas were built {ageMonths} month
                {ageMonths === 1 ? "" : "s"} ago — if your customers or product
                have moved on since, consider rebuilding the pack to keep new
                readings grounded in recent behavior. Saved runs are unaffected.
              </CardNote>
            )}
            <CardLink href="/personas/latest">BROWSE PERSONAS →</CardLink>
          </Card>
        )}
        <Card ghost>
          <CardHead name="Build a new pack">
            <LibChip>BUILDER</LibChip>
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
            <LibChip>AUTHORED IN WIZARD</LibChip>
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
        <LibChip>DERIVED FROM RUNS</LibChip>
      </CardHead>
      <p className="v2-lib-stim-prose">{stimulus.prose}</p>
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
            <span key="runs" className="v2-lib-stim-runs">
              {shownRuns.map((run) => (
                <span key={run.id} className="v2-lib-stim-run">
                  <span className={run.status === "running" ? "v2-lib-carrier" : undefined}>
                    {runDesignator(run.id)} · {run.status.toUpperCase()}
                  </span>
                </span>
              ))}
              {moreRuns > 0 && <span className="v2-lib-stim-run">+{moreRuns} MORE</span>}
            </span>,
          ],
        ]}
      />
      <CardLink href={`/simulations/${newestRun.id}`}>OPEN RUN →</CardLink>
    </Card>
  );
}

// ── sample-workspace seeding (Console-styled port of SampleWorkspaceCard) ────
//
// The legacy SampleWorkspaceCard styles itself from the live "paper" TOKENS,
// which would render a light card inside the dark Console. This port keeps the
// EXACT same behaviour — detectEmpty probe (GET /personas is_starter + GET
// /capabilities 404), click-only seed, success copy, hard reload, 409 + error
// handling — and only swaps the surface to v2 tokens. No data or logic changes.

function SampleWorkspaceCardV2() {
  const [visible, setVisible] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seeded, setSeeded] = useState<SampleWorkspaceResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    const is404 = async (probe: () => Promise<unknown>) => {
      try {
        await probe();
        return false; // pack exists — nothing to seed
      } catch (e) {
        return e instanceof ApiError && e.status === 404;
      }
    };
    // Personas need their own probe: a starter pack returns 200 but means the
    // tenant has no real personas yet (#212), so it counts as empty.
    const noRealPersonas = async () => {
      try {
        const res = await getActivePersonas();
        return res.is_starter === true;
      } catch (e) {
        return e instanceof ApiError && e.status === 404;
      }
    };
    (async () => {
      const [noPersonas, noCapabilities] = await Promise.all([
        noRealPersonas(),
        is404(getCapabilities),
      ]);
      if (!cancelled && noPersonas && noCapabilities) {
        setVisible(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!visible) return null;

  async function handleGenerate() {
    setWorking(true);
    setError(null);
    try {
      const res = await generateSampleWorkspace();
      setSeeded(res);
      // Give the PM a beat to read the confirmation, then refetch the page.
      window.setTimeout(() => window.location.reload(), 1600);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError(
          "This workspace already has data — the sample is only for empty workspaces.",
        );
      } else if (e instanceof Error) {
        setError(`Could not generate the sample workspace: ${e.message}`);
      } else {
        setError("Could not generate the sample workspace.");
      }
      setWorking(false);
    }
  }

  return (
    <div className="v2-lib-sample">
      <div className="v2-lib-sample-title">Try a sample workspace</div>
      <p className="v2-lib-sample-body">
        Seed this workspace with Streamly, a sample streaming product — 6 personas and 2
        crawled capabilities — so you can run simulations right away. Nothing is generated
        until you click.
      </p>
      {seeded ? (
        <div className="v2-lib-sample-done">
          Seeded <span className="v2-tnum">{seeded.persona_count}</span> personas (pack{" "}
          <code className="v2-mono">{seeded.persona_pack_version}</code>) and{" "}
          <span className="v2-tnum">{seeded.capabilities.length}</span> capabilities (pack{" "}
          <code className="v2-mono">{seeded.feature_pack_version}</code>). Reloading…
        </div>
      ) : (
        <Button
          variant="primary"
          onClick={handleGenerate}
          aria-busy={working}
          // `disabled` is a native button attribute the shared Button forwards
          // via {...rest} but doesn't expose on its public HTMLAttributes type;
          // pass it through a typed spread rather than editing the primitive.
          {...({ disabled: working } as { disabled: boolean })}
        >
          {working ? "Generating…" : "Generate sample workspace"}
        </Button>
      )}
      {error && (
        <div role="alert" className="v2-lib-sample-error">
          {error}
        </div>
      )}
    </div>
  );
}

"use client";

// Feature pack — the full capability browser (Library IA + scale, #207).
//
// The Library landing previews a bounded handful of capabilities; this page
// holds the whole pack and stays readable as the crawler finds more — search
// (name substring), an A–Z group toggle, and dependency-free pagination. Each
// capability row links to its reverse-PRD + reverse-Figma record at
// /personas/capability/{name} (the #236 detail route).
//
// Data source: GET /capabilities (the names-only FeaturePackManifest — version,
// generated_at, capability names). It serves the LATEST snapshot, so only the
// latest version is reachable today; the [version] segment matches the IA's
// future multi-version shape, and a mismatched version renders an honest note
// rather than a wrong pack. Role / domain grouping waits on the crawler
// (sidira-crawler#18) and a richer summary endpoint — A–Z is the interim view.

import Link from "next/link";
import { Fragment, useEffect, useMemo, useState } from "react";
import { ApiError, getCapabilities, type FeaturePackManifest } from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO } from "@/lib/design";
import {
  BodyNote,
  Card,
  CardGrid,
  CardHead,
  CardLink,
  Chip,
  EmptyState,
  ErrorNote,
  isoDate,
  LibraryStyles,
  PendingNote,
  Rows,
  Section,
} from "@/components/library/furniture";

const PAGE_SIZE = 24;

type GroupBy = "none" | "alpha";

type Fetchable<T> =
  | { state: "loading" }
  | { state: "ready"; data: T }
  | { state: "empty" }
  | { state: "error"; message: string };

// First letter, uppercased; anything non-alphabetic buckets under "#".
function bucketOf(name: string): string {
  const c = name.trim().charAt(0).toUpperCase();
  return c >= "A" && c <= "Z" ? c : "#";
}

export default function FeaturePackPage({ params }: { params: { version: string } }) {
  const requestedVersion = decodeURIComponent(params.version);
  const [pack, setPack] = useState<Fetchable<FeaturePackManifest>>({ state: "loading" });
  const [query, setQuery] = useState("");
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [page, setPage] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getCapabilities();
        if (cancelled) return;
        setPack(data.capabilities.length === 0 ? { state: "empty" } : { state: "ready", data });
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) setPack({ state: "empty" });
        else setPack({ state: "error", message: e instanceof Error ? e.message : "request failed" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Search + group-by reset to the first page.
  useEffect(() => {
    setPage(0);
  }, [query, groupBy]);

  const latestVersion = pack.state === "ready" ? pack.data.snapshot_version : null;

  const ordered = useMemo(() => {
    if (pack.state !== "ready") return [] as string[];
    const q = query.trim().toLowerCase();
    const filtered = q
      ? pack.data.capabilities.filter((name) => name.toLowerCase().includes(q))
      : pack.data.capabilities;
    return groupBy === "alpha"
      ? [...filtered].sort((a, b) => a.localeCompare(b))
      : filtered;
  }, [pack, query, groupBy]);

  const total = ordered.length;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const start = safePage * PAGE_SIZE;
  const pageItems = ordered.slice(start, start + PAGE_SIZE);

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
        <Link href="/personas" className="lib-link" style={{ fontSize: 12.5, fontWeight: 500 }}>
          ← Library
        </Link>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>
          Feature pack
        </h1>
        {pack.state === "ready" && (
          <span
            style={{
              fontFamily: FONT_MONO,
              fontSize: 11,
              color: TOKENS.inkMuted,
              letterSpacing: "0.06em",
            }}
          >
            SNAPSHOT {pack.data.snapshot_version} · {isoDate(pack.data.generated_at)} ·{" "}
            {pack.data.capabilities.length} CAPABILITIES
          </span>
        )}
      </header>

      <div style={{ padding: 24 }}>
        {pack.state === "loading" && <PendingNote>Loading the feature pack…</PendingNote>}
        {pack.state === "error" && (
          <ErrorNote>The feature pack could not be loaded: {pack.message}</ErrorNote>
        )}
        {pack.state === "empty" && (
          <EmptyState>
            No feature pack yet — the pack is a generated snapshot of your as-built product. Start
            the first crawl from{" "}
            <Link href="/personas/crawl-setup" className="lib-link">
              crawl setup
            </Link>
            ; the latest pointer flips once a clean crawl lands.
          </EmptyState>
        )}

        {pack.state === "ready" && latestVersion && requestedVersion !== latestVersion && (
          <EmptyState>
            Only the latest snapshot is browsable. You asked for{" "}
            <strong>{requestedVersion}</strong>, but the current pack is{" "}
            <strong>{latestVersion}</strong> — older snapshots aren&apos;t served yet. Open the{" "}
            <Link
              href={`/personas/feature-pack/${encodeURIComponent(latestVersion)}`}
              className="lib-link"
            >
              latest pack
            </Link>{" "}
            instead.
          </EmptyState>
        )}

        {pack.state === "ready" && requestedVersion === latestVersion && (
          <Section label={`All capabilities — ${pack.data.capabilities.length}`}>
            <Controls
              query={query}
              onQuery={setQuery}
              groupBy={groupBy}
              onGroupBy={setGroupBy}
            />
            <BodyNote>
              Grouping by product domain is pending the crawler (sidira-crawler#18); A–Z is an
              interim view over the capability names.
            </BodyNote>

            {total === 0 ? (
              <BodyNote>
                No capabilities match “{query.trim()}”. Clear the search to see the full pack.
              </BodyNote>
            ) : (
              <>
                <CapabilityGrid
                  items={pageItems}
                  snapshot={pack.data.snapshot_version}
                  grouped={groupBy === "alpha"}
                />
                <Pager
                  page={safePage}
                  pageCount={pageCount}
                  total={total}
                  start={start}
                  shown={pageItems.length}
                  onPrev={() => setPage((p) => Math.max(0, p - 1))}
                  onNext={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                />
              </>
            )}
          </Section>
        )}
      </div>
    </main>
  );
}

// ── capability grid ───────────────────────────────────────────────────────

function CapabilityGrid({
  items,
  snapshot,
  grouped,
}: {
  items: string[];
  snapshot: string;
  grouped: boolean;
}) {
  let lastBucket = "";
  return (
    <CardGrid>
      {items.map((name) => {
        const bucket = bucketOf(name);
        const showHeading = grouped && bucket !== lastBucket;
        lastBucket = bucket;
        return (
          <Fragment key={name}>
            {showHeading && <GroupHeading letter={bucket} />}
            <Card>
              <CardHead name={name}>
                <Chip>CAPABILITY</Chip>
              </CardHead>
              <Rows
                rows={[
                  ["Snapshot", snapshot],
                  ["Artifacts", "REVERSE PRD + REVERSE FIGMA"],
                ]}
              />
              <CardLink href={`/personas/capability/${encodeURIComponent(name)}`}>
                OPEN CAPABILITY →
              </CardLink>
            </Card>
          </Fragment>
        );
      })}
    </CardGrid>
  );
}

// Full-width letter divider inside the grid (§7 zone eyebrow, mono caps).
function GroupHeading({ letter }: { letter: string }) {
  return (
    <span
      style={{
        gridColumn: "1 / -1",
        fontFamily: FONT_MONO,
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: "0.12em",
        color: TOKENS.inkMuted,
        paddingTop: 6,
        paddingBottom: 4,
        borderBottom: `1px solid ${TOKENS.rule}`,
      }}
    >
      {letter}
    </span>
  );
}

// ── controls ──────────────────────────────────────────────────────────────

function Controls({
  query,
  onQuery,
  groupBy,
  onGroupBy,
}: {
  query: string;
  onQuery: (v: string) => void;
  groupBy: GroupBy;
  onGroupBy: (g: GroupBy) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        flexWrap: "wrap",
        marginTop: 14,
      }}
    >
      <input
        type="text"
        value={query}
        onChange={(e) => onQuery(e.target.value)}
        placeholder="Search capabilities…"
        aria-label="Search capabilities"
        style={{
          // §7.1 inputs radius 2; §7.4 paper-elevated input, no inset shadow.
          flex: "1 1 240px",
          minWidth: 200,
          maxWidth: 360,
          background: TOKENS.paperElevated,
          border: `1px solid ${TOKENS.rule}`,
          borderRadius: 2,
          color: TOKENS.ink,
          fontFamily: FONT_SANS,
          fontSize: 13,
          padding: "7px 10px",
        }}
      />
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span
          style={{
            fontSize: 10,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: TOKENS.inkMuted,
          }}
        >
          Group
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          <GroupToggle active={groupBy === "none"} onClick={() => onGroupBy("none")}>
            NONE
          </GroupToggle>
          <GroupToggle active={groupBy === "alpha"} onClick={() => onGroupBy("alpha")}>
            A–Z
          </GroupToggle>
        </div>
      </div>
    </div>
  );
}

// §7.7 quiet / row-action button — mono designator, radius 2. The active option
// inverts to paper-on-ink (a selected toggle, never ink-on-ink).
function GroupToggle({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10.5,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        background: active ? TOKENS.ink : "transparent",
        color: active ? TOKENS.paper : TOKENS.inkMuted,
        border: `1px solid ${active ? TOKENS.ink : TOKENS.rule}`,
        borderRadius: 2,
        padding: "3px 9px",
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

// ── pager ─────────────────────────────────────────────────────────────────

function Pager({
  page,
  pageCount,
  total,
  start,
  shown,
  onPrev,
  onNext,
}: {
  page: number;
  pageCount: number;
  total: number;
  start: number;
  shown: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  if (pageCount <= 1) return null;
  const from = total === 0 ? 0 : start + 1;
  const to = start + shown;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        marginTop: 18,
        paddingTop: 14,
        borderTop: `1px solid ${TOKENS.rule}`,
      }}
    >
      <PagerButton onClick={onPrev} disabled={page === 0}>
        ← Prev
      </PagerButton>
      <PagerButton onClick={onNext} disabled={page >= pageCount - 1}>
        Next →
      </PagerButton>
      <span
        style={{
          fontFamily: FONT_MONO,
          fontSize: 11,
          letterSpacing: "0.04em",
          color: TOKENS.inkMuted,
        }}
      >
        SHOWING {from}–{to} OF {total} · PAGE {page + 1}/{pageCount}
      </span>
    </div>
  );
}

// §7.7 secondary action — transparent, ink text, rule border. Disabled stays
// visible at opacity 0.5 (never hidden, never recolored).
function PagerButton({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        background: "transparent",
        color: TOKENS.ink,
        border: `1px solid ${TOKENS.rule}`,
        borderRadius: 2,
        padding: "5px 12px",
        fontFamily: FONT_SANS,
        fontSize: 12.5,
        fontWeight: 500,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {children}
    </button>
  );
}

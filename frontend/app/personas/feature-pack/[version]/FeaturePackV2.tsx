"use client";

// ───────────────────────────────────────────────────────────────────────────
// /personas/feature-pack/[version] — the v2 dark "Reading Console" reskin.
//
// FORK-AND-RESTYLE of FeaturePackLegacy.tsx (the FROZEN source of truth for ALL
// behaviour). This file reproduces every data load, state branch, search /
// group-by / pagination computation, honesty/disclosure branch, <Link> and
// button the legacy page has — byte-for-byte in LOGIC — and changes ONLY the
// presentation (markup + CSS classes + layout) into the dark Console language
// of design-rethink/mocks/feature-pack.html.
//
// It renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar). The body is scoped under a single `.rconsole` wrapper so the copied
// dark token block applies; we do NOT emit the mock's own .app/.rail/.topbar
// (the shell owns that chrome).
//
// Honesty law (DESIGN.md §8.1): NO fabricated fields. The legacy
// FeaturePackSummary carries NO per-capability coverage reading, no graded /
// uncalibrated tally, no domain counts — so this reskin adopts the mock's dark
// Console *grammar* (palette, logbook table, group headings, controls, pager)
// but renders ONLY the fields the data actually has (name, snapshot, roles /
// domain via grouping, artifacts string). No coverage column, no poster, no
// calibration tally. Every disclosure / empty-state copy survives verbatim.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { Fragment, useEffect, useMemo, useState } from "react";
import { ApiError, getCapabilitySummary, type FeaturePackSummary } from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";

const PAGE_SIZE = 24;
// Capabilities with no role (by-role view) or no domain (by-domain view) bucket
// here, sorted last.
const UNSCOPED = "UNSCOPED";

type GroupBy = "none" | "alpha" | "role" | "domain";

// One displayed row: a capability under a heading bucket. Under "role" a
// multi-role capability expands to one entry per role (it genuinely belongs to
// each), so a name can appear more than once; key on bucket+name. "domain" is
// single-membership (one bucket per capability).
type Entry = { name: string; bucket: string };

// Named buckets sort alphabetically, UNSCOPED always last, then by capability
// name within a bucket. Shared by the by-role and by-domain views.
function byBucketThenName(a: Entry, b: Entry): number {
  if (a.bucket !== b.bucket) {
    if (a.bucket === UNSCOPED) return 1;
    if (b.bucket === UNSCOPED) return -1;
    return a.bucket.localeCompare(b.bucket);
  }
  return a.name.localeCompare(b.name);
}

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

// isoDate — the same short ISO-date helper the legacy furniture exposes; inlined
// here so the dark reskin carries no light-paper furniture imports.
function isoDate(iso: string): string {
  try {
    return new Date(iso).toISOString().slice(0, 10);
  } catch {
    return iso;
  }
}

// ── scoped dark Console tokens + layout (palette mirrors RCONSOLE_CSS /
//    feature-pack.html). The `.fp-bleed` helper breaks the header + body bands
//    out of the .v2-appmain section padding, then a centered `.fp-wrap` re-pads.
const FP_CSS = `
.rconsole{
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#F2F4F8; --text:#C6CCD8; --text-mut:#929BAE; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894;
  --spread:#C8B68A; --spread-dim:#90815F;
  --edge-warn:#C9A227; --alert:#F0683C;
  --r-well:4px; --r-panel:8px; --r-frame:10px;
  --font-sans:var(--v2-font-sans,var(--font-sans,"Geist",system-ui,sans-serif));
  --font-mono:var(--v2-font-mono,var(--font-mono,ui-monospace,"Geist Mono",monospace));
  color:var(--text); font-family:var(--font-sans); font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased; font-variant-numeric:tabular-nums;
  overflow-x:hidden;
}
.rconsole *{box-sizing:border-box; font-variant-numeric:tabular-nums;}
.rconsole a{color:inherit; text-decoration:none;}
.rconsole ::selection{background:rgba(72,239,202,.22); color:var(--text-hi);}
.rconsole .mono{font-family:var(--font-mono);}

/* full-bleed bands: pull out of the .v2-appmain section padding so the header
   and body span edge-to-edge; the centered wrap re-pads. */
.rconsole .fp-bleed{
  margin-left:calc(-1 * var(--space-section,48px));
  margin-right:calc(-1 * var(--space-section,48px));
}
.rconsole .fp-bleed.top{margin-top:calc(-1 * var(--space-section,48px));}
.rconsole .fp-wrap{max-width:1320px; margin:0 auto; padding:0 32px;}

/* header band */
.rconsole .fp-header{
  border-bottom:1px solid rgba(51,64,92,.5); padding:36px 0 28px;
}
.rconsole .crumb{display:inline-flex; align-items:center; gap:7px; font-size:13px;
  font-weight:500; color:var(--text-mut); margin-bottom:20px;}
.rconsole .crumb:hover{color:var(--text-hi);}
.rconsole h1.fp-title{font-size:2rem; font-weight:600; letter-spacing:-.025em;
  line-height:1.08; color:var(--text-hi); margin:0; text-wrap:balance;}
.rconsole .fp-prov{display:flex; flex-wrap:wrap; align-items:baseline; gap:8px;
  margin-top:16px; font-family:var(--font-mono); font-size:11px;
  letter-spacing:.03em; color:var(--text-mut);}
.rconsole .fp-prov .pk{letter-spacing:.1em; text-transform:uppercase; opacity:.8;}
.rconsole .fp-prov .pv{color:var(--text);}
.rconsole .fp-prov .sep{opacity:.4; margin:0 4px;}

/* body band */
.rconsole .fp-body{padding:40px 0 64px;}

/* notes (loading / error / empty / stale snapshot) — a data condition, not an
   alarm: hairline / border-left rule, message in ink, no tint. */
.rconsole .note{border:1px solid rgba(51,64,92,.5); border-radius:var(--r-panel);
  padding:16px 18px; background:var(--console-800); font-size:14px;
  color:var(--text); line-height:1.55; max-width:74ch;}
.rconsole .note.alert{border-color:rgba(240,104,60,.55);}
.rconsole .note.warn{border-left:2px solid var(--edge-warn);}
.rconsole .note a{color:var(--text-hi); text-decoration:underline;
  text-underline-offset:2px; text-decoration-color:rgba(146,155,174,.4);}
.rconsole .note a:hover{text-decoration-color:var(--text-hi);}
.rconsole .note strong{color:var(--text-hi); font-weight:600;}

/* section head */
.rconsole .sec-head{display:flex; align-items:baseline; justify-content:space-between;
  gap:24px; flex-wrap:wrap; border-bottom:1px solid rgba(51,64,92,.5);
  padding-bottom:14px; margin-bottom:24px;}
.rconsole .sec-title{font-size:1.125rem; font-weight:550; color:var(--text-hi);
  letter-spacing:-.01em;}
.rconsole .sec-count{font-family:var(--font-mono); font-size:11px; letter-spacing:.06em;
  color:var(--text-mut); text-transform:uppercase;}

/* controls — search + group-by segmented toggle */
.rconsole .controls{display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  margin-bottom:16px;}
.rconsole .search{position:relative; flex:1 1 280px; max-width:360px; min-width:200px;}
.rconsole .search input{width:100%; height:36px; background:var(--console-700);
  border:1px solid rgba(51,64,92,.7); border-radius:var(--r-well);
  color:var(--text-hi); font-family:var(--font-sans); font-size:14px;
  padding:0 12px; outline:none; transition:border-color .14s;}
.rconsole .search input::placeholder{color:rgba(146,155,174,.7);}
.rconsole .search input:focus{border-color:var(--signal-dim);}
.rconsole .grp{display:flex; align-items:center; gap:10px;}
.rconsole .grp .glab{font-family:var(--font-mono); font-size:10px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--text-mut);}
.rconsole .seg-toggle{display:flex; border:1px solid rgba(51,64,92,.7);
  border-radius:var(--r-well); overflow:hidden;}
.rconsole .seg-toggle button{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.05em; text-transform:uppercase; background:transparent;
  color:var(--text-mut); border:none; padding:7px 13px; cursor:pointer;
  border-right:1px solid rgba(51,64,92,.5); transition:color .14s,background .14s;}
.rconsole .seg-toggle button:last-child{border-right:none;}
.rconsole .seg-toggle button:hover{color:var(--text-hi); background:var(--console-800);}
.rconsole .seg-toggle button.on{color:var(--text-hi); background:var(--console-750);}

.rconsole .body-note{font-size:13px; color:var(--text-mut); line-height:1.55;
  max-width:74ch; margin-bottom:20px;}

/* logbook (capability table) */
.rconsole .logbook{border:1px solid rgba(51,64,92,.5); border-radius:var(--r-panel);
  overflow:hidden; background:var(--console-800);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.rconsole .lb-head,.rconsole .lb-row{display:grid;
  grid-template-columns:minmax(320px,2fr) 148px; align-items:center; gap:18px;
  padding:0 22px;}
.rconsole .lb-head{height:38px; border-bottom:1px solid rgba(51,64,92,.5);
  font-family:var(--font-mono); font-size:10.5px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--text-mut); background:var(--console-850);}
.rconsole .lb-row{min-height:52px; border-bottom:1px solid rgba(51,64,92,.3);
  color:inherit; position:relative; transition:background .12s; padding-top:8px;
  padding-bottom:8px;}
.rconsole .lb-row:last-child{border-bottom:none;}
.rconsole .lb-row:hover{background:var(--console-750);}
.rconsole .cap-name{display:flex; flex-direction:column; gap:3px; min-width:0;}
.rconsole .cap-name .nm{font-size:14.5px; font-weight:500; color:var(--text-hi);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0;}
.rconsole .cap-name .meta{font-family:var(--font-mono); font-size:10.5px;
  color:var(--text-mut); letter-spacing:.02em; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis;}
.rconsole .openlink{font-family:var(--font-mono); font-size:11px; letter-spacing:.04em;
  color:var(--text-mut); display:inline-flex; align-items:center; gap:5px;
  justify-self:end; transition:color .14s;}
.rconsole .lb-row:hover .openlink{color:var(--text-hi);}

/* group heading row — domain / role / A–Z partition */
.rconsole .grp-head{grid-column:1/-1; display:flex; align-items:center; gap:12px;
  padding:14px 0 8px; border-bottom:1px solid rgba(51,64,92,.5);
  border-top:1px solid rgba(51,64,92,.3);}
.rconsole .grp-head:first-child{border-top:none;}
.rconsole .grp-head .gname{font-family:var(--font-mono); font-size:11px;
  font-weight:500; letter-spacing:.1em; text-transform:uppercase; color:var(--text-hi);}
.rconsole .grp-head .grule{flex:1; height:1px; background:rgba(51,64,92,.4);}

/* the grp-head sits inside the grid so it spans full-bleed — pad it back to row
   inset via the logbook's own 22px gutter. */
.rconsole .logbook .grp-head{padding-left:22px; padding-right:22px;}

/* pager */
.rconsole .pager{display:flex; align-items:center; gap:14px; margin-top:24px;
  padding-top:16px; border-top:1px solid rgba(51,64,92,.5);}
.rconsole .pbtn{background:transparent; color:var(--text);
  border:1px solid rgba(51,64,92,.7); border-radius:var(--r-well); height:34px;
  padding:0 14px; font-family:var(--font-sans); font-size:13px; font-weight:500;
  cursor:pointer; transition:background .14s;}
.rconsole .pbtn:hover:not(:disabled){background:var(--console-800); color:var(--text-hi);}
.rconsole .pbtn:disabled{color:var(--text-faint); border-color:rgba(51,64,92,.4);
  cursor:not-allowed;}
.rconsole .pmeta{font-family:var(--font-mono); font-size:11px; letter-spacing:.04em;
  color:var(--text-mut); margin-left:4px;}
.rconsole .pmeta .strong{color:var(--text);}

.rconsole a:focus-visible,.rconsole button:focus-visible,.rconsole input:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px; border-radius:var(--r-well);}

@media(max-width:760px){
  .rconsole .lb-head{display:none;}
  .rconsole .lb-row{grid-template-columns:1fr auto; min-height:auto;
    padding:14px 16px; gap:8px;}
}
@media(max-width:1024px){
  .rconsole .fp-bleed{
    margin-left:calc(-1 * var(--space-room,24px));
    margin-right:calc(-1 * var(--space-room,24px));
  }
  .rconsole .fp-bleed.top{margin-top:calc(-1 * var(--space-room,24px));}
}
@media(prefers-reduced-motion:reduce){.rconsole *{animation:none!important;}}
`;

export default function FeaturePackV2({ params }: { params: { version: string } }) {
  const requestedVersion = decodeURIComponent(params.version);
  const [pack, setPack] = useState<Fetchable<FeaturePackSummary>>({ state: "loading" });
  const [query, setQuery] = useState("");
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [page, setPage] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getCapabilitySummary();
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

  const ordered = useMemo<Entry[]>(() => {
    if (pack.state !== "ready") return [];
    const q = query.trim().toLowerCase();
    const caps = q
      ? pack.data.capabilities.filter((c) => c.name.toLowerCase().includes(q))
      : pack.data.capabilities;

    if (groupBy === "role") {
      // Expand to one entry per (capability, role); roleless → UNSCOPED.
      const entries: Entry[] = [];
      for (const c of caps) {
        if (c.roles.length === 0) entries.push({ name: c.name, bucket: UNSCOPED });
        else for (const role of c.roles) entries.push({ name: c.name, bucket: role });
      }
      return entries.sort(byBucketThenName);
    }

    if (groupBy === "domain") {
      // Single-membership: each capability sits under its synthesized domain;
      // domainless → UNSCOPED.
      const entries: Entry[] = caps.map((c) => ({ name: c.name, bucket: c.domain || UNSCOPED }));
      return entries.sort(byBucketThenName);
    }

    const entries = caps.map((c) => ({ name: c.name, bucket: bucketOf(c.name) }));
    return groupBy === "alpha"
      ? entries.sort((a, b) => a.name.localeCompare(b.name))
      : entries;
  }, [pack, query, groupBy]);

  const total = ordered.length;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const start = safePage * PAGE_SIZE;
  const pageItems = ordered.slice(start, start + PAGE_SIZE);

  return (
    <AppShellV2 activeNav="personas" title="Feature pack" surface="console">
      <div className="rconsole">
        <style>{FP_CSS}</style>

      {/* ── header band ─────────────────────────────────────────── */}
      <div className="fp-bleed top">
        <div className="fp-wrap">
          <header className="fp-header">
            <Link href="/personas" className="crumb">
              ← Library
            </Link>
            <h1 className="fp-title">Feature pack</h1>
            {pack.state === "ready" && (
              <div className="fp-prov">
                <span className="pk">Snapshot</span>
                <span className="pv">{pack.data.snapshot_version}</span>
                <span className="sep">·</span>
                <span className="pv">{isoDate(pack.data.generated_at)}</span>
                <span className="sep">·</span>
                <span className="pv">{pack.data.capabilities.length} CAPABILITIES</span>
              </div>
            )}
          </header>
        </div>
      </div>

      {/* ── body band ───────────────────────────────────────────── */}
      <div className="fp-bleed">
        <div className="fp-wrap">
          <section className="fp-body">
            {pack.state === "loading" && (
              <div className="note">Loading the feature pack…</div>
            )}
            {pack.state === "error" && (
              <div className="note alert" role="alert">
                The feature pack could not be loaded: {pack.message}
              </div>
            )}
            {pack.state === "empty" && (
              <div className="note">
                No feature pack yet — the pack is a generated snapshot of your as-built product. Start
                the first crawl from{" "}
                <Link href="/personas/crawl-setup">crawl setup</Link>; the latest pointer flips once a
                clean crawl lands.
              </div>
            )}

            {pack.state === "ready" && latestVersion && requestedVersion !== latestVersion && (
              <div className="note">
                Only the latest snapshot is browsable. You asked for{" "}
                <strong>{requestedVersion}</strong>, but the current pack is{" "}
                <strong>{latestVersion}</strong> — older snapshots aren&apos;t served yet. Open the{" "}
                <Link href={`/personas/feature-pack/${encodeURIComponent(latestVersion)}`}>
                  latest pack
                </Link>{" "}
                instead.
              </div>
            )}

            {pack.state === "ready" && requestedVersion === latestVersion && (
              <>
                <div className="sec-head">
                  <div className="sec-title">All capabilities</div>
                  <div className="sec-count">{pack.data.capabilities.length}</div>
                </div>

                <Controls
                  query={query}
                  onQuery={setQuery}
                  groupBy={groupBy}
                  onGroupBy={setGroupBy}
                />
                <div className="body-note">
                  Group by product domain, role, or A–Z. Role grouping lists a capability under each
                  role it serves; domain grouping places it under the one product area the crawler
                  synthesized for it, with anything ungrouped under {UNSCOPED}.
                </div>

                {total === 0 ? (
                  <div className="body-note">
                    No capabilities match “{query.trim()}”. Clear the search to see the full pack.
                  </div>
                ) : (
                  <>
                    <CapabilityGrid
                      items={pageItems}
                      snapshot={pack.data.snapshot_version}
                      grouped={groupBy !== "none"}
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
              </>
            )}
          </section>
        </div>
      </div>
      </div>
    </AppShellV2>
  );
}

// ── capability logbook ─────────────────────────────────────────────────────

function CapabilityGrid({
  items,
  snapshot,
  grouped,
}: {
  items: Entry[];
  snapshot: string;
  grouped: boolean;
}) {
  let lastBucket = "";
  return (
    <div className="logbook">
      <div className="lb-head">
        <span>Capability</span>
        <span>Artifacts</span>
      </div>
      {items.map((entry) => {
        const showHeading = grouped && entry.bucket !== lastBucket;
        lastBucket = entry.bucket;
        return (
          <Fragment key={`${entry.bucket}:${entry.name}`}>
            {showHeading && <GroupHeading label={entry.bucket} />}
            <Link
              className="lb-row"
              href={`/personas/capability/${encodeURIComponent(entry.name)}`}
            >
              <span className="cap-name">
                <span className="nm">{entry.name}</span>
                <span className="meta">SNAPSHOT {snapshot}</span>
              </span>
              <span className="openlink">REVERSE PRD + FIGMA →</span>
            </Link>
          </Fragment>
        );
      })}
    </div>
  );
}

// Full-width divider inside the logbook — a letter under A–Z, a role name under
// by-role, a domain under by-domain (UNSCOPED last).
function GroupHeading({ label }: { label: string }) {
  return (
    <div className="grp-head">
      <span className="gname">{label}</span>
      <span className="grule" />
    </div>
  );
}

// ── controls ────────────────────────────────────────────────────────────────

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
    <div className="controls">
      <label className="search">
        <input
          type="text"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search capabilities…"
          aria-label="Search capabilities"
        />
      </label>
      <div className="grp">
        <span className="glab">Group</span>
        <div className="seg-toggle" role="tablist">
          <button
            type="button"
            className={groupBy === "none" ? "on" : undefined}
            aria-pressed={groupBy === "none"}
            onClick={() => onGroupBy("none")}
          >
            None
          </button>
          <button
            type="button"
            className={groupBy === "alpha" ? "on" : undefined}
            aria-pressed={groupBy === "alpha"}
            onClick={() => onGroupBy("alpha")}
          >
            A–Z
          </button>
          <button
            type="button"
            className={groupBy === "role" ? "on" : undefined}
            aria-pressed={groupBy === "role"}
            onClick={() => onGroupBy("role")}
          >
            Roles
          </button>
          <button
            type="button"
            className={groupBy === "domain" ? "on" : undefined}
            aria-pressed={groupBy === "domain"}
            onClick={() => onGroupBy("domain")}
          >
            Domain
          </button>
        </div>
      </div>
    </div>
  );
}

// ── pager ───────────────────────────────────────────────────────────────────

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
    <div className="pager">
      <button type="button" className="pbtn" onClick={onPrev} disabled={page === 0}>
        ← Prev
      </button>
      <button
        type="button"
        className="pbtn"
        onClick={onNext}
        disabled={page >= pageCount - 1}
      >
        Next →
      </button>
      <span className="pmeta">
        SHOWING{" "}
        <span className="strong">
          {from}–{to}
        </span>{" "}
        OF <span className="strong">{total}</span> · PAGE {page + 1}/{pageCount}
      </span>
    </div>
  );
}

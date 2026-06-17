"use client";

// ───────────────────────────────────────────────────────────────────────────
// /personas/capability/[name] — the v2 LIGHT "Sheet" (Reading-Console record)
// reskin.
//
// FORK-AND-RESTYLE of CapabilityDetailLegacy.tsx (the FROZEN source of truth for
// ALL behaviour). This file reproduces every data load, state branch, honesty
// branch, conditional and <Link> the legacy record has — byte-for-byte in LOGIC
// — and changes ONLY the presentation (markup + scoped CSS classes + layout)
// into the light Sheet language of design-rethink/mocks/capability-detail.html.
// The dependency-free markdown renderer (Markdown / List / Inline / parseList …)
// is the legacy's content logic and is preserved byte-for-byte; only the leaf
// element class names / inline styles change.
//
// It renders INSIDE AppShellV2 surface="sheet" (the shell owns the dark Console
// rail + the appbar; surface="sheet" gives a light <main> with padding:0). The
// body is scoped under a single `.rsheet` wrapper so the copied RSHEET_CSS
// applies; we do NOT emit the mock's own .sheetbar/.record chrome — the shell
// owns the topbar. The `.rsheet` wrapper re-establishes the Sheet background +
// its own padding (the sheet <main> ships padding:0).
//
// HONESTY (DESIGN.md §8.1): no fabricated fields. The mock's embedded Console
// WELL "live estimate", noise-floor figure, settled-distribution poster, lift
// stamp and linked-simulations logbook all describe data the legacy capability
// read does NOT carry, so NONE are rendered here — only the snapshot / capture /
// name / roles / surfaces / entry-points / implicit-metric / reverse-PRD /
// reverse-Figma the legacy record actually loads. The ◇ hollow glyph marks the
// UNCALIBRATED state; no verdict shows on this record, so no verdict glyph
// appears.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
import AppShellV2 from "@/components/v2/AppShellV2";
import {
  ApiError,
  getCapability,
  type Capability,
  type CapabilityRecord,
  type ReverseFigma,
} from "@/lib/api";

type Fetchable<T> =
  | { state: "loading" }
  | { state: "ready"; data: T }
  | { state: "missing" }
  | { state: "error"; message: string };

// ── scoped light Sheet tokens (mirrors capability-detail.html: masthead title
//    block, Provenance Spine column, capability-map meta grid, reverse-PRD
//    document of record, reverse-Figma companion spec). Token-driven light
//    surface; re-establishes the Sheet background + own padding because the
//    AppShellV2 sheet <main> ships padding:0. ─────────────────────────────────
const RSHEET_CSS = `
.rsheet{
  --sheet:#F3F4F7; --sheet-raised:#FBFBFD; --sheet-sunk:#E6E8EE;
  --sheet-line:#D4D8E0; --sheet-ink:#1A2336; --sheet-mut:#5E6678;
  --sheet-signal:#00785F; --sheet-spread:#6F5E33;
  --spread-wash:rgba(200,182,138,.14);
  --r-well:4px; --r-panel:8px;
  --font-sans:var(--v2-font-sans,system-ui,sans-serif);
  --font-mono:var(--v2-font-mono,var(--font-mono,ui-monospace,"JetBrains Mono",monospace));
  --font-serif:"Newsreader",Georgia,serif;
  background:var(--sheet);
  color:var(--sheet-ink);
  font-family:var(--font-sans);
  font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
  font-variant-numeric:tabular-nums;
  min-height:100%;
  background-image:
    linear-gradient(rgba(26,35,54,.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(26,35,54,.018) 1px, transparent 1px);
  background-size:34px 34px;
}
.rsheet *{box-sizing:border-box; font-variant-numeric:tabular-nums;}
.rsheet a{color:inherit; text-decoration:none;}
.rsheet ::selection{background:rgba(0,120,95,.14);}
.rsheet .mono{font-family:var(--font-mono);}

/* shell: Provenance Spine + reading measure column */
.rsheet .shell{display:grid; grid-template-columns:188px minmax(0,1fr);
  max-width:1140px; margin:0 auto; padding:0 0 128px;}
.rsheet .reading{padding:0 56px; min-width:0;}

/* Provenance Spine */
.rsheet .spine{position:relative; border-right:.75px solid var(--sheet-line);
  padding:48px 24px 80px 0;}
.rsheet .spine-sticky{position:sticky; top:24px; display:flex; flex-direction:column;}
.rsheet .spine-title{font-family:var(--font-mono); font-size:10.5px;
  letter-spacing:.13em; text-transform:uppercase; color:var(--sheet-mut);
  margin:0 0 18px;}
.rsheet .spine-row{padding:11px 0; border-top:.75px solid var(--sheet-line);}
.rsheet .spine-row:first-of-type{border-top:none;}
.rsheet .spine-k{font-family:var(--font-mono); font-size:9.5px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--sheet-mut); display:block;
  margin-bottom:5px;}
.rsheet .spine-v{font-family:var(--font-mono); font-size:13px; color:var(--sheet-ink);
  line-height:1.4; display:block; overflow-wrap:anywhere;}
.rsheet .calib{display:inline-flex; align-items:baseline; gap:6px;
  color:var(--sheet-mut);}
.rsheet .glyph-hollow{color:var(--sheet-spread); font-size:12px;}
.rsheet .spine-note{font-family:var(--font-serif); font-size:13px; line-height:1.6;
  color:var(--sheet-mut); margin:18px 0 0; text-wrap:pretty;}

/* record title block */
.rsheet .rec-head{padding:48px 0 0; margin-bottom:48px;}
.rsheet .rec-kicker{font-family:var(--font-mono); font-size:11px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--sheet-mut); display:flex;
  align-items:center; gap:10px;}
.rsheet h1.rec-h1{margin:16px 0 0; font-family:var(--font-sans); font-size:2rem;
  line-height:1.08; font-weight:600; letter-spacing:-.025em; color:var(--sheet-ink);
  text-wrap:balance;}

/* capability-map meta grid */
.rsheet .meta{margin-bottom:48px;}
.rsheet .sec-eyebrow{font-family:var(--font-mono); font-size:10.5px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--sheet-mut);
  display:flex; align-items:center; gap:12px; margin:0 0 20px;}
.rsheet .sec-eyebrow::after{content:""; flex:1; height:1px;
  background:var(--sheet-line);}
.rsheet .meta-grid{display:grid; grid-template-columns:1fr 1fr; gap:22px 36px;}
.rsheet .meta-grid .full{grid-column:1 / -1;}
.rsheet .lbl{font-family:var(--font-mono); font-size:9.5px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--sheet-mut); display:block;
  margin-bottom:9px;}
.rsheet .chips{display:flex; flex-wrap:wrap; gap:6px;}
.rsheet .chip{font-family:var(--font-mono); font-size:11px; letter-spacing:.03em;
  border:1px solid var(--sheet-line); color:var(--sheet-mut);
  border-radius:var(--r-well); padding:3px 8px; white-space:nowrap;
  background:var(--sheet-raised);}
.rsheet .chip.role{color:var(--sheet-ink); border-color:#C3C8D2;}
.rsheet .metric-line{font-family:var(--font-serif); font-size:1.0625rem;
  line-height:1.6; color:var(--sheet-ink); margin:0; max-width:64ch;
  text-wrap:pretty;}
.rsheet .meta-empty{font-size:12px; color:var(--sheet-mut);}

/* reverse PRD — the document of record */
.rsheet .prd{margin-bottom:48px;}
.rsheet .prd-prov{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--sheet-mut); padding-bottom:14px;
  margin-bottom:30px; border-bottom:1px solid var(--sheet-line);
  overflow-wrap:anywhere;}
.rsheet .prd-body{max-width:68ch;}
.rsheet .code-inline{font-family:var(--font-mono); font-size:.86em;
  background:var(--sheet-sunk); border-radius:3px; padding:1px 5px;
  color:var(--sheet-ink);}

/* reverse Figma — companion spec */
.rsheet .figma{margin-bottom:48px;}
.rsheet .figma-prov{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--sheet-mut); padding-bottom:14px;
  margin-bottom:24px; border-bottom:1px solid var(--sheet-line);}
.rsheet .screen{border-top:1px solid var(--sheet-line); padding:24px 0;}
.rsheet .screen:first-of-type{border-top:none; padding-top:0;}
.rsheet .screen-head{display:flex; align-items:baseline; gap:10px; flex-wrap:wrap;}
.rsheet .screen-head .nm{font-family:var(--font-sans); font-size:1.125rem;
  font-weight:600; letter-spacing:-.01em; color:var(--sheet-ink);}
.rsheet .desig{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.04em;
  text-transform:uppercase; border:.75px solid var(--sheet-line);
  color:var(--sheet-mut); border-radius:var(--r-well); padding:2px 7px;
  white-space:nowrap;}
.rsheet .comp-list{margin-top:16px; padding-left:18px;
  border-left:1px solid var(--sheet-line); display:flex; flex-direction:column;
  gap:16px;}
.rsheet .comp .row{display:flex; align-items:baseline; gap:8px; flex-wrap:wrap;}
.rsheet .comp .crole{font-size:12px; color:var(--sheet-mut);}
.rsheet .comp .ctext{font-family:var(--font-serif); font-size:.9375rem;
  line-height:1.5; margin:6px 0 0; color:var(--sheet-ink);}
.rsheet .comp .states{font-family:var(--font-mono); font-size:11px;
  color:var(--sheet-mut); margin:6px 0 0;}
.rsheet .transitions{margin-top:24px;}
.rsheet .trans-row{display:flex; align-items:baseline; gap:12px; flex-wrap:wrap;
  padding:10px 0; border-top:1px solid var(--sheet-line);}
.rsheet .trans-row:first-of-type{border-top:none;}
.rsheet .trans-row .trig{font-size:.9375rem; color:var(--sheet-ink);}
.rsheet .trans-row .flow{font-family:var(--font-mono); font-size:12px;
  color:var(--sheet-mut);}

/* quiet states */
.rsheet .quiet{max-width:1140px; margin:0 auto; padding:64px 56px 96px;}
.rsheet .recordnote{max-width:640px; padding:18px 20px;
  border:.75px solid var(--sheet-line); border-radius:var(--r-panel);
  background:var(--sheet-sunk); color:var(--sheet-ink); font-size:13.5px;
  line-height:1.55;}
.rsheet .recordnote.alert{border-color:var(--sheet-spread); border-width:1px;}
.rsheet .recordnote strong{color:var(--sheet-ink); font-weight:600;}
.rsheet .recordnote .back{margin:14px 0 0;}
.rsheet .loadnote{margin:0; font-size:13px; color:var(--sheet-mut);}

/* footer */
.rsheet .recfoot{margin:72px 0 0; padding-top:22px;
  border-top:1px solid var(--sheet-line); display:flex;
  justify-content:space-between; flex-wrap:wrap; gap:18px; align-items:center;}
.rsheet .recfoot .l{font-family:var(--font-mono); font-size:11px;
  color:var(--sheet-mut); letter-spacing:.04em;}
.rsheet .recfoot .gl-foot{color:var(--sheet-spread);}
.rsheet .recfoot a{font-family:var(--font-mono); font-size:11px;
  color:var(--sheet-ink); border-bottom:1px dotted var(--sheet-mut);
  padding-bottom:1px;}
.rsheet .recfoot a:hover{border-bottom-style:solid;}

.rsheet .sheet-link{color:var(--sheet-ink); border-bottom:1px dotted var(--sheet-mut);
  transition:border-color 80ms ease-out;}
.rsheet .sheet-link:hover{border-bottom-color:var(--sheet-ink);}

.rsheet a:focus-visible{outline:2px solid var(--sheet-signal); outline-offset:2px;
  border-radius:var(--r-well);}

@media (max-width:1000px){
  .rsheet .shell{grid-template-columns:1fr;}
  .rsheet .spine{border-right:none; border-bottom:1px solid var(--sheet-line);
    padding:24px 0;}
  .rsheet .spine-sticky{position:static;}
  .rsheet .reading{padding:0 24px;}
  .rsheet .rec-head{padding:36px 0 0;}
  .rsheet .quiet{padding:36px 24px 96px;}
  .rsheet .meta-grid{grid-template-columns:1fr;}
}
`;

export default function CapabilityDetailV2({ params }: { params: { name: string } }) {
  const name = decodeURIComponent(params.name);
  const [rec, setRec] = useState<Fetchable<CapabilityRecord>>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getCapability(name);
        if (!cancelled) setRec({ state: "ready", data });
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) setRec({ state: "missing" });
        else setRec({ state: "error", message: e instanceof Error ? e.message : "Unknown error" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [name]);

  // ── pre-content states (loading / missing / error) — light Sheet quiet states.
  if (rec.state !== "ready") {
    return (
      <AppShellV2 activeNav="personas" title="Capability" surface="sheet">
      <div className="rsheet">
        <style>{RSHEET_CSS}</style>
        <div className="quiet">
          {rec.state === "loading" && (
            <p className="loadnote">Loading the capability record…</p>
          )}
          {rec.state === "missing" && (
            <RecordNote>
              No record for <strong>{name}</strong> in the latest feature pack. The capability
              may have been renamed or dropped in a more recent crawl, or the pack hasn&apos;t
              been generated yet.
            </RecordNote>
          )}
          {rec.state === "error" && (
            <RecordNote alert>
              The capability record could not be loaded: {rec.message}
            </RecordNote>
          )}
        </div>
      </div>
      </AppShellV2>
    );
  }

  const data = rec.data;

  return (
    <AppShellV2 activeNav="personas" title="Capability" surface="sheet">
    <div className="rsheet">
      <style>{RSHEET_CSS}</style>

      <div className="shell">
        {/* ── Provenance Spine — only the fields the capability read carries ──── */}
        <aside className="spine">
          <div className="spine-sticky">
            <p className="spine-title">Provenance</p>
            <div className="spine-row">
              <span className="spine-k">Snapshot</span>
              <span className="spine-v mono">{data.snapshot_version}</span>
            </div>
            <div className="spine-row">
              <span className="spine-k">Captured</span>
              <span className="spine-v mono">{formatCapture(data.generated_at)}</span>
            </div>
            <div className="spine-row">
              <span className="spine-k">Calibration</span>
              <span className="spine-v calib">
                <span className="glyph-hollow">◇</span> UNCALIBRATED
              </span>
            </div>
            <p className="spine-note">
              Provenance comes from the same read that served this record. The
              header can never label a capability with another snapshot&apos;s date.
            </p>
          </div>
        </aside>

        {/* ── Reading column ──────────────────────────────────────────────────── */}
        <main className="reading">
          <header className="rec-head">
            <div className="rec-kicker">Capability · As-built product</div>
            <h1 className="rec-h1">{name}</h1>
          </header>

          <CapabilityMeta cap={data.capability} />
          <ReversePrdSheet
            name={name}
            prd={data.capability.reverse_prd}
            prov={{ snapshot: data.snapshot_version, generated: data.generated_at }}
          />
          <ReverseFigmaSheet figma={data.capability.reverse_figma} />

          <footer className="recfoot">
            <span className="l">
              RECORD · {name.toUpperCase()} · {data.snapshot_version} ·{" "}
              <span className="gl-foot">◇</span> UNCALIBRATED
            </span>
            <Link href="/personas" className="sheet-link">
              ← Back to the Library
            </Link>
          </footer>
        </main>
      </div>
    </div>
    </AppShellV2>
  );
}

// ── capability meta (surfaces · roles · implicit metric) ──────────────────

function CapabilityMeta({ cap }: { cap: Capability }) {
  return (
    <section className="meta">
      <div className="sec-eyebrow">Capability map</div>
      <div className="meta-grid">
        <DesignatorRow label="Roles" items={cap.roles} role />
        <DesignatorRow label="Surfaces" items={cap.surfaces} />
        {cap.entry_points.length > 0 && (
          <DesignatorRow label="Entry points" items={cap.entry_points} />
        )}
        {cap.implicit_metric && (
          <div className="full">
            <span className="lbl">Implicit metric</span>
            <p className="metric-line">{cap.implicit_metric}</p>
          </div>
        )}
      </div>
    </section>
  );
}

function DesignatorRow({
  label,
  items,
  role = false,
}: {
  label: string;
  items: string[];
  role?: boolean;
}) {
  return (
    <div>
      <span className="lbl">{label}</span>
      <div className="chips">
        {items.length === 0 ? (
          <span className="meta-empty">—</span>
        ) : (
          items.map((it) => (
            <span key={it} className={role ? "chip role" : "chip"}>
              {it}
            </span>
          ))
        )}
      </div>
    </div>
  );
}

// ── reverse PRD — the record voice (§7.6) ─────────────────────────────────

function ReversePrdSheet({
  name,
  prd,
  prov,
}: {
  name: string;
  prd: string;
  prov: { snapshot: string; generated: string };
}) {
  return (
    <section className="prd">
      <div className="prd-prov">
        REVERSE PRD · {name} · SNAPSHOT {prov.snapshot} · {formatCapture(prov.generated)}
      </div>
      <div className="prd-body">
        <Markdown source={prd} />
      </div>
    </section>
  );
}

// ── reverse Figma — companion spec record ─────────────────────────────────

function ReverseFigmaSheet({ figma }: { figma: ReverseFigma }) {
  const screens = figma.screens ?? [];
  const transitions = figma.transitions ?? [];

  return (
    <section className="figma">
      <div className="figma-prov">
        REVERSE FIGMA · {screens.length} SCREEN{screens.length === 1 ? "" : "S"} ·{" "}
        {transitions.length} TRANSITION{transitions.length === 1 ? "" : "S"}
      </div>

      <div>
        {screens.map((screen) => (
          <div key={screen.id} className="screen">
            <div className="screen-head">
              <span className="nm">{screen.name}</span>
              <span className="desig">{screen.id}</span>
              {screen.role && <span className="desig">{screen.role}</span>}
            </div>
            <div className="comp-list">
              {(screen.components ?? []).map((c) => (
                <div key={c.id} className="comp">
                  <div className="row">
                    <span className="desig">{c.id}</span>
                    {c.role && <span className="crole">{c.role}</span>}
                    {(c.visible_to_roles ?? []).map((r) => (
                      <span key={r} className="desig">
                        {r}
                      </span>
                    ))}
                  </div>
                  {c.text && <p className="ctext">{c.text}</p>}
                  {(c.states ?? []).length > 0 && (
                    <p className="states">
                      States: {(c.states ?? []).map((s) => s.name).join(" · ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {transitions.length > 0 && (
          <div className="transitions">
            <span className="lbl">Transitions</span>
            <div>
              {transitions.map((t, i) => (
                <div key={`${t.from_screen}-${t.to_screen}-${i}`} className="trans-row">
                  <span className="trig">{t.trigger}</span>
                  <span className="flow">
                    {t.from_screen} → {t.to_screen}
                  </span>
                  {(t.role_gated ?? []).map((r) => (
                    <span key={r} className="desig">
                      {r}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

// ── notes ─────────────────────────────────────────────────────────────────

function RecordNote({ children, alert = false }: { children: React.ReactNode; alert?: boolean }) {
  return (
    <div role={alert ? "alert" : undefined} className={alert ? "recordnote alert" : "recordnote"}>
      {children}
      <p className="back">
        <Link href="/personas" className="sheet-link">
          ← Back to the Library
        </Link>
      </p>
    </div>
  );
}

// ── minimal markdown renderer (§7.6 subset) ───────────────────────────────
//
// Dependency-free; renders the reverse-PRD subset the crawler emits: ATX
// headings, ordered / unordered lists (one nesting level), paragraphs, and
// inline **bold** · *italic* / _italic_ · `code`. Per §7.6 the body is
// sans-only — inline code is marked with a recessed background, never a mono
// font (mono stops at the provenance header).
//
// LOGIC PRESERVED byte-for-byte from the legacy; only the rendered class names /
// inline styles below change to the Sheet palette (serif body, --sheet tokens).

const HEADING_SIZES: Record<number, number> = { 1: 32, 2: 24, 3: 20, 4: 18, 5: 16, 6: 16 };

function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  let paragraph: string[] = [];
  let key = 0;

  const flushParagraph = () => {
    if (paragraph.length === 0) return;
    const text = paragraph.join(" ");
    blocks.push(
      <p
        key={`p-${key++}`}
        style={{
          margin: "0 0 16px",
          fontFamily: "var(--font-serif)",
          fontSize: "1.0625rem",
          lineHeight: 1.65,
          color: "var(--sheet-ink)",
        }}
      >
        <Inline text={text} />
      </p>,
    );
    paragraph = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim() === "") {
      flushParagraph();
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph();
      const level = heading[1].length;
      const size = HEADING_SIZES[level];
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      blocks.push(
        <Tag
          key={`h-${key++}`}
          style={{
            margin: level <= 2 ? "32px 0 14px" : "20px 0 10px",
            fontFamily: "var(--font-sans)",
            fontSize: size,
            fontWeight: 600,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            color: "var(--sheet-ink)",
          }}
        >
          <Inline text={heading[2]} />
        </Tag>,
      );
      continue;
    }

    // List blocks — collect consecutive list lines, then render with nesting.
    if (isListLine(line)) {
      flushParagraph();
      const group: string[] = [];
      while (i < lines.length && (isListLine(lines[i]) || isIndentedContinuation(lines[i], group))) {
        group.push(lines[i]);
        i++;
      }
      i--; // step back; loop will advance
      blocks.push(<List key={`l-${key++}`} lines={group} />);
      continue;
    }

    paragraph.push(line.trim());
  }
  flushParagraph();

  return <>{blocks}</>;
}

const ORDERED_RE = /^(\s*)\d+\.\s+(.*)$/;
const UNORDERED_RE = /^(\s*)[-*]\s+(.*)$/;

function isListLine(line: string): boolean {
  return ORDERED_RE.test(line) || UNORDERED_RE.test(line);
}

function isIndentedContinuation(line: string, group: string[]): boolean {
  // A non-list, indented line directly under a list item is wrap text — keep it
  // attached so it isn't torn into its own paragraph.
  return group.length > 0 && /^\s+\S/.test(line) && !isListLine(line);
}

interface ListItem {
  text: string;
  ordered: boolean;
  children: ListItem[];
}

function List({ lines }: { lines: string[] }) {
  const items = parseList(lines);
  return <ListNodes items={items} />;
}

function parseList(lines: string[]): ListItem[] {
  const root: ListItem[] = [];
  // Stack of (indent, item-list) frames; the deepest matching indent owns the line.
  const stack: { indent: number; items: ListItem[] }[] = [{ indent: -1, items: root }];

  for (const raw of lines) {
    const ordered = ORDERED_RE.exec(raw);
    const unordered = UNORDERED_RE.exec(raw);
    const m = ordered ?? unordered;
    if (!m) {
      // Continuation line — append to the last item's text.
      const top = stack[stack.length - 1].items;
      const last = top[top.length - 1];
      if (last) last.text += ` ${raw.trim()}`;
      continue;
    }
    const indent = m[1].replace(/\t/g, "  ").length;
    const item: ListItem = { text: m[2].trim(), ordered: Boolean(ordered), children: [] };

    // Pop frames that are at or deeper than this line's indent; the remaining
    // top frame is this item's parent list.
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) {
      stack.pop();
    }
    const parentFrame = stack[stack.length - 1];
    parentFrame.items.push(item);
    stack.push({ indent, items: item.children });
  }
  return root;
}

function ListNodes({ items }: { items: ListItem[] }) {
  if (items.length === 0) return null;
  const ordered = items[0].ordered;
  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag
      style={{
        margin: "0 0 16px",
        paddingLeft: 24,
        fontFamily: "var(--font-serif)",
        fontSize: "1.0625rem",
        lineHeight: 1.65,
        color: "var(--sheet-ink)",
      }}
    >
      {items.map((it, idx) => (
        <li key={idx} style={{ marginBottom: 8 }}>
          <Inline text={it.text} />
          {it.children.length > 0 && <ListNodes items={it.children} />}
        </li>
      ))}
    </Tag>
  );
}

// Inline spans: **bold**, *italic* / _italic_, `code`. Order matters — match
// bold before single-asterisk italic.
const INLINE_RE = /(\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*|_([^_]+)_)/g;

function Inline({ text }: { text: string }) {
  const out: React.ReactNode[] = [];
  let last = 0;
  let i = 0;
  let m: RegExpExecArray | null;
  INLINE_RE.lastIndex = 0;
  while ((m = INLINE_RE.exec(text)) !== null) {
    if (m.index > last) out.push(<Fragment key={`t-${i}`}>{text.slice(last, m.index)}</Fragment>);
    if (m[2] !== undefined) {
      out.push(
        <strong key={`b-${i}`} style={{ fontWeight: 500 }}>
          {m[2]}
        </strong>,
      );
    } else if (m[3] !== undefined) {
      // §7.6 — code stays sans; a recessed background marks the token.
      out.push(
        <span key={`c-${i}`} className="code-inline">
          {m[3]}
        </span>,
      );
    } else if (m[4] !== undefined) {
      out.push(<em key={`i-${i}`}>{m[4]}</em>);
    } else if (m[5] !== undefined) {
      out.push(<em key={`u-${i}`}>{m[5]}</em>);
    }
    last = m.index + m[0].length;
    i++;
  }
  if (last < text.length) out.push(<Fragment key={`t-${i}`}>{text.slice(last)}</Fragment>);
  return <>{out}</>;
}

function formatCapture(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

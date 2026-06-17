"use client";

// Capability detail — the reverse PRD + reverse-Figma record for one capability
// of the as-built product (Library browsability, #207). Reads
// GET /capabilities/{name}, which returns a CapabilityRecord: the capability
// plus the provenance (snapshot version · capture timestamp) of the pack it was
// read from. Provenance comes from the SAME read that served the body, so the
// record header can never label a capability with a different snapshot's date.
//
// This is a RECORD, not a reading — DESIGN.md §7.6 "record voice": the reverse
// PRD renders as a paper document (paper-elevated sheet, mono provenance header,
// then sans-only body at 16px / line-height 1.6 in a ≤68ch measure). No glass,
// no semantic color, no motion. Mono stops at the provenance header; the
// document body is sans only. The reverse-Figma spec renders as a companion
// record below — structured data where mono designators (screen / component ids)
// are appropriate (§7.7 designators).

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
import {
  ApiError,
  getCapability,
  type Capability,
  type CapabilityRecord,
  type ReverseFigma,
} from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO } from "@/lib/design";

// §7.6 long-form measure — the one sanctioned line-height exception (1.6).
const MEASURE = "68ch";
const BODY_LH = 1.6;

type Fetchable<T> =
  | { state: "loading" }
  | { state: "ready"; data: T }
  | { state: "missing" }
  | { state: "error"; message: string };

export default function CapabilityDetailLegacy({ params }: { params: { name: string } }) {
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

  return (
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
      <style
        dangerouslySetInnerHTML={{
          __html: `
            .cap-link { color: ${TOKENS.ink}; text-decoration: none; border-bottom: 1px dotted ${TOKENS.inkMuted}; transition: border-color 80ms ease-out; }
            .cap-link:hover { border-bottom-color: ${TOKENS.ink}; }
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
        <Link href="/personas" className="cap-link" style={{ fontSize: 12.5, fontWeight: 500 }}>
          ← Library
        </Link>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>
          {name}
        </h1>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: TOKENS.inkMuted,
            letterSpacing: "0.06em",
          }}
        >
          CAPABILITY · AS-BUILT PRODUCT
        </span>
      </header>

      <div style={{ padding: 24 }}>
        {rec.state === "loading" && (
          <p style={{ margin: 0, fontSize: 13, color: TOKENS.inkMuted }}>
            Loading the capability record…
          </p>
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

        {rec.state === "ready" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <CapabilityMeta cap={rec.data.capability} />
            <ReversePrdSheet
              name={name}
              prd={rec.data.capability.reverse_prd}
              prov={{ snapshot: rec.data.snapshot_version, generated: rec.data.generated_at }}
            />
            <ReverseFigmaSheet figma={rec.data.capability.reverse_figma} />
          </div>
        )}
      </div>
    </main>
  );
}

// ── capability meta (surfaces · roles · implicit metric) ──────────────────

function CapabilityMeta({ cap }: { cap: Capability }) {
  return (
    <section
      style={{
        background: TOKENS.paperElevated,
        border: `1px solid ${TOKENS.rule}`,
        borderRadius: 4,
        boxShadow: `inset 0 1px 0 ${TOKENS.paperElevated}`,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <DesignatorRow label="Roles" items={cap.roles} />
      <DesignatorRow label="Surfaces" items={cap.surfaces} />
      {cap.entry_points.length > 0 && (
        <DesignatorRow label="Entry points" items={cap.entry_points} />
      )}
      {cap.implicit_metric && (
        <div>
          <Label>Implicit metric</Label>
          <p style={{ margin: "4px 0 0", fontSize: 13, lineHeight: 1.5 }}>{cap.implicit_metric}</p>
        </div>
      )}
    </section>
  );
}

function DesignatorRow({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <Label>{label}</Label>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
        {items.length === 0 ? (
          <span style={{ fontSize: 12, color: TOKENS.inkMuted }}>—</span>
        ) : (
          items.map((it) => <Designator key={it}>{it}</Designator>)
        )}
      </div>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        display: "block",
        fontSize: 10,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: TOKENS.inkMuted,
      }}
    >
      {children}
    </span>
  );
}

function Designator({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10.5,
        letterSpacing: "0.04em",
        border: `1px solid ${TOKENS.rule}`,
        color: TOKENS.inkMuted,
        borderRadius: 2,
        padding: "2px 7px",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
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
    <section
      style={{
        background: TOKENS.paperElevated,
        border: `1px solid ${TOKENS.rule}`,
        borderRadius: 4,
        boxShadow: `inset 0 1px 0 ${TOKENS.paperElevated}`,
        padding: "20px 24px 24px",
      }}
    >
      {/* Provenance header — the one place mono appears (§7.6). */}
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 10.5,
          letterSpacing: "0.06em",
          color: TOKENS.inkMuted,
          textTransform: "uppercase",
          paddingBottom: 14,
          marginBottom: 18,
          borderBottom: `1px solid ${TOKENS.rule}`,
        }}
      >
        REVERSE PRD · {name} · SNAPSHOT {prov.snapshot} · {formatCapture(prov.generated)}
      </div>
      {/* Sans-only document body, 16px / 1.6, ≤68ch measure (§7.6). */}
      <div style={{ maxWidth: MEASURE }}>
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
    <section
      style={{
        background: TOKENS.paperElevated,
        border: `1px solid ${TOKENS.rule}`,
        borderRadius: 4,
        boxShadow: `inset 0 1px 0 ${TOKENS.paperElevated}`,
        padding: "20px 24px 24px",
      }}
    >
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 10.5,
          letterSpacing: "0.06em",
          color: TOKENS.inkMuted,
          textTransform: "uppercase",
          paddingBottom: 14,
          marginBottom: 18,
          borderBottom: `1px solid ${TOKENS.rule}`,
        }}
      >
        REVERSE FIGMA · {screens.length} SCREEN{screens.length === 1 ? "" : "S"} ·{" "}
        {transitions.length} TRANSITION{transitions.length === 1 ? "" : "S"}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {screens.map((screen) => (
          <div key={screen.id}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
              <span style={{ fontSize: 15, fontWeight: 600 }}>{screen.name}</span>
              <Designator>{screen.id}</Designator>
              {screen.role && <Designator>{screen.role}</Designator>}
            </div>
            <div
              style={{
                marginTop: 8,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                paddingLeft: 12,
                borderLeft: `1px solid ${TOKENS.rule}`,
              }}
            >
              {(screen.components ?? []).map((c) => (
                <div key={c.id}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
                    <Designator>{c.id}</Designator>
                    {c.role && (
                      <span style={{ fontSize: 11, color: TOKENS.inkMuted }}>{c.role}</span>
                    )}
                    {(c.visible_to_roles ?? []).map((r) => (
                      <Designator key={r}>{r}</Designator>
                    ))}
                  </div>
                  {c.text && (
                    <p style={{ margin: "3px 0 0", fontSize: 13, lineHeight: 1.5 }}>{c.text}</p>
                  )}
                  {(c.states ?? []).length > 0 && (
                    <p style={{ margin: "3px 0 0", fontSize: 12, color: TOKENS.inkMuted }}>
                      States: {(c.states ?? []).map((s) => s.name).join(" · ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {transitions.length > 0 && (
          <div>
            <Label>Transitions</Label>
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
              {transitions.map((t, i) => (
                <div
                  key={`${t.from_screen}-${t.to_screen}-${i}`}
                  style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}
                >
                  <span style={{ fontSize: 13 }}>{t.trigger}</span>
                  <span style={{ fontFamily: FONT_MONO, fontSize: 11, color: TOKENS.inkMuted }}>
                    {t.from_screen} → {t.to_screen}
                  </span>
                  {(t.role_gated ?? []).map((r) => (
                    <Designator key={r}>{r}</Designator>
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
    <div
      role={alert ? "alert" : undefined}
      style={{
        maxWidth: 640,
        padding: 16,
        border: `${alert ? "0.75px" : "1px"} solid ${alert ? TOKENS.alert : TOKENS.rule}`,
        borderRadius: alert ? 2 : 4,
        background: TOKENS.paperRecessed,
        color: TOKENS.ink,
        fontSize: 13,
        lineHeight: 1.5,
      }}
    >
      {children}
      <p style={{ margin: "12px 0 0" }}>
        <Link href="/personas" className="cap-link" style={{ fontWeight: 500 }}>
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
        style={{ margin: "0 0 14px", fontSize: 16, lineHeight: BODY_LH }}
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
            margin: level <= 2 ? "20px 0 10px" : "16px 0 8px",
            fontSize: size,
            fontWeight: 600,
            lineHeight: 1.25,
            letterSpacing: "-0.01em",
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
        margin: "0 0 14px",
        paddingLeft: 24,
        fontSize: 16,
        lineHeight: BODY_LH,
      }}
    >
      {items.map((it, idx) => (
        <li key={idx} style={{ marginBottom: 4 }}>
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
      out.push(<strong key={`b-${i}`}>{m[2]}</strong>);
    } else if (m[3] !== undefined) {
      // §7.6 — code stays sans; a recessed background marks the token.
      out.push(
        <span
          key={`c-${i}`}
          style={{
            background: TOKENS.paperRecessed,
            borderRadius: 2,
            padding: "0.5px 4px",
          }}
        >
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

"use client";

// Persona-pack detail — the full record for one persona pack of the modelled
// population (Library browsability, #207 / #25). Reads GET /persona-packs/{id}/detail,
// the RENDERED view: every persona's description / JTBD / behavioral snapshot,
// plus the server-rendered behavioral-comparison blocks (the centroid "how this
// segment compares" profile and, on a v1.1 pack, the per-member individual-row
// profile), every weight scheme with an honest reason when one is unavailable,
// and the pack's stability. `id` is usually the "latest" sentinel — the active
// pack — but an explicit version addresses an older snapshot directly.
//
// The comparison blocks are rendered SERVER-SIDE (behavioral_profile.py) so the
// salience/grounding/honesty rules that govern what an agent reads also govern
// what's shown here — this page just lays the rendered deltas out, it does not
// re-derive them.
//
// These are RECORDS, not readings — DESIGN.md §7.6 "record voice": each persona
// renders as a paper sheet (paper-elevated, mono provenance/designator header,
// then sans-only prose at 16px / line-height 1.6 in a ≤68ch measure). No glass,
// no semantic color, no motion. Mono is reserved for designators (persona id,
// weight, snapshot keys); the descriptive prose is sans only.
//
// A starter pack (#212) is honestly labelled: the generic placeholder a tenant
// gets before it has built or seeded a real pack — clickable, but never from
// the customer's own data.

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiError,
  getPersonaPackDetail,
  type PersonaPackDetail,
  type PersonaProfileView,
  type ProfileBlockView,
  type WeightSchemeView,
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

export default function PersonaPackDetailPage({ params }: { params: { id: string } }) {
  const id = decodeURIComponent(params.id);
  const [pack, setPack] = useState<Fetchable<PersonaPackDetail>>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getPersonaPackDetail(id);
        if (!cancelled) setPack({ state: "ready", data });
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) setPack({ state: "missing" });
        else setPack({ state: "error", message: e instanceof Error ? e.message : "Unknown error" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // The header label tracks the resolved pack once we have it, falling back to
  // the requested id while loading.
  const headerVersion =
    pack.state === "ready" ? pack.data.version : id === "latest" ? "LATEST" : id.toUpperCase();

  return (
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
      <style
        dangerouslySetInnerHTML={{
          __html: `
            .pack-link { color: ${TOKENS.ink}; text-decoration: none; border-bottom: 1px dotted ${TOKENS.inkMuted}; transition: border-color 80ms ease-out; }
            .pack-link:hover { border-bottom-color: ${TOKENS.ink}; }
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
        <Link href="/personas" className="pack-link" style={{ fontSize: 12.5, fontWeight: 500 }}>
          ← Library
        </Link>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>
          Persona pack
        </h1>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: TOKENS.inkMuted,
            letterSpacing: "0.06em",
          }}
        >
          {headerVersion.toUpperCase()} · MODELLED POPULATION
        </span>
      </header>

      <div style={{ padding: 24 }}>
        {pack.state === "loading" && (
          <p style={{ margin: 0, fontSize: 13, color: TOKENS.inkMuted }}>
            Loading the persona pack…
          </p>
        )}

        {pack.state === "missing" && (
          <RecordNote>
            No persona pack <strong>{id}</strong> for this workspace. The version may have been
            retired or never generated.
          </RecordNote>
        )}

        {pack.state === "error" && (
          <RecordNote alert>The persona pack could not be loaded: {pack.message}</RecordNote>
        )}

        {pack.state === "ready" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <PackMeta pack={pack.data} />
            {pack.data.personas.map((persona) => (
              <PersonaSheet
                key={persona.id}
                persona={persona}
                schemes={pack.data.weight_schemes}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

// ── pack meta (version · capture · stability · weight schemes · honesty) ───

function PackMeta({ pack }: { pack: PersonaPackDetail }) {
  const unavailable = pack.weight_schemes.filter((s) => !s.available);
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
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 10.5,
          letterSpacing: "0.06em",
          color: TOKENS.inkMuted,
          textTransform: "uppercase",
        }}
      >
        {pack.is_starter ? "STARTER PACK" : "ACTIVE PACK"} · {pack.persona_count} PERSONA
        {pack.persona_count === 1 ? "" : "S"} · SNAPSHOT {pack.version.toUpperCase()} ·{" "}
        {formatCapture(pack.generated_at)} · STABILITY {pack.stability_score.toFixed(2)} · SCHEMA{" "}
        {pack.schema_version}
      </div>

      {/* Weight bases the pack carries — headcount is always present; the
          revenue/order weightings appear only when the source data covered
          every persona (§7.6: state the absence honestly, don't hide it). */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {pack.weight_schemes
          .filter((s) => s.available)
          .map((s) => (
            <Designator key={s.key}>{s.label.toUpperCase()}</Designator>
          ))}
      </div>
      {unavailable.map((s) => (
        <p
          key={s.key}
          style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: TOKENS.inkMuted, maxWidth: MEASURE }}
        >
          <strong>{s.label}</strong> — {s.note}
        </p>
      ))}

      {pack.is_starter && (
        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: TOKENS.inkMuted, maxWidth: MEASURE }}>
          These are generic placeholder personas so you can click through Sidira right away —
          they are <strong>not</strong> built from your data. Build a real pack, or seed the
          sample workspace, before trusting any reading.
        </p>
      )}
    </section>
  );
}

// ── one persona — the record voice (§7.6) ─────────────────────────────────

function PersonaSheet({
  persona,
  schemes,
}: {
  persona: PersonaProfileView;
  schemes: WeightSchemeView[];
}) {
  const snapshot = Object.entries(persona.behavioral_snapshot ?? {});
  // Per-scheme share designators, in the pack's scheme order, label from the
  // pack-level scheme list so the wording stays single-sourced.
  const shareChips = schemes
    .filter((s) => typeof persona.shares[s.key] === "number")
    .map((s) => ({ key: s.key, label: s.label, pct: persona.shares[s.key] }));

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
      {/* Designator header — the one place mono appears (§7.6). */}
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          flexWrap: "wrap",
          paddingBottom: 14,
          marginBottom: 18,
          borderBottom: `1px solid ${TOKENS.rule}`,
        }}
      >
        <span style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.01em" }}>
          {persona.name}
        </span>
        <Designator>{persona.id}</Designator>
        {shareChips.map((c) => (
          <Designator key={c.key}>
            {(c.pct * 100).toFixed(0)}% {c.label.toUpperCase()}
          </Designator>
        ))}
      </div>

      {/* Sans-only document body, 16px / 1.6, ≤68ch measure (§7.6). */}
      <div style={{ maxWidth: MEASURE, display: "flex", flexDirection: "column", gap: 16 }}>
        <p style={{ margin: 0, fontSize: 16, lineHeight: BODY_LH }}>{persona.description}</p>

        {persona.jtbd && (
          <div>
            <Label>Jobs to be done</Label>
            <p style={{ margin: "6px 0 0", fontSize: 16, lineHeight: BODY_LH }}>{persona.jtbd}</p>
          </div>
        )}

        {snapshot.length > 0 && (
          <div>
            <Label>Behavioral snapshot</Label>
            <dl
              style={{
                margin: "8px 0 0",
                display: "grid",
                gridTemplateColumns: "auto 1fr",
                gap: "4px 16px",
              }}
            >
              {snapshot.map(([k, v]) => (
                <div key={k} style={{ display: "contents" }}>
                  <dt style={{ fontSize: 13, color: TOKENS.inkMuted }}>{humanizeKey(k)}</dt>
                  <dd
                    style={{
                      margin: 0,
                      fontFamily: FONT_MONO,
                      fontSize: 12.5,
                      letterSpacing: "0.02em",
                    }}
                  >
                    {formatSnapshotValue(v)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {/* Behavioral-comparison blocks — only when the renderer found salient
            divergence (§2 no-silent-degradation: absence is shown, not faked). */}
        {persona.how_you_compare && <ComparisonBlock block={persona.how_you_compare} />}
        {persona.distinctive && <ComparisonBlock block={persona.distinctive} />}
      </div>
    </section>
  );
}

// ── one rendered behavioral-comparison block ──────────────────────────────

function ComparisonBlock({ block }: { block: ProfileBlockView }) {
  return (
    <div>
      <Label>{block.heading}</Label>
      <p style={{ margin: "8px 0 0", fontSize: 16, lineHeight: BODY_LH }}>{block.intro}</p>
      <ul
        style={{
          margin: "8px 0 0",
          paddingLeft: 20,
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
      >
        {block.deltas.map((d, i) => (
          <li key={i} style={{ fontSize: 16, lineHeight: 1.5 }}>
            <strong>
              {d.magnitude} {d.direction}
            </strong>{" "}
            {d.label}
          </li>
        ))}
      </ul>
      {block.tail_count > 0 && (
        <p style={{ margin: "8px 0 0", fontSize: 13, color: TOKENS.inkMuted }}>
          …plus {block.tail_count} further, smaller difference{block.tail_count === 1 ? "" : "s"} —
          these are just the most pronounced.
        </p>
      )}
      {block.suppressed_count > 0 && (
        <p style={{ margin: "6px 0 0", fontSize: 13, color: TOKENS.inkMuted }}>
          {block.suppressed_count} further trait{block.suppressed_count === 1 ? "" : "s"} sit within
          the typical range.
        </p>
      )}
      <p style={{ margin: "10px 0 0", fontSize: 13, lineHeight: 1.5, color: TOKENS.inkMuted }}>
        {block.note}
      </p>
    </div>
  );
}

// ── shared bits (mirrors the capability detail record) ────────────────────

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
        <Link href="/personas" className="pack-link" style={{ fontWeight: 500 }}>
          ← Back to the Library
        </Link>
      </p>
    </div>
  );
}

// snapshot keys arrive as snake_case machine names; present them in sentence
// case for the human-facing label column (§5.4) while values stay mono data.
function humanizeKey(key: string): string {
  const spaced = key.replace(/_/g, " ").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

function formatSnapshotValue(v: number | string): string {
  if (typeof v === "number") {
    // Keep integers whole; round noisy floats to 2dp.
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  return v;
}

function formatCapture(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 10);
}

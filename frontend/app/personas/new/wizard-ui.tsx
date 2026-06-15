"use client";

// Persona Builder wizard — shared UI vocabulary (#26/#27/#28).
//
// These style objects and the small row furniture are lifted verbatim from
// the feature-pack crawl-setup page (frontend/app/personas/crawl-setup/
// page.tsx), our canonical instrument-posture template (DESIGN.md §7). Every
// wizard step imports from here so the visual grammar — 0.75px hairlines,
// mono uppercase labels with tabular numerals, paper-recessed alert notes
// whose message reads in ink (§4.3/§7.7) — stays identical across files and
// in lockstep with crawl-setup. No new colors, no spinners: pending states
// are honest text (§8.6).

import { ApiError } from "@/lib/api";
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";

// ── error parsing ────────────────────────────────────────────────────────
//
// Backend errors arrive as JSON {"detail": ...} where `detail` is EITHER a
// plain string OR a structured object {error_kind, message} (the feature-store
// test/preview routes use the latter). Surface the human part, never the raw
// envelope. Returns a single line; callers that want error_kind separately can
// use apiErrorParts below.
export function apiErrorMessage(e: unknown): string {
  const parts = apiErrorParts(e);
  return parts.kind ? `${parts.kind} · ${parts.message}` : parts.message;
}

export function apiErrorParts(e: unknown): { kind: string | null; message: string } {
  if (e instanceof ApiError) {
    try {
      const detail = JSON.parse(e.body)?.detail;
      if (typeof detail === "string") return { kind: null, message: detail };
      if (detail && typeof detail === "object") {
        const kind = typeof detail.error_kind === "string" ? detail.error_kind.toUpperCase() : null;
        const message =
          typeof detail.message === "string" ? detail.message : e.body || `HTTP ${e.status}`;
        return { kind, message };
      }
    } catch {
      /* non-JSON body — fall through to the raw text */
    }
    return { kind: null, message: e.body || `HTTP ${e.status}` };
  }
  return { kind: null, message: e instanceof Error ? e.message : "request failed" };
}

// Crawl-setup UTC stamp style — used for every event/timestamp line (§5.3).
export const utcStamp = (iso: string) =>
  new Date(iso).toISOString().replace("T", " · ").slice(0, 18) + " UTC";

// ── row furniture (copied from crawl-setup) ──────────────────────────────

export function AddButton({
  onClick,
  children,
}: {
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        marginTop: 10,
        background: "transparent",
        border: `0.75px solid ${TOKENS.rule}`,
        borderRadius: 2,
        padding: "4px 10px",
        fontFamily: FONT_MONO,
        fontSize: 10.5,
        letterSpacing: "0.06em",
        color: TOKENS.inkMuted,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

export function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      style={{
        background: "transparent",
        border: `0.75px solid ${TOKENS.rule}`,
        borderRadius: 2,
        padding: "0 10px",
        fontFamily: FONT_MONO,
        fontSize: 12,
        color: TOKENS.inkMuted,
        cursor: "pointer",
        flexShrink: 0,
      }}
    >
      ×
    </button>
  );
}

// A bordered mono confidence/status chip — NOT a colored fill. Confidence is
// carried by the wording (HIGH / MED / LOW), never by color (§4.3: color never
// carries state alone). Mirrors the chip anatomy in DESIGN.md §8.2.
export function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 10,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: TOKENS.inkMuted,
        border: `0.75px solid ${TOKENS.rule}`,
        borderRadius: 2,
        padding: "1px 6px",
        whiteSpace: "nowrap",
        ...TNUM,
      }}
    >
      {children}
    </span>
  );
}

// ── shared styles — instrument posture (DESIGN.md §7.4) ───────────────────

export const inputStyle: React.CSSProperties = {
  width: "100%",
  fontFamily: FONT_SANS,
  fontSize: 14,
  color: TOKENS.ink,
  background: TOKENS.paperElevated,
  border: `0.75px solid ${TOKENS.rule}`,
  borderRadius: 2,
  padding: "8px 11px",
  boxSizing: "border-box",
};

export const selectStyle: React.CSSProperties = {
  ...inputStyle,
  fontFamily: FONT_MONO,
  fontSize: 13,
};

// Mono input variant — for FQNs, SQL, account identifiers (§5.3).
export const monoInputStyle: React.CSSProperties = {
  ...inputStyle,
  fontFamily: FONT_MONO,
  fontSize: 13,
};

export const textareaStyle: React.CSSProperties = {
  ...monoInputStyle,
  minHeight: 120,
  resize: "vertical",
  lineHeight: 1.5,
};

export const sectionStyle: React.CSSProperties = {
  marginTop: 28,
};

export const sectionLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: "0.16em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  paddingBottom: 8,
  borderBottom: `0.75px solid ${TOKENS.rule}`,
  ...TNUM,
};

export const sublabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  marginBottom: 6,
};

export const hintStyle: React.CSSProperties = {
  fontSize: 12,
  color: TOKENS.inkMuted,
  marginTop: 6,
  lineHeight: 1.45,
  maxWidth: "52ch",
};

export const fieldStyle: React.CSSProperties = {
  marginTop: 16,
};

export const fieldRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 16,
};

export const primaryBtnStyle: React.CSSProperties = {
  background: TOKENS.ink,
  color: TOKENS.paper,
  border: `0.75px solid ${TOKENS.ink}`,
  borderRadius: 2,
  padding: "7px 14px",
  fontWeight: 500,
  fontSize: 13,
  fontFamily: FONT_SANS,
  cursor: "pointer",
};

export const secondaryBtnStyle: React.CSSProperties = {
  background: "transparent",
  color: TOKENS.ink,
  border: `0.75px solid ${TOKENS.ink}`,
  borderRadius: 2,
  padding: "7px 14px",
  fontWeight: 500,
  fontSize: 13,
  fontFamily: FONT_SANS,
  cursor: "pointer",
};

export const railAlertStyle: React.CSSProperties = {
  padding: "8px 10px",
  background: TOKENS.paperRecessed,
  border: `0.75px solid ${TOKENS.alert}`,
  borderRadius: 2,
  // alert is accent-only (border) — the message reads in ink (§4.3/§7.7).
  color: TOKENS.ink,
  fontSize: 12,
  lineHeight: 1.45,
  overflowWrap: "break-word",
};

export const railCaptionStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  color: TOKENS.inkMuted,
  letterSpacing: "0.04em",
  lineHeight: 1.5,
  ...TNUM,
};

export const errorBannerStyle: React.CSSProperties = {
  marginBottom: 16,
  padding: "12px 16px",
  background: TOKENS.paperRecessed,
  border: `0.75px solid ${TOKENS.alert}`,
  borderRadius: 2,
  // alert is accent-only (border) — the message reads in ink (§4.3/§7.7).
  color: TOKENS.ink,
  fontSize: 14,
  maxWidth: 620,
  boxSizing: "border-box",
};

// A success/confirmation note — honest text (§8.6). Same paper-recessed
// anatomy as the alert note, but the border is the `success` token; the
// message still reads in ink so meaning never rides on color alone (§4.3).
export const okBannerStyle: React.CSSProperties = {
  padding: "10px 12px",
  background: TOKENS.paperRecessed,
  border: `0.75px solid ${TOKENS.success}`,
  borderRadius: 2,
  color: TOKENS.ink,
  fontSize: 13,
  lineHeight: 1.45,
  overflowWrap: "break-word",
};

// Honest-text status line, mono uppercase — the §8.6 "no spinners" primitive.
export const statusLineStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 12,
  letterSpacing: "0.06em",
  color: TOKENS.ink,
  ...TNUM,
};

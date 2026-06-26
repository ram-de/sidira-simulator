// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — canonical aperture marks for the v2 top bars.
//
// These are NOT new geometry. They reuse the canonical six-blade camera
// diaphragm (DESIGN.md §1.1) — the exact polygon point-set shipped in
// frontend/public/brand/sidira-mark.svg (mono) and sidira-mark-duo.svg (duo),
// the same set SidiraLockup.tsx / SidiraLockupDuo.tsx render. The duo blue/rose
// come from lib/design.ts (DUO_SID / DUO_AVIRA) — no new hardcoded hexes.
//
//  • SheetMarkDuo — the standard dual-color mark (DESIGN.md §1.3, ticket #35):
//    3 Sid-blue + 3 Avira-rose blades. It is the default mark EVERYWHERE now —
//    public marketing (SheetTopBar) AND in-product (the AppShellV2 console
//    rail). Its fixed DUO_SID/DUO_AVIRA strokes render on any ground.
//  • ConsoleMarkMono — legacy monochrome ink mark, currentColor stroke. No
//    longer the in-product default (§1.3 now rests dual-color everywhere);
//    kept as a fallback and still used by the ConsoleShell marketing TopBar,
//    AppFrame mock, and auth screens until those are migrated.
// ───────────────────────────────────────────────────────────────────────────
import { DUO_SID, DUO_AVIRA } from "@/lib/design";

// Canonical duo mark — geometry + colors lifted verbatim from
// frontend/public/brand/sidira-mark-duo.svg (viewBox 0 0 100 100).
export function SheetMarkDuo({ size = 30 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      fill="none"
      aria-hidden
      style={{ display: "block" }}
    >
      <g strokeWidth={3.5} strokeLinejoin="round" fill="none">
        <g stroke={DUO_SID}>
          <polygon points="50,90 15.359,70 38.740,56.5 50,63" />
          <polygon points="15.359,70 15.359,30 38.740,43.5 38.740,56.5" />
          <polygon points="15.359,30 50,10 50,37 38.740,43.5" />
        </g>
        <g stroke={DUO_AVIRA}>
          <polygon points="84.641,70 50,90 50,63 61.260,56.5" />
          <polygon points="50,10 84.641,30 61.260,43.5 50,37" />
          <polygon points="84.641,30 84.641,70 61.260,56.5 61.260,43.5" />
        </g>
      </g>
    </svg>
  );
}

// Canonical monochrome mark — geometry lifted verbatim from
// frontend/public/brand/sidira-mark.svg / SidiraLockup.tsx (viewBox 0 0 100 100).
// Stroke is currentColor so it inherits the in-product ink.
export function ConsoleMarkMono({ size = 28 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      fill="none"
      aria-hidden
      style={{ display: "block", color: "currentColor" }}
    >
      <g stroke="currentColor" strokeWidth={3.5} strokeLinejoin="round" fill="none">
        <polygon points="84.641,70 50,90 50,63 61.260,56.5" />
        <polygon points="50,90 15.359,70 38.740,56.5 50,63" />
        <polygon points="15.359,70 15.359,30 38.740,43.5 38.740,56.5" />
        <polygon points="15.359,30 50,10 50,37 38.740,43.5" />
        <polygon points="50,10 84.641,30 61.260,43.5 50,37" />
        <polygon points="84.641,30 84.641,70 61.260,56.5 61.260,43.5" />
      </g>
    </svg>
  );
}

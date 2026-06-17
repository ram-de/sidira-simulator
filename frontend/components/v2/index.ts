// DESIGN SYSTEM v2 — shared component barrel.
// Import v2 primitives/components from "@/components/v2"; the scoped tokens come
// from lib/design-v2.ts and the v2-theme.css stylesheet the page imports.
export {
  Designator,
  Chip,
  CalGlyph,
  StatusBadge,
  StatusDot,
  Button,
  Panel,
} from "./primitives";
export {
  ConsoleShell,
  SheetShell,
  Wrap,
  TopBar,
  type NavItem,
} from "./ConsoleShell";
export {
  SheetTopBar,
  RecordGrid,
  ProvenanceSpine,
  Prose,
  SheetSection,
  SheetKicker,
  type SheetNavItem,
  type SpineFact,
} from "./Sheet";
export {
  ProvenanceBar,
  ProvenanceMarker,
  type ProvSeg,
  type ProvenanceMarkerProps,
} from "./Provenance";
export { Section, SectionHead, ScrollReveal } from "./Section";
export { ConsoleWell } from "./ConsoleWell";
export {
  DistributionPoster,
  PosterFigure,
  type Bar,
  type DistributionPosterProps,
} from "./DistributionPoster";

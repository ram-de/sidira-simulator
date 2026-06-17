// ───────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM v2 — THE POPULATION FIELD (§5.5 / §7.1) — the ONE signature viz.
//
// A full-bleed canvas of N particles, each one synthetic *agent*. At rest the
// cohort drifts in a calm curl-noise flow-field — a breathing population warming
// up. On a "bet" (the canned hero loop), a `--signal` wavefront sweeps left→right
// and every particle re-sorts along a 1-D reaction axis (left rejects · right
// adopts) into a two-arm distribution silhouette; a `--spread` CI ribbon
// materializes; the field settles, holds, then dissolves back to drift. The
// emergent histogram IS the reading.
//
// Tier-2 (Canvas 2D) of the §5.5 recipe — robust, dependency-free, ≤700 points,
// capped ~30fps, additive low-α (graphite dust catching light, not fireworks).
//
// HONESTY (§5.5 / §5.6): this is a SHOWPIECE-only live reading, so the field IS
// its region's single signal carrier (§1.9). It is a *canned* baseline, never a
// faked verdict: it loops drift → wavefront → settle → ribbon → dissolve and
// never locks a ◆.
//
// ACCESSIBILITY / PERF (NON-NEGOTIABLE, §5.5 taste rules):
//   • prefers-reduced-motion → ONE static settled frame, no rAF loop at all.
//   • SSR-safe: the canvas renders empty markup on the server; all window/canvas
//     access is inside useEffect (after mount).
//   • devicePixelRatio-aware; frame-rate capped (~30fps); rAF paused on a hidden
//     tab (visibilitychange) AND when scrolled offscreen (IntersectionObserver);
//     all rAF + listeners cleaned up on unmount.
//
// COLOR: sourced at runtime from the v2 CSS custom properties on
// document.documentElement (--signal · --spread · --text-mut · --arm-* …) so the
// field stays token-linked. Each read has a small hardcoded fallback used ONLY
// if the property reads empty (e.g. SSR/first paint) — every literal below is
// flagged `runtime-fallback` and mirrors styles/v2-theme.css verbatim.
// ───────────────────────────────────────────────────────────────────────────
"use client";

import { useEffect, useRef, type CSSProperties } from "react";

export type PopulationFieldProps = {
  /** Particle count (one per synthetic agent). Capped to [120, 700] for perf. */
  particleCount?: number;
  /**
   * "live"   — the looping canned bet (drift → wavefront → settle → dissolve).
   * "settled"— a single still settled frame (the distribution at rest), no loop.
   * Reduced-motion forces "settled" regardless.
   */
  mode?: "live" | "settled";
  /** Drift amplitude / wavefront vigor multiplier (0..1). Calm by default. */
  intensity?: number;
  /** CSS height of the field. Width is always 100% of the parent. */
  height?: number | string;
  /** Deterministic seed so the canned field is stable across renders. */
  seed?: number;
  className?: string;
  style?: CSSProperties;
  /** Decorative by default; the page supplies the accessible description. */
  ariaLabel?: string;
};

// ── runtime token resolver ──────────────────────────────────────────────────
// Reads a v2 CSS custom property off :root; returns `fallback` ONLY if the
// property is empty (e.g. before the scoped stylesheet resolves). The fallbacks
// mirror styles/v2-theme.css and are the component's sole color literals.
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return fallback;
  }
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return v || fallback;
}

// Parse a "#rrggbb" / "#rgb" hex into [r,g,b]; tolerant of the runtime token.
function hexToRgb(
  hex: string,
  fallback: [number, number, number],
): [number, number, number] {
  const m = hex.trim().replace(/^#/, "");
  if (m.length === 3) {
    const r = parseInt(m[0] + m[0], 16);
    const g = parseInt(m[1] + m[1], 16);
    const b = parseInt(m[2] + m[2], 16);
    if ([r, g, b].every((n) => Number.isFinite(n))) return [r, g, b];
  }
  if (m.length === 6) {
    const r = parseInt(m.slice(0, 2), 16);
    const g = parseInt(m.slice(2, 4), 16);
    const b = parseInt(m.slice(4, 6), 16);
    if ([r, g, b].every((n) => Number.isFinite(n))) return [r, g, b];
  }
  return fallback;
}

// Small deterministic PRNG (mulberry32) — no Math.random, so the field is stable.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Smooth ease for the settle / dissolve transitions (matches --ease-settle feel).
function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

type Particle = {
  // rest position (drift home), in normalized [0,1] field space
  rx: number;
  ry: number;
  // settled position (the binned distribution target)
  sx: number;
  sy: number;
  // current drawn position
  x: number;
  y: number;
  // phase offsets for the curl-ish drift
  pa: number;
  pb: number;
  arm: 0 | 1; // 0 = control, 1 = treatment
  // reaction score [0,1] along the axis — drives the settled x bin
  reaction: number;
  size: number;
};

// ── the canned-bet timeline (seconds), per §5.3 (~8s hero loop) ─────────────
const T_DRIFT = 2.4; // calm drift before the wavefront
const T_SWEEP = 1.9; // wavefront crosses + particles begin re-sorting
const T_SETTLE = 1.6; // distribution locks into shape + CI ribbon rises
const T_HOLD = 1.6; // settled, held (the reading you can read)
const T_DISSOLVE = 1.5; // back to drift
const T_LOOP = T_DRIFT + T_SWEEP + T_SETTLE + T_HOLD + T_DISSOLVE; // ≈ 9s

export function PopulationField({
  particleCount = 560,
  mode = "live",
  intensity = 1,
  height = 560,
  seed = 0x51d1a0, // "sidira"-ish constant; any stable int works

  className,
  style,
  ariaLabel,
}: PopulationFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const reduceMotion =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Reduced-motion (or explicit settled mode) → one static settled frame.
    const staticFrame = reduceMotion || mode === "settled";

    // ── resolve tokens at runtime (fallbacks mirror v2-theme.css) ───────────
    const SIGNAL = hexToRgb(cssVar("--signal", "#48efca"), [72, 239, 202]); // runtime-fallback: --signal
    const SIGNAL_DIM = hexToRgb(cssVar("--signal-dim", "#39b894"), [57, 184, 148]); // runtime-fallback: --signal-dim
    const SPREAD = hexToRgb(cssVar("--spread", "#c8b68a"), [200, 182, 138]); // runtime-fallback: --spread
    const ARM_CONTROL = hexToRgb(cssVar("--arm-control", "#4fa8e0"), [79, 168, 224]); // runtime-fallback: --arm-control
    const ARM_TREAT = hexToRgb(cssVar("--arm-treat", "#e08bc4"), [224, 139, 196]); // runtime-fallback: --arm-treat
    const TEXT_MUT = hexToRgb(cssVar("--text-mut", "#929bae"), [146, 155, 174]); // runtime-fallback: --text-mut
    const rgba = (c: [number, number, number], a: number) =>
      `rgba(${c[0]},${c[1]},${c[2]},${a})`;

    // ── build the cohort (deterministic) ───────────────────────────────────
    const count = Math.max(120, Math.min(700, Math.round(particleCount)));
    const rng = mulberry32(seed);
    const amp = Math.max(0, Math.min(1, intensity));
    const particles: Particle[] = [];
    for (let i = 0; i < count; i++) {
      const arm: 0 | 1 = rng() < 0.5 ? 0 : 1;
      // Two arms react slightly differently: treatment skews a touch toward
      // "adopts" — a calm, honest separation, never a dramatic one.
      const center = arm === 0 ? 0.44 : 0.56;
      // Gaussian-ish reaction via averaged uniforms (bell, bounded 0..1).
      const r = (rng() + rng() + rng()) / 3;
      const reaction = Math.max(0.02, Math.min(0.98, center + (r - 0.5) * 0.66));
      particles.push({
        rx: rng(),
        ry: rng(),
        sx: 0,
        sy: 0,
        x: rng(),
        y: rng(),
        pa: rng() * Math.PI * 2,
        pb: rng() * Math.PI * 2,
        arm,
        reaction,
        size: 0.85 + rng() * 0.7,
      });
    }

    // Histogram layout: bin particles by reaction so the settled field forms a
    // real two-arm distribution silhouette (control bins below, treat above the
    // baseline, dodged — the §5.5 "histogram IS the verdict" read).
    const BINS = 26;
    const binCounts = new Array(BINS).fill(0);
    const sorted = [...particles].sort((a, b) => a.reaction - b.reaction);
    for (const p of sorted) {
      const bin = Math.min(BINS - 1, Math.floor(p.reaction * BINS));
      const stack = binCounts[bin]++;
      // x: centered column for the bin; y: stacked from a baseline, arm-dodged.
      const colX = (bin + 0.5) / BINS;
      const jitterX = (rng() - 0.5) * (0.9 / BINS);
      const baseline = 0.62; // settled baseline sits low so the cloud reads as a curve
      const rise = stack * 0.018; // stack height per particle
      p.sx = Math.max(0.02, Math.min(0.98, colX + jitterX));
      // control settles just under the baseline; treatment mirrors just above,
      // so the two arms read as a dodged pair around the reaction curve.
      p.sy =
        p.arm === 0
          ? Math.min(0.96, baseline + rise * 0.5 + 0.02)
          : Math.max(0.06, baseline - rise);
    }
    // Pooled mean (for the settled mean tick) — a fact about THIS canned cohort.
    let meanReaction = 0;
    for (const p of particles) meanReaction += p.reaction;
    meanReaction /= particles.length;

    // ── sizing (devicePixelRatio-aware) ─────────────────────────────────────
    let dpr = 1;
    let cssW = 0;
    let cssH = 0;
    function resize() {
      if (!canvas || !wrap) return;
      dpr = Math.min(2, window.devicePixelRatio || 1); // cap dpr at 2 for perf
      const rect = wrap.getBoundingClientRect();
      cssW = Math.max(1, rect.width);
      cssH = Math.max(1, rect.height);
      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      canvas.style.width = cssW + "px";
      canvas.style.height = cssH + "px";
    }
    resize();

    // Map normalized field space → device pixels, with a small inset margin so
    // particles never clip the edge.
    const MX = 0.04;
    const MY = 0.08;
    const px = (nx: number) => (MX + nx * (1 - 2 * MX)) * cssW * dpr;
    const py = (ny: number) => (MY + ny * (1 - 2 * MY)) * cssH * dpr;

    // ── one frame renderer ──────────────────────────────────────────────────
    // phase: 0 = full drift, 1 = fully settled distribution. wavefrontX in
    // device px (−1 = no wavefront). Additive blending for the dust glow.
    function draw(
      timeSec: number,
      phase: number,
      wavefrontX: number,
      ribbonA: number,
    ) {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const settle = easeInOut(phase);

      // CI ribbon (spread) — a soft vertical band around the mean, rising with
      // the settle. Drawn first (source-over), under the additive dust.
      if (ribbonA > 0.001) {
        ctx.globalCompositeOperation = "source-over";
        const meanX = px(0.06 + meanReaction * 0.9);
        const bandW = cssW * dpr * 0.16;
        const g = ctx.createLinearGradient(
          meanX - bandW / 2,
          0,
          meanX + bandW / 2,
          0,
        );
        g.addColorStop(0, rgba(SPREAD, 0));
        g.addColorStop(0.5, rgba(SPREAD, 0.12 * ribbonA));
        g.addColorStop(1, rgba(SPREAD, 0));
        ctx.fillStyle = g;
        ctx.fillRect(meanX - bandW / 2, py(0.04), bandW, py(0.97) - py(0.04));
        // settled mean tick — signal-dim (a canned baseline never the bright
        // live --signal lock, P5).
        ctx.strokeStyle = rgba(SIGNAL_DIM, 0.5 * ribbonA);
        ctx.lineWidth = 1 * dpr;
        ctx.beginPath();
        ctx.moveTo(meanX, py(0.05));
        ctx.lineTo(meanX, py(0.96));
        ctx.stroke();
      }

      ctx.globalCompositeOperation = "lighter"; // additive — low-α dust, not glow

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        // drift home: slow curl-ish wander around the rest position
        const driftAmp = 0.05 * amp;
        const dx =
          Math.sin(timeSec * 0.18 + p.pa) * driftAmp +
          Math.cos(timeSec * 0.11 + p.pb * 1.3) * driftAmp * 0.5;
        const dy =
          Math.cos(timeSec * 0.15 + p.pb) * driftAmp +
          Math.sin(timeSec * 0.09 + p.pa * 1.7) * driftAmp * 0.5;
        const driftX = p.rx + dx;
        const driftY = p.ry + dy;

        // settled target with a hairline residual shimmer so it stays "alive"
        const liveShimmer = staticFrame ? 0 : 0.004;
        const setX = p.sx + Math.sin(timeSec * 0.5 + p.pa) * liveShimmer;
        const setY = p.sy + Math.cos(timeSec * 0.5 + p.pb) * liveShimmer;

        // blend drift → settled by the global phase, but stagger per-index so
        // the field re-sorts as a wavefront, not a uniform snap.
        const stagger = (i / particles.length) * 0.25;
        const local = Math.max(0, Math.min(1, (settle - stagger) / (1 - 0.25)));
        const nx = driftX + (setX - driftX) * local;
        const ny = driftY + (setY - driftY) * local;
        p.x = nx;
        p.y = ny;

        const X = px(nx);
        const Y = py(ny);

        // color: drift = graphite (text-mut); settled = arm tints. Wavefront
        // particles flare to signal as the front passes them.
        let col = TEXT_MUT;
        let a = 0.5;
        if (local > 0.02) {
          col = p.arm === 0 ? ARM_CONTROL : ARM_TREAT;
          a = 0.42 + 0.4 * local;
        }
        // wavefront flare — only at/just-behind the sweeping front line
        if (wavefrontX >= 0) {
          const d = Math.abs(X - wavefrontX);
          const front = Math.max(0, 1 - d / (cssW * dpr * 0.08));
          if (front > 0.01) {
            col = SIGNAL;
            a = Math.max(a, 0.55 * front + 0.25);
          }
        }

        const r = p.size * dpr * (1 + 0.25 * local);
        ctx.fillStyle = rgba(col, a);
        ctx.beginPath();
        ctx.arc(X, Y, r, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalCompositeOperation = "source-over";
    }

    // ── static path: one settled frame, NO rAF ──────────────────────────────
    if (staticFrame) {
      draw(0, 1, -1, 1);
      // Redraw once on resize so the still frame stays crisp; no animation loop.
      let rs: number | undefined;
      const onResize = () => {
        if (rs) cancelAnimationFrame(rs);
        rs = requestAnimationFrame(() => {
          resize();
          draw(0, 1, -1, 1);
        });
      };
      window.addEventListener("resize", onResize);
      return () => {
        window.removeEventListener("resize", onResize);
        if (rs) cancelAnimationFrame(rs);
      };
    }

    // ── animated path: capped-fps rAF, paused when hidden/offscreen ─────────
    let raf = 0;
    let running = true; // tab visible
    let onScreen = true; // intersecting viewport
    let last = 0;
    const FRAME_MS = 1000 / 30; // ~30fps cap (§5.5)
    let startMs = 0;

    function loop(now: number) {
      raf = requestAnimationFrame(loop);
      if (!running || !onScreen) {
        last = now; // don't let dt jump after a pause
        return;
      }
      if (now - last < FRAME_MS) return;
      last = now;
      if (!startMs) startMs = now;
      const elapsed = (now - startMs) / 1000;

      // resolve the loop timeline → (phase, wavefrontX, ribbonA)
      const t = elapsed % T_LOOP;
      let phase = 0;
      let wavefrontX = -1;
      let ribbonA = 0;
      if (t < T_DRIFT) {
        phase = 0;
      } else if (t < T_DRIFT + T_SWEEP) {
        const u = (t - T_DRIFT) / T_SWEEP;
        phase = easeInOut(u) * 0.65;
        wavefrontX = u * cssW * dpr * 1.05; // front crosses the field
        ribbonA = 0;
      } else if (t < T_DRIFT + T_SWEEP + T_SETTLE) {
        const u = (t - T_DRIFT - T_SWEEP) / T_SETTLE;
        phase = 0.65 + 0.35 * easeInOut(u);
        ribbonA = easeInOut(u);
      } else if (t < T_DRIFT + T_SWEEP + T_SETTLE + T_HOLD) {
        phase = 1;
        ribbonA = 1;
      } else {
        const u =
          (t - T_DRIFT - T_SWEEP - T_SETTLE - T_HOLD) / T_DISSOLVE;
        phase = 1 - easeInOut(u);
        ribbonA = 1 - easeInOut(u);
      }

      draw(elapsed, phase, wavefrontX, ribbonA);
    }
    raf = requestAnimationFrame(loop);

    // pause on hidden tab
    const onVisibility = () => {
      running = document.visibilityState !== "hidden";
      last = performance.now();
    };
    document.addEventListener("visibilitychange", onVisibility);

    // pause when scrolled offscreen
    let io: IntersectionObserver | undefined;
    if ("IntersectionObserver" in window) {
      io = new IntersectionObserver(
        (entries) => {
          for (const e of entries) onScreen = e.isIntersecting;
          last = performance.now();
        },
        { threshold: 0.01 },
      );
      io.observe(wrap);
    }

    // resize handling (debounced via rAF)
    let rs: number | undefined;
    const onResize = () => {
      if (rs) cancelAnimationFrame(rs);
      rs = requestAnimationFrame(resize);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      if (rs) cancelAnimationFrame(rs);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("resize", onResize);
      io?.disconnect();
    };
  }, [particleCount, mode, intensity, seed]);

  return (
    <div
      ref={wrapRef}
      className={className}
      style={{ position: "relative", width: "100%", height, ...style }}
      aria-hidden={ariaLabel ? undefined : true}
      role={ariaLabel ? "img" : undefined}
      aria-label={ariaLabel}
    >
      {/* SSR-safe: empty canvas on the server; the cohort is drawn in useEffect
          after mount. A token-linked still wash sits behind it so the region is
          never a blank rectangle before first paint / with JS disabled. */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(70% 60% at 50% 42%, var(--signal-wash), transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <canvas
        ref={canvasRef}
        style={{
          position: "relative",
          display: "block",
          width: "100%",
          height: "100%",
        }}
      />
    </div>
  );
}

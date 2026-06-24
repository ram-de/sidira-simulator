"use client";

// ───────────────────────────────────────────────────────────────────────────
// /simulations/compare/[old]/[new] — the Phase-8 side-by-side diff (#45).
//
// Renders the GET /simulations/compare result: the two hypothesis labels in
// record voice, the confidence score arrow old→new (honest numbers, sign
// explicit — DESIGN.md §8.3), the weakness-category diff grouped by
// appeared/disappeared/changed, and the sentiment shift if present.
//
// Honesty law (§8.2/§8.3): no celebratory color, no invented verdict. The score
// delta's sign IS the signal — an improvement and a regression read the same
// hairline-and-ink way; the +/− and the word ("improved"/"regressed"/"flat")
// carry the polarity, never a fill. Lime budget (§4.1) is untouched — the only
// signal accent on this surface is the console focus ring.
//
// Renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar), scoped under a single `.rconsole` wrapper so the copied console
// tokens apply. Mirrors the token language of SimulationDetailV2.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiError,
  compareSimulations,
  type SimulationComparison,
  type WeaknessCategoryDiff,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";

function formatCategory(cat: string): string {
  return cat
    .split("_")
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function fmtScore(n: number | null): string {
  return n == null ? "—.—" : n.toFixed(1);
}

function fmtSignedScore(n: number | null): string {
  if (n == null) return "—.—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;
}

function fmtPct(n: number | null): string {
  return n == null ? "—" : `${(n * 100).toFixed(0)}%`;
}

function fmtSignedPct(n: number | null): string {
  if (n == null) return "—";
  const pts = n * 100;
  return `${pts >= 0 ? "+" : ""}${pts.toFixed(0)} pts`;
}

function shortId(id: string): string {
  return id.slice(0, 8).toUpperCase();
}

// Score-delta direction — the WORD that co-signals the sign (§8.2: color never
// carries state alone). Honest about a missing side.
function deltaWording(delta: number | null): string {
  if (delta == null) return "ONE SIDE HAS NO SCORE";
  if (delta > 0) return "AGREEMENT IMPROVED";
  if (delta < 0) return "AGREEMENT REGRESSED";
  return "AGREEMENT UNCHANGED";
}

const RCONSOLE_CSS = `
.rconsole{
  --console-900:#0B1220; --console-850:#10192A; --console-800:#161F32;
  --console-750:#1D2740; --console-700:#26314C; --console-line:#33405C;
  --text-hi:#E7ECF5; --text:#C6CCD8; --text-mut:#929BAE; --text-faint:#646E84;
  --signal:#48EFCA; --signal-dim:#39B894;
  --spread:#C8B68A; --spread-dim:#90815F;
  --arm-control:#4FA8E0; --arm-treat:#E08BC4;
  --edge-warn:#C9A227; --alert:#F0683C;
  --r-well:4px; --r-panel:8px; --r-frame:10px;
  --font-mono:var(--v2-font-mono,var(--font-mono,ui-monospace,"JetBrains Mono",SFMono-Regular,monospace));
  color:var(--text); font-family:var(--font-mono); font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased; font-variant-numeric:tabular-nums;
}
.rconsole *{box-sizing:border-box; font-variant-numeric:tabular-nums;}
.rconsole a{color:inherit; text-decoration:none;}
.rconsole ::selection{background:rgba(72,239,202,.12); color:var(--text-hi);}
.rconsole .wrap{max-width:1100px; margin:0 auto; padding:32px 24px 96px;}
.rconsole .desig{font-size:11px; font-weight:500; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text-mut);}

/* breadcrumb + back-to-parent link */
.rconsole .crumbrow{display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  margin-bottom:22px;}
.rconsole .backlink{font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--text-mut); border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:5px 10px; display:inline-block;}
.rconsole .backlink:hover{color:var(--text-hi); border-color:var(--text-mut);}
.rconsole .crumb{font-size:11px; letter-spacing:.08em; text-transform:uppercase;
  color:var(--text-mut);}
.rconsole .crumb b{color:var(--text-hi); font-weight:500;}

/* the headline score arrow — old → new, sign explicit. No color fill. */
.rconsole .scorehead{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-frame);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04); padding:28px 32px;
  margin-bottom:32px;}
.rconsole .scorehead .lab{font-size:11px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--text-mut); margin-bottom:18px;}
.rconsole .scoreflow{display:flex; align-items:baseline; gap:22px; flex-wrap:wrap;}
.rconsole .scoreflow .num{font-weight:500; font-size:56px; line-height:.95;
  color:var(--text-hi); letter-spacing:-.01em;}
.rconsole .scoreflow .num.muted{color:var(--text-mut);}
.rconsole .scoreflow .arrow{font-size:30px; color:var(--text-mut);
  align-self:center;}
.rconsole .scoreflow .of{font-size:18px; color:var(--text-mut);}
.rconsole .scoreflow .delta{font-size:24px; color:var(--text-hi); font-weight:500;
  margin-left:6px;}
.rconsole .scoreword{margin-top:16px; display:inline-flex; align-items:center;
  gap:9px; font-size:12px; letter-spacing:.05em; text-transform:uppercase;
  color:var(--text-hi); border:1px solid var(--console-line);
  border-radius:var(--r-well); padding:5px 11px;}
.rconsole .scoreword .gl{color:var(--spread-dim); font-size:13px;}
.rconsole .scorefoot{font-size:11px; letter-spacing:.02em; line-height:1.7;
  color:var(--text-mut); margin-top:14px; max-width:78ch;}

/* record-voice hypothesis pair */
.rconsole .pair{display:grid; grid-template-columns:1fr 1fr; gap:24px;
  margin-bottom:32px;}
.rconsole .record{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04); overflow:hidden;}
.rconsole .record-head{display:flex; align-items:baseline; gap:10px;
  flex-wrap:wrap; padding:11px 18px; border-bottom:1px solid var(--console-line);
  background:rgba(11,18,32,.4); font-size:10.5px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--text-mut);}
.rconsole .record-head .rid{color:var(--text-hi); font-family:var(--font-mono);}
.rconsole .record-head .rsc{margin-left:auto; color:var(--text-hi);
  font-family:var(--font-mono);}
.rconsole .record-body{padding:20px 18px;}
.rconsole .record-body .label{font-size:16px; line-height:1.55; color:var(--text-hi);}
.rconsole .record-body .open{margin-top:14px; font-size:10px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--text-mut);
  border:1px solid var(--console-line); border-radius:var(--r-well);
  padding:4px 9px; display:inline-block;}
.rconsole .record-body .open:hover{color:var(--text-hi); border-color:var(--text-mut);}

/* sections */
.rconsole .sec{margin-bottom:32px;}
.rconsole .sechead{font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--text-mut); margin:0 0 16px;}
.rconsole .panel{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04); padding:22px 24px;}

/* weakness diff — grouped change rows */
.rconsole .wkgroup{margin-bottom:18px;}
.rconsole .wkgroup:last-child{margin-bottom:0;}
.rconsole .wkgroup-head{font-size:11px; letter-spacing:.05em; text-transform:uppercase;
  color:var(--text-mut); font-weight:600; padding-bottom:8px;
  border-bottom:1px solid var(--console-line); display:flex; gap:8px;
  align-items:baseline;}
.rconsole .wkgroup-head .n{color:var(--text-faint); font-weight:400;}
.rconsole .wkdiff{display:grid; grid-template-columns:minmax(0,1fr) auto;
  gap:16px; align-items:baseline; padding:11px 0;
  border-top:1px solid var(--console-line);}
.rconsole .wkdiff:first-of-type{border-top:none;}
.rconsole .wkdiff .cat{font-size:14px; color:var(--text-hi); font-weight:500;
  display:flex; align-items:center; gap:9px;}
.rconsole .wkdiff .gl{font-family:var(--font-mono); font-size:13px; width:13px;
  display:inline-block; text-align:center;}
.rconsole .wkdiff .gl.up{color:var(--alert);}
.rconsole .wkdiff .gl.down{color:var(--signal-dim);}
.rconsole .wkdiff .gl.flat{color:var(--text-mut);}
.rconsole .wkdiff .counts{font-size:12.5px; color:var(--text-mut);
  font-family:var(--font-mono); white-space:nowrap;}
.rconsole .wkdiff .counts b{color:var(--text-hi); font-weight:500;}
.rconsole .nodiff{font-size:13px; color:var(--text-mut); line-height:1.6;}

/* refinement suggestion deltas */
.rconsole .refcols{display:grid; grid-template-columns:1fr 1fr; gap:24px;}
.rconsole .refcol .rh{font-size:11px; letter-spacing:.05em; text-transform:uppercase;
  color:var(--text-mut); font-weight:600; margin-bottom:10px;}
.rconsole .refcol ul{margin:0; padding-left:18px;}
.rconsole .refcol li{font-size:13.5px; color:var(--text); line-height:1.55;
  margin-bottom:7px;}
.rconsole .refcol .empty{font-size:13px; color:var(--text-faint);}

/* sentiment shift */
.rconsole .skv{display:flex; gap:40px; flex-wrap:wrap;}
.rconsole .skv .k{font-size:10px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--text-mut); margin-bottom:5px;}
.rconsole .skv .v{font-size:24px; color:var(--text-hi); font-weight:500;}
.rconsole .skv .v.muted{color:var(--text-mut);}

/* quiet states (loading / 404 / error) */
.rconsole .quiet-card{background:var(--console-800);
  border:1px solid var(--console-line); border-radius:var(--r-panel);
  padding:32px; box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.rconsole .quiet-card.failed{border-color:rgba(240,104,60,.55);}
.rconsole .quiet-head{font-size:12px; letter-spacing:.06em; text-transform:uppercase;
  display:flex; align-items:center; gap:9px; margin-bottom:14px;}
.rconsole .quiet-head.pending{color:var(--text-mut);}
.rconsole .quiet-head.failed{color:var(--alert);}
.rconsole .quiet-body{font-size:13.5px; color:var(--text-mut); line-height:1.6;
  max-width:64ch;}
.rconsole .quiet-body a{color:var(--text-hi); text-decoration:underline;
  text-decoration-color:var(--console-line);}
.rconsole .glyph-hollow{color:var(--spread-dim);}

/* focus rings */
.rconsole a:focus-visible, .rconsole button:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px;
  border-radius:var(--r-well);}

@media (max-width:859px){
  .rconsole .pair, .rconsole .refcols{grid-template-columns:1fr;}
  .rconsole .scoreflow .num{font-size:44px;}
}
@media (prefers-reduced-motion:reduce){
  .rconsole *{animation:none!important;}
}
`;

function WeaknessGroup({
  title,
  diffs,
}: {
  title: string;
  diffs: WeaknessCategoryDiff[];
}) {
  if (diffs.length === 0) return null;
  return (
    <div className="wkgroup">
      <div className="wkgroup-head">
        <span>{title}</span>
        <span className="n">{diffs.length}</span>
      </div>
      {diffs.map((d) => {
        const delta = d.agent_count_delta;
        const glClass = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
        const glyph = delta > 0 ? "+" : delta < 0 ? "−" : "~";
        return (
          <div className="wkdiff" key={d.category}>
            <span className="cat">
              <span className={`gl ${glClass}`} aria-hidden="true">
                {glyph}
              </span>
              {formatCategory(d.category)}
            </span>
            <span className="counts">
              <b>{d.old_agent_count}</b> → <b>{d.new_agent_count}</b> agents (
              {fmtSignedScore(d.agent_count_delta)}) · {fmtPct(d.old_frequency)}{" "}
              → {fmtPct(d.new_frequency)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function ComparisonV2() {
  const params = useParams<{ old: string; new: string }>();
  const oldId = params?.old ?? "";
  const newId = params?.new ?? "";

  const [data, setData] = useState<SimulationComparison | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!oldId || !newId) return;
    setLoaded(false);
    setNotFound(false);
    setError(null);
    (async () => {
      try {
        const cmp = await compareSimulations(oldId, newId);
        if (cancelled) return;
        setData(cmp);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          setNotFound(true);
        } else {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [oldId, newId]);

  // ── quiet states ──────────────────────────────────────────────────────────
  if (!loaded) {
    return (
      <AppShellV2 activeNav="simulations" title="Compare" surface="console">
        <div className="rconsole">
          <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />
          <div className="wrap">
            <div className="quiet-card">
              <div className="quiet-head pending">
                <span className="glyph-hollow">◇</span> LOADING COMPARISON…
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  if (notFound) {
    return (
      <AppShellV2 activeNav="simulations" title="Compare" surface="console">
        <div className="rconsole">
          <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />
          <div className="wrap">
            <div className="quiet-card" role="alert">
              <div className="quiet-head pending">COMPARISON UNAVAILABLE</div>
              <div className="quiet-body">
                One or both of these simulations could not be compared. Both must
                exist, be owned by you, and have finished (status{" "}
                <span style={{ color: "var(--text-hi)" }}>complete</span>) before
                a diff is available.
                <div style={{ marginTop: 16 }}>
                  <Link href={`/simulations/${oldId}`}>← {shortId(oldId)}</Link>
                  {"   ·   "}
                  <Link href={`/simulations/${newId}`}>{shortId(newId)} →</Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  if (error || !data) {
    return (
      <AppShellV2 activeNav="simulations" title="Compare" surface="console">
        <div className="rconsole">
          <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />
          <div className="wrap">
            <div className="quiet-card failed">
              <div className="quiet-head failed">UNABLE TO LOAD COMPARISON</div>
              <div className="quiet-body" role="alert">
                {error ?? "Unable to load comparison."}
              </div>
            </div>
          </div>
        </div>
      </AppShellV2>
    );
  }

  // ── loaded ─────────────────────────────────────────────────────────────────
  const delta = data.confidence_score_delta;
  const appeared = data.weakness_category_diffs.filter(
    (d) => d.change === "appeared",
  );
  const disappeared = data.weakness_category_diffs.filter(
    (d) => d.change === "disappeared",
  );
  const changed = data.weakness_category_diffs.filter(
    (d) => d.change === "changed",
  );
  const hasWeaknessDiff =
    appeared.length + disappeared.length + changed.length > 0;

  const hasSentiment =
    data.old_sentiment_positive_share != null ||
    data.new_sentiment_positive_share != null;

  return (
    <AppShellV2 activeNav="simulations" title="Compare" surface="console">
      <div className="rconsole">
        <style dangerouslySetInnerHTML={{ __html: RCONSOLE_CSS }} />
        <div className="wrap">
          {/* breadcrumb + back-to-parent link (#45: reachable from lineage) */}
          <div className="crumbrow">
            <Link href={`/simulations/${data.old.id}`} className="backlink">
              ← Parent simulation
            </Link>
            <span className="crumb">
              COMPARE <b>{shortId(data.old.id)}</b> → <b>{shortId(data.new.id)}</b>
            </span>
          </div>

          {/* score arrow old → new, sign explicit (§8.3 honest numbers) */}
          <div className="scorehead">
            <div className="lab">SIMULATION AGREEMENT — RAW, UNCALIBRATED</div>
            <div className="scoreflow">
              <span
                className={`num${data.old_confidence_score == null ? " muted" : ""}`}
              >
                {fmtScore(data.old_confidence_score)}
              </span>
              <span className="arrow" aria-hidden="true">
                →
              </span>
              <span
                className={`num${data.new_confidence_score == null ? " muted" : ""}`}
              >
                {fmtScore(data.new_confidence_score)}
              </span>
              <span className="of">/ 100</span>
              <span className="delta">{fmtSignedScore(delta)}</span>
            </div>
            <div className="scoreword">
              <span className="gl" aria-hidden="true">
                ◇
              </span>
              {deltaWording(delta)}
            </div>
            <div className="scorefoot">
              Both readings are raw simulation agreement — no live-outcome
              calibration has been applied (ledger empty). The delta is the new
              run&rsquo;s agreement minus the old run&rsquo;s, in agreement
              points.
            </div>
          </div>

          {/* hypothesis pair — record voice (§7.6): labels render as records */}
          <div className="pair">
            {[data.old, data.new].map((ref, idx) => (
              <div className="record" key={ref.id}>
                <div className="record-head">
                  <span>{idx === 0 ? "OLD" : "NEW"}</span>
                  <span className="rid">{shortId(ref.id)}</span>
                  <span className="rsc">{fmtScore(ref.confidence_score)}</span>
                </div>
                <div className="record-body">
                  <div className="label">{ref.hypothesis_label}</div>
                  <Link href={`/simulations/${ref.id}`} className="open">
                    Open reading →
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {/* weakness category diff — grouped appeared / disappeared / changed */}
          <div className="sec">
            <h2 className="sechead">WEAKNESS CATEGORIES</h2>
            <div className="panel">
              {hasWeaknessDiff ? (
                <>
                  <WeaknessGroup title="Appeared" diffs={appeared} />
                  <WeaknessGroup title="Disappeared" diffs={disappeared} />
                  <WeaknessGroup title="Changed" diffs={changed} />
                </>
              ) : (
                <p className="nodiff">
                  No weakness category appeared, disappeared, or changed between
                  these two runs.
                </p>
              )}
            </div>
          </div>

          {/* refinement suggestion deltas — added / resolved */}
          {(data.refinement_suggestions_added.length > 0 ||
            data.refinement_suggestions_resolved.length > 0) && (
            <div className="sec">
              <h2 className="sechead">REFINEMENT SUGGESTIONS</h2>
              <div className="panel">
                <div className="refcols">
                  <div className="refcol">
                    <div className="rh">Resolved (gone in new)</div>
                    {data.refinement_suggestions_resolved.length > 0 ? (
                      <ul>
                        {data.refinement_suggestions_resolved.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className="empty">None resolved.</div>
                    )}
                  </div>
                  <div className="refcol">
                    <div className="rh">Added (new in new)</div>
                    {data.refinement_suggestions_added.length > 0 ? (
                      <ul>
                        {data.refinement_suggestions_added.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className="empty">None added.</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* sentiment shift — data, not an alarm (§8.5: ink-muted, never red) */}
          {hasSentiment && (
            <div className="sec">
              <h2 className="sechead">SENTIMENT — POSITIVE SHARE</h2>
              <div className="panel">
                <div className="skv">
                  <div>
                    <div className="k">Old</div>
                    <div
                      className={`v${data.old_sentiment_positive_share == null ? " muted" : ""}`}
                    >
                      {fmtPct(data.old_sentiment_positive_share)}
                    </div>
                  </div>
                  <div>
                    <div className="k">New</div>
                    <div
                      className={`v${data.new_sentiment_positive_share == null ? " muted" : ""}`}
                    >
                      {fmtPct(data.new_sentiment_positive_share)}
                    </div>
                  </div>
                  <div>
                    <div className="k">Shift</div>
                    <div
                      className={`v${data.sentiment_positive_share_delta == null ? " muted" : ""}`}
                    >
                      {fmtSignedPct(data.sentiment_positive_share_delta)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShellV2>
  );
}

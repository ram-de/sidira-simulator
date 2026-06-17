"use client";

// ───────────────────────────────────────────────────────────────────────────
// /personas/[id] — the v2 LIGHT "Sheet" (Reading-Console record) reskin.
//
// FORK-AND-RESTYLE of PersonaPackDetailLegacy.tsx (the FROZEN source of truth for
// ALL behaviour). This file reproduces every data load, state branch, honesty
// branch, conditional and <Link> the legacy record has — byte-for-byte in LOGIC
// — and changes ONLY the presentation (markup + scoped CSS classes + layout)
// into the light Sheet language of design-rethink/mocks/persona-detail.html.
//
// It renders INSIDE AppShellV2 surface="sheet" (the shell owns the dark Console
// rail + the appbar; surface="sheet" gives a light <main> with padding:0). The
// body is scoped under a single `.rsheet` wrapper so the copied RSHEET_CSS
// applies; we do NOT emit the mock's own .topbar/.shell chrome — the shell owns
// that. The `.rsheet` wrapper re-establishes the Sheet background + its own
// padding (the sheet <main> ships padding:0).
//
// HONESTY (DESIGN.md §8.1): no fabricated fields. The mock's frozen distribution
// posters, the Pack Reaction Map, per-row ± Spread Stamps, build-seed / model /
// population-n spine rows, and arm tints all describe data the legacy detail
// read does NOT carry, so NONE of them are rendered here — only the version /
// capture / stability / schema / persona-count / weight-schemes / personas the
// legacy record actually loads. Snapshot values stay BARE (the legacy renders no
// ±). The ◇ hollow glyph marks the UNCALIBRATED state verbatim; no verdict shows
// on this record, so no verdict glyph appears either.
// ───────────────────────────────────────────────────────────────────────────

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShellV2 from "@/components/v2/AppShellV2";
import {
  ApiError,
  getPersonaPackDetail,
  type PersonaPackDetail,
  type PersonaProfileView,
  type ProfileBlockView,
  type WeightSchemeView,
} from "@/lib/api";

type Fetchable<T> =
  | { state: "loading" }
  | { state: "ready"; data: T }
  | { state: "missing" }
  | { state: "error"; message: string };

// ── scoped light Sheet tokens (mirrors the persona-detail.html mock palette +
//    structure: masthead, meta-strip receipt, Provenance Spine column, persona
//    record cards, behavioral-snapshot logbook, comparison blocks). Token-driven
//    light surface; re-establishes the Sheet background + own padding because the
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
  max-width:1140px; margin:0 auto; padding:0 0 96px;}
.rsheet .reading{padding:0 56px; min-width:0;}

/* Provenance Spine — the page's ONE provenance, in a left binder margin */
.rsheet .spine{position:relative; border-right:.75px solid var(--sheet-line);
  padding:44px 24px 80px 0;}
.rsheet .spine-sticky{position:sticky; top:24px; display:flex; flex-direction:column;}
.rsheet .spine-title{font-family:var(--font-mono); font-size:10.5px;
  letter-spacing:.13em; text-transform:uppercase; color:var(--sheet-mut);
  margin:0 0 18px;}
.rsheet .spine-row{padding:12px 0; border-top:.75px solid var(--sheet-line);}
.rsheet .spine-row:first-of-type{border-top:none;}
.rsheet .spine-k{font-family:var(--font-mono); font-size:10.5px;
  letter-spacing:.09em; text-transform:uppercase; color:var(--sheet-mut);
  display:block; margin-bottom:5px;}
.rsheet .spine-v{font-family:var(--font-mono); font-size:12.5px;
  letter-spacing:.01em; color:var(--sheet-ink); line-height:1.4; display:block;
  overflow-wrap:anywhere;}
.rsheet .calib{display:inline-flex; align-items:baseline; gap:5px;
  color:var(--sheet-mut);}
.rsheet .glyph-hollow{color:var(--sheet-spread); font-size:12px;}
.rsheet .spine-note{font-family:var(--font-sans); font-size:12px; line-height:1.5;
  color:var(--sheet-mut); margin:18px 0 0;}

/* masthead */
.rsheet .masthead{padding:48px 0 0;}
.rsheet .eyebrow{font-family:var(--font-mono); font-size:11px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--sheet-mut); margin:0 0 16px;
  display:flex; gap:10px; flex-wrap:wrap; align-items:center;}
.rsheet h1.title{font-family:var(--font-sans); font-weight:600; font-size:38px;
  line-height:1.05; letter-spacing:-.025em; margin:0; color:var(--sheet-ink);
  text-wrap:balance;}

/* meta-strip receipt */
.rsheet .meta-strip{margin:36px 0 0; background:var(--sheet-raised);
  border:.75px solid var(--sheet-line); border-radius:var(--r-panel);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.6);
  display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));}
.rsheet .meta-cell{padding:18px 20px; border-left:.75px solid var(--sheet-line);}
.rsheet .meta-cell:first-child{border-left:none;}
.rsheet .meta-cell.focal{
  background:linear-gradient(180deg,rgba(111,94,51,.10),rgba(111,94,51,.02) 78%);
  box-shadow:inset 2px 0 0 var(--sheet-spread);}
.rsheet .meta-k{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--sheet-mut); display:block;
  margin-bottom:8px;}
.rsheet .meta-v{font-family:var(--font-mono); font-size:23px; font-weight:500;
  letter-spacing:-.01em; color:var(--sheet-ink); display:flex;
  align-items:baseline; gap:6px;}
.rsheet .meta-v small{font-size:12px; color:var(--sheet-mut); font-weight:400;}
.rsheet .meta-v.hero{font-size:42px; line-height:.95; gap:8px;}
.rsheet .meta-v.hero .gl{font-size:20px; color:var(--sheet-spread);
  font-weight:400; align-self:flex-start; line-height:1; position:relative; top:2px;}

/* weight-scheme chips + honesty */
.rsheet .scheme-row{display:flex; gap:8px; flex-wrap:wrap; margin:28px 0 0;
  align-items:center;}
.rsheet .chip{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.04em;
  text-transform:uppercase; border:.75px solid var(--sheet-line);
  color:var(--sheet-ink); background:var(--sheet-raised); border-radius:var(--r-well);
  padding:4px 9px;}
.rsheet .chip.off{color:var(--sheet-mut); border-style:dashed;}
.rsheet .honesty{font-family:var(--font-sans); font-size:13.5px; line-height:1.55;
  color:var(--sheet-mut); max-width:64ch; margin:16px 0 0;}
.rsheet .honesty strong{color:var(--sheet-ink); font-weight:500;}

/* section divider */
.rsheet .sec-head{display:flex; align-items:baseline; gap:14px; margin:72px 0 0;
  padding-bottom:12px; border-bottom:.75px solid var(--sheet-line);}
.rsheet .sec-head h2{font-family:var(--font-sans); font-weight:600; font-size:22px;
  letter-spacing:-.02em; margin:0; color:var(--sheet-ink);}
.rsheet .sec-head .spacerline{flex:1;}
.rsheet .sec-head .count{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.06em; color:var(--sheet-mut); text-transform:uppercase;}

/* one persona record card */
.rsheet .persona{margin:36px 0 0; background:var(--sheet-raised);
  border:.75px solid var(--sheet-line); border-radius:var(--r-panel);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.6); overflow:hidden;}
.rsheet .persona-head{padding:24px 30px 22px;
  border-bottom:.75px solid var(--sheet-line);}
.rsheet .persona-name{font-family:var(--font-sans); font-weight:600; font-size:19px;
  letter-spacing:-.012em; display:flex; align-items:baseline; gap:12px;
  flex-wrap:wrap; color:var(--sheet-ink);}
.rsheet .share-row{display:flex; gap:7px; flex-wrap:wrap; margin-top:14px;}
.rsheet .desig{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.04em;
  text-transform:uppercase; border:.75px solid var(--sheet-line);
  color:var(--sheet-mut); border-radius:var(--r-well); padding:2px 7px;
  white-space:nowrap;}
.rsheet .desig.share b{color:var(--sheet-ink); font-weight:500;}

.rsheet .persona-body{padding:26px 30px 30px; max-width:740px;}
.rsheet .prose{font-family:var(--font-serif); font-weight:400; font-size:17px;
  line-height:1.62; letter-spacing:-.003em; color:var(--sheet-ink); margin:0;
  max-width:64ch; text-wrap:pretty;}
.rsheet .subhead{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.13em;
  text-transform:uppercase; color:var(--sheet-mut); display:block;
  margin:26px 0 9px;}
.rsheet .jtbd{font-family:var(--font-serif); font-size:17px; line-height:1.6;
  color:var(--sheet-ink); margin:0; max-width:64ch;}

/* behavioral snapshot — recorded logbook on Sheet */
.rsheet .snap{display:grid; grid-template-columns:auto 1fr; gap:0 16px; margin:0;
  max-width:560px;}
.rsheet .snap dt{font-size:13.5px; color:var(--sheet-mut); padding:7px 0;
  border-top:.75px solid var(--sheet-line);}
.rsheet .snap dd{margin:0; font-family:var(--font-mono); font-size:13px;
  color:var(--sheet-ink); padding:7px 0; border-top:.75px solid var(--sheet-line);
  text-align:right; white-space:nowrap; letter-spacing:.02em;}
.rsheet .snap .pair:first-child dt,
.rsheet .snap .pair:first-child dd{border-top:none;}

/* comparison block — divergence from population, ink + glyph only, no valence */
.rsheet .cmp{margin:28px 0 0; padding:20px 22px; background:var(--sheet-sunk);
  border-radius:var(--r-well); border:.75px solid var(--sheet-line);}
.rsheet .cmp .head{font-family:var(--font-mono); font-size:10.5px;
  letter-spacing:.11em; text-transform:uppercase; color:var(--sheet-mut);
  display:block;}
.rsheet .cmp .intro{font-family:var(--font-serif); font-size:16px; line-height:1.55;
  margin:11px 0 0; color:var(--sheet-ink); max-width:62ch;}
.rsheet .cmp ul{margin:14px 0 0; padding:0; list-style:none; display:flex;
  flex-direction:column;}
.rsheet .cmp li{font-size:14.5px; line-height:1.5; padding:9px 0;
  border-top:.75px solid var(--sheet-line); display:flex; gap:12px;
  align-items:baseline;}
.rsheet .cmp li:first-child{border-top:none;}
.rsheet .cmp .mag{font-family:var(--font-mono); font-size:11px; letter-spacing:.02em;
  text-transform:uppercase; color:var(--sheet-ink); font-weight:500;
  flex:0 0 auto; min-width:128px;}
.rsheet .cmp .lab{color:var(--sheet-ink);}
.rsheet .cmp .tail{font-size:12px; line-height:1.5; color:var(--sheet-mut);
  margin:14px 0 0;}
.rsheet .cmp .note{font-size:12px; line-height:1.5; color:var(--sheet-mut);
  margin:14px 0 0; border-top:.75px solid var(--sheet-line); padding-top:11px;}

/* quiet states (loading / missing / error) */
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
  border-top:.75px solid var(--sheet-line); display:flex;
  justify-content:space-between; flex-wrap:wrap; gap:16px; align-items:center;}
.rsheet .recfoot .l{font-family:var(--font-mono); font-size:11px;
  color:var(--sheet-mut); letter-spacing:.04em;}
.rsheet .recfoot .gl-foot{color:var(--sheet-spread);}
.rsheet .recfoot a{font-family:var(--font-mono); font-size:11px;
  color:var(--sheet-ink); border-bottom:1px dotted var(--sheet-mut);
  padding-bottom:1px;}
.rsheet .recfoot a:hover{border-bottom-style:solid;}

/* crumb / link affordance reused inside notes */
.rsheet .sheet-link{color:var(--sheet-ink); border-bottom:1px dotted var(--sheet-mut);
  transition:border-color 80ms ease-out;}
.rsheet .sheet-link:hover{border-bottom-color:var(--sheet-ink);}

.rsheet a:focus-visible{outline:2px solid var(--sheet-signal); outline-offset:2px;
  border-radius:var(--r-well);}

@media (max-width:1100px){
  .rsheet .shell{grid-template-columns:1fr;}
  .rsheet .spine{border-right:none; border-bottom:.75px solid var(--sheet-line);
    padding:24px 0;}
  .rsheet .spine-sticky{position:static;}
  .rsheet .reading{padding:0 24px;}
  .rsheet .masthead{padding:36px 0 0;}
  .rsheet .quiet{padding:36px 24px 96px;}
}
`;

export default function PersonaPackDetailV2({ params }: { params: { id: string } }) {
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

  // ── pre-content states (loading / missing / error) — light Sheet quiet states.
  if (pack.state !== "ready") {
    return (
      <AppShellV2 activeNav="personas" title="Persona pack" surface="sheet">
      <div className="rsheet">
        <style>{RSHEET_CSS}</style>
        <div className="quiet">
          {pack.state === "loading" && (
            <p className="loadnote">Loading the persona pack…</p>
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
        </div>
      </div>
      </AppShellV2>
    );
  }

  const data = pack.data;
  const unavailable = data.weight_schemes.filter((s) => !s.available);

  return (
    <AppShellV2 activeNav="personas" title="Persona pack" surface="sheet">
    <div className="rsheet">
      <style>{RSHEET_CSS}</style>

      <div className="shell">
        {/* ── Provenance Spine — only the fields the detail read actually carries ── */}
        <aside className="spine">
          <div className="spine-sticky">
            <p className="spine-title">Provenance</p>
            <div className="spine-row">
              <span className="spine-k">Snapshot</span>
              <span className="spine-v mono">{data.version.toUpperCase()}</span>
            </div>
            <div className="spine-row">
              <span className="spine-k">Captured</span>
              <span className="spine-v mono">{formatCapture(data.generated_at)}</span>
            </div>
            <div className="spine-row">
              <span className="spine-k">Schema</span>
              <span className="spine-v mono">{data.schema_version}</span>
            </div>
            <div className="spine-row">
              <span className="spine-k">Stability</span>
              <span className="spine-v mono">{data.stability_score.toFixed(2)}</span>
            </div>
            <div className="spine-row">
              <span className="spine-k">Calibration</span>
              <span className="spine-v calib">
                <span className="glyph-hollow">◇</span> UNCALIBRATED
              </span>
            </div>
            <p className="spine-note">
              No ground-truth holdout has graded this pack. The figures on this
              record are modelled, not measured.
            </p>
          </div>
        </aside>

        {/* ── Reading column ──────────────────────────────────────────────────── */}
        <main className="reading">
          <header className="masthead">
            <p className="eyebrow">
              <span>{headerVersion.toUpperCase()} · persona pack</span>
              <span className="desig">MODELLED POPULATION</span>
            </p>
            <h1 className="title">Persona pack</h1>

            {/* the receipt — recorded facts. Only fields the legacy PackMeta has. */}
            <div className="meta-strip">
              <div className="meta-cell">
                <span className="meta-k">{data.is_starter ? "Starter pack" : "Active pack"}</span>
                <span className="meta-v">
                  {data.persona_count}{" "}
                  <small>persona{data.persona_count === 1 ? "" : "s"}</small>
                </span>
              </div>
              <div className="meta-cell">
                <span className="meta-k">Snapshot</span>
                <span className="meta-v">{data.version.toUpperCase()}</span>
              </div>
              <div className="meta-cell focal">
                <span className="meta-k">Cluster stability</span>
                <span className="meta-v hero">
                  <span className="gl">◇</span>
                  {data.stability_score.toFixed(2)}
                </span>
              </div>
              <div className="meta-cell">
                <span className="meta-k">Schema</span>
                <span className="meta-v">{data.schema_version}</span>
              </div>
            </div>

            {/* Weight bases — head count always present; revenue/order appear only
                when the source covered every persona (§7.6: state absence honestly). */}
            <div className="scheme-row">
              {data.weight_schemes
                .filter((s) => s.available)
                .map((s) => (
                  <span key={s.key} className="chip">
                    {s.label.toUpperCase()}
                  </span>
                ))}
              {unavailable.map((s) => (
                <span key={s.key} className="chip off">
                  {s.label} · unavailable
                </span>
              ))}
            </div>
            {unavailable.map((s) => (
              <p key={s.key} className="honesty">
                <strong>{s.label}</strong> — {s.note}
              </p>
            ))}

            {data.is_starter && (
              <p className="honesty">
                These are generic placeholder personas so you can click through Sidira right away —
                they are <strong>not</strong> built from your data. Build a real pack, or seed the
                sample workspace, before trusting any reading.
              </p>
            )}
          </header>

          {/* ── Personas ───────────────────────────────────────────────────────── */}
          <div className="sec-head">
            <h2>The segments</h2>
            <span className="spacerline" />
            <span className="count">
              {data.persona_count} record{data.persona_count === 1 ? "" : "s"} · schema{" "}
              {data.schema_version}
            </span>
          </div>

          {data.personas.map((persona) => (
            <PersonaSheet
              key={persona.id}
              persona={persona}
              schemes={data.weight_schemes}
            />
          ))}

          <footer className="recfoot">
            <span className="l">
              RECORD · {data.version.toUpperCase()} ·{" "}
              <span className="gl-foot">◇</span> UNCALIBRATED · generated{" "}
              {formatCapture(data.generated_at)}
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
    <section className="persona">
      <div className="persona-head">
        <div className="persona-name">
          <span>{persona.name}</span>
          <span className="desig">{persona.id}</span>
        </div>
        {shareChips.length > 0 && (
          <div className="share-row">
            {shareChips.map((c) => (
              <span key={c.key} className="desig share">
                <b>{(c.pct * 100).toFixed(0)}%</b> {c.label.toUpperCase()}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="persona-body">
        <p className="prose">{persona.description}</p>

        {persona.jtbd && (
          <>
            <span className="subhead">Jobs to be done</span>
            <p className="jtbd">{persona.jtbd}</p>
          </>
        )}

        {snapshot.length > 0 && (
          <>
            <span className="subhead">Behavioral snapshot</span>
            <dl className="snap">
              {snapshot.map(([k, v]) => (
                <div key={k} className="pair" style={{ display: "contents" }}>
                  <dt>{humanizeKey(k)}</dt>
                  <dd>{formatSnapshotValue(v)}</dd>
                </div>
              ))}
            </dl>
          </>
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
    <div className="cmp">
      <span className="head">{block.heading}</span>
      <p className="intro">{block.intro}</p>
      <ul>
        {block.deltas.map((d, i) => (
          <li key={i}>
            <span className="mag">
              {d.magnitude} {d.direction}
            </span>
            <span className="lab">{d.label}</span>
          </li>
        ))}
      </ul>
      {block.tail_count > 0 && (
        <p className="tail">
          …plus {block.tail_count} further, smaller difference{block.tail_count === 1 ? "" : "s"} —
          these are just the most pronounced.
        </p>
      )}
      {block.suppressed_count > 0 && (
        <p className="tail">
          {block.suppressed_count} further trait{block.suppressed_count === 1 ? "" : "s"} sit
          {block.suppressed_count === 1 ? "s" : ""} within the typical range.
        </p>
      )}
      <p className="note">{block.note}</p>
    </div>
  );
}

// ── shared bits ───────────────────────────────────────────────────────────

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

"use client";

// ───────────────────────────────────────────────────────────────────────────
// /personas/crawl-setup — the v2 dark "Reading Console" reskin.
//
// FORK-AND-RESTYLE of CrawlSetupLegacy.tsx (the FROZEN source of truth for ALL
// behaviour). This file reproduces every data load, poll, state branch,
// validation, save / start-crawl mutation, error / loading branch, honesty
// disclosure, <Link> / button / onClick the legacy page has — byte-for-byte in
// LOGIC — and changes ONLY the presentation (markup + CSS classes + layout)
// into the dark Console language of design-rethink/mocks/crawl-setup.html.
//
// It renders INSIDE AppShellV2 surface="console" (the shell owns the dark rail +
// appbar). The body is scoped under a single `.rconsole` wrapper so the copied
// dark token block applies; we do NOT emit the mock's own .shell/.rail/.topbar.
//
// Structure note: the legacy renders capability NAMES (§01) and ENTRY POINTS
// (§02) as two separate sections — that exact two-section data shape is
// preserved (NOT merged into the mock's collapsible-per-capability layout),
// since the iron rule forbids re-logicking. Only presentation is dark-Console.
//
// Honesty law (DESIGN.md §8.1 / §8.6): NO fabricated fields. No spinners —
// pending is honest text. No verdict color; alert is border + word, never a
// fill. Every disclosure / status / hint copy survives verbatim.
// ───────────────────────────────────────────────────────────────────────────

import { useEffect, useState } from "react";
import {
  ApiError,
  getCapabilities,
  getCrawl,
  getCrawlSetup,
  listCrawls,
  saveCrawlSetup,
  startCrawl,
  type CrawlCadence,
  type CrawlSetupInput,
  type CrawlSummary,
  type FeaturePackManifest,
} from "@/lib/api";
import AppShellV2 from "@/components/v2/AppShellV2";

// Mirrors the backend CrawlSetup contract (schemas/crawl.py) so rejects
// surface inline instead of as a 422 wall.
const MAX_CAPABILITIES = 10;
const MAX_ENTRY_URLS = 3;
const MAX_TEST_USERS = 8;

interface CapabilityDraft {
  name: string;
  urls: string[];
}

interface TestUserDraft {
  role: string;
  username: string;
  // Write-only (#206 Slice C): collected here, encrypted at rest, never
  // returned by GET — so it loads blank and must be re-entered to re-save.
  password: string;
}

const emptyCapability = (): CapabilityDraft => ({ name: "", urls: [""] });

const isHttpUrl = (value: string) => /^https?:\/\/\S+$/i.test(value.trim());

// A capability name becomes both a URL path segment (the Library's
// /personas/capability/<name> detail route) and an artifact storage path
// segment, so it must be a slug. Mirror the backend's _CAPABILITY_SLUG_RE
// (schemas/crawl.py) here so a bad name is caught before save instead of
// bouncing back as a raw 422 after the user re-enters passwords.
const isCapabilitySlug = (value: string) => /^[A-Za-z0-9_-]+$/.test(value.trim());

function validate(
  caps: CapabilityDraft[],
  sandboxUrl: string,
  users: TestUserDraft[],
): string | null {
  if (caps.length === 0) return "Name at least one capability to crawl.";
  for (const cap of caps) {
    if (!cap.name.trim()) return "Every capability needs a name.";
    if (!isCapabilitySlug(cap.name))
      return `Capability "${cap.name.trim()}" must be a slug — letters, digits, "-" or "_" only (no spaces, slashes, or other punctuation).`;
    const urls = cap.urls.map((u) => u.trim()).filter(Boolean);
    if (urls.length === 0)
      return `Capability "${cap.name.trim()}" needs at least one entry URL.`;
    const bad = urls.find((u) => !isHttpUrl(u));
    if (bad) return `Entry URL "${bad}" must start with http:// or https://.`;
  }
  if (!isHttpUrl(sandboxUrl))
    return "The sandbox tenant URL must start with http:// or https://.";
  const filledUsers = users.filter((u) => u.role.trim() && u.username.trim());
  if (filledUsers.length === 0)
    return "Add at least one test login — role and username.";
  const missingPassword = filledUsers.find((u) => !u.password.trim());
  if (missingPassword)
    return `Enter the password for the "${missingPassword.role.trim()}" login — it is encrypted at rest and re-entered on each save.`;
  const roles = filledUsers.map((u) => u.role.trim());
  if (new Set(roles).size !== roles.length)
    return "Each role may have only one test login.";
  return null;
}

type SaveState =
  | { state: "idle" }
  | { state: "saving" }
  | { state: "saved"; at: string }
  | { state: "error"; message: string };

// GET /crawls/{id} cadence while a crawl is pending/running. The crawl takes
// ~40 min; the poll only reads status, so a slow beat is plenty.
const CRAWL_POLL_MS = 5000;

const isInFlight = (c: CrawlSummary | null): boolean =>
  c !== null && (c.status === "pending" || c.status === "running");

// Backend errors arrive as JSON {"detail": "..."} — surface the detail, not
// the raw envelope.
function apiErrorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    try {
      const detail = JSON.parse(e.body)?.detail;
      if (typeof detail === "string") return detail;
    } catch {
      /* non-JSON body — fall through */
    }
    return e.body || `HTTP ${e.status}`;
  }
  return e instanceof Error ? e.message : "request failed";
}

// Honest-text status line (§8.6) — every word is backed by backend data.
function crawlStatusLine(c: CrawlSummary): string {
  switch (c.status) {
    case "pending":
      return "PENDING — QUEUED ON GITHUB";
    case "running":
      return c.phase ? `RUNNING · ${c.phase.toUpperCase()}` : "RUNNING";
    case "complete":
      return c.snapshot_version
        ? `COMPLETE · SNAPSHOT ${c.snapshot_version} IS LATEST`
        : "COMPLETE";
    case "failed":
      return "FAILED";
  }
}

const utcStamp = (iso: string) =>
  new Date(iso).toISOString().replace("T", " · ").slice(0, 18) + " UTC";

export default function CrawlSetupV2() {
  const [caps, setCaps] = useState<CapabilityDraft[]>([emptyCapability()]);
  const [sandboxUrl, setSandboxUrl] = useState("");
  const [users, setUsers] = useState<TestUserDraft[]>([
    { role: "admin", username: "", password: "" },
    { role: "member", username: "", password: "" },
  ]);
  const [ipNote, setIpNote] = useState("");
  const [cadence, setCadence] = useState<CrawlCadence>("weekly");
  const [walkDepth, setWalkDepth] = useState(6);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [save, setSave] = useState<SaveState>({ state: "idle" });
  const [validationError, setValidationError] = useState<string | null>(null);
  const [manifest, setManifest] = useState<FeaturePackManifest | null>(null);

  // #193 fire-and-watch: the latest crawl row (in-flight or last outcome).
  const [crawl, setCrawl] = useState<CrawlSummary | null>(null);
  const [crawlStarting, setCrawlStarting] = useState(false);
  const [crawlError, setCrawlError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getCrawlSetup()
      .then((envelope) => {
        if (cancelled) return;
        if (envelope.setup) {
          const s = envelope.setup;
          setCaps(
            s.capabilities.map((c) => ({ name: c.name, urls: [...c.entry_urls] })),
          );
          setSandboxUrl(s.sandbox_url);
          // GET never returns passwords — load role+username, blank password.
          setUsers(s.test_users.map((u) => ({ ...u, password: "" })));
          setIpNote(s.ip_allowlist_note);
          setCadence(s.cadence);
          setWalkDepth(s.walk_depth);
          if (envelope.updated_at) setSave({ state: "saved", at: envelope.updated_at });
        }
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setLoadError(e?.message ?? "request failed");
        setLoading(false);
      });

    // Snapshot context for the manifest rail — absent on an empty tenant.
    getCapabilities()
      .then((m) => {
        if (!cancelled) setManifest(m);
      })
      .catch((e) => {
        if (!cancelled && !(e instanceof ApiError && e.status === 404)) {
          // Non-404 errors only affect rail context; the form still works.
          setManifest(null);
        }
      });

    // Rediscover a crawl after tab close/reopen: prefer the newest in-flight
    // row (a newer terminal row — e.g. a dispatch-failed attempt — must not
    // shadow a live crawl), fall back to the last outcome on record. Never
    // overwrite a crawl already started on this page: this response can
    // resolve after a fast POST /crawls.
    listCrawls()
      .then((rows) => {
        if (cancelled || rows.length === 0) return;
        const rediscovered = rows.find(isInFlight) ?? rows[0];
        setCrawl((current) => current ?? rediscovered);
      })
      .catch(() => {
        /* the trigger button still works without the history */
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Watch poll — runs only while the crawl is pending/running; the id is
  // stable across polls so the interval survives until a terminal status.
  const watchId = isInFlight(crawl) ? crawl!.id : null;
  useEffect(() => {
    if (!watchId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const next = await getCrawl(watchId);
        if (cancelled) return;
        setCrawl(next);
        if (next.status === "complete") {
          // The CI-side pointer flip already published — refresh the
          // manifest rail so SNAPSHOT shows what the tenant now serves.
          getCapabilities()
            .then((m) => {
              if (!cancelled) setManifest(m);
            })
            .catch(() => {});
        }
      } catch {
        // 502 = flaky GitHub poll (the backend keeps the row's last-known
        // status by design); network blips likewise — the next beat retries.
      }
    };
    const interval = setInterval(tick, CRAWL_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [watchId]);

  const handleStartCrawl = async () => {
    setCrawlError(null);
    setCrawlStarting(true);
    try {
      setCrawl(await startCrawl());
    } catch (e) {
      setCrawlError(apiErrorMessage(e));
    } finally {
      setCrawlStarting(false);
    }
  };

  const handleSave = async () => {
    const error = validate(caps, sandboxUrl, users);
    setValidationError(error);
    if (error) return;

    const payload: CrawlSetupInput = {
      capabilities: caps.map((c) => ({
        name: c.name.trim(),
        entry_urls: c.urls.map((u) => u.trim()).filter(Boolean),
      })),
      sandbox_url: sandboxUrl.trim(),
      test_users: users
        .filter((u) => u.role.trim() && u.username.trim())
        // Password is sent byte-for-byte (no trim) — surrounding whitespace can
        // be significant; only its presence is validated above.
        .map((u) => ({
          role: u.role.trim(),
          username: u.username.trim(),
          password: u.password,
        })),
      ip_allowlist_note: ipNote.trim(),
      cadence,
      walk_depth: walkDepth,
    };

    setSave({ state: "saving" });
    try {
      const envelope = await saveCrawlSetup(payload);
      setSave({ state: "saved", at: envelope.updated_at ?? "" });
    } catch (e) {
      setSave({
        state: "error",
        message: e instanceof Error ? e.message : "save failed",
      });
    }
  };

  // Capability mutators — entry URLs live with their capability.
  const setCapName = (i: number, name: string) =>
    setCaps((prev) => prev.map((c, idx) => (idx === i ? { ...c, name } : c)));
  const removeCap = (i: number) =>
    setCaps((prev) => prev.filter((_, idx) => idx !== i));
  const setCapUrl = (i: number, j: number, url: string) =>
    setCaps((prev) =>
      prev.map((c, idx) =>
        idx === i ? { ...c, urls: c.urls.map((u, k) => (k === j ? url : u)) } : c,
      ),
    );
  const addCapUrl = (i: number) =>
    setCaps((prev) =>
      prev.map((c, idx) => (idx === i ? { ...c, urls: [...c.urls, ""] } : c)),
    );
  const removeCapUrl = (i: number, j: number) =>
    setCaps((prev) =>
      prev.map((c, idx) =>
        idx === i ? { ...c, urls: c.urls.filter((_, k) => k !== j) } : c,
      ),
    );

  const setUser = (i: number, patch: Partial<TestUserDraft>) =>
    setUsers((prev) => prev.map((u, idx) => (idx === i ? { ...u, ...patch } : u)));

  const namedCaps = caps.filter((c) => c.name.trim());
  const entryUrlCount = caps.reduce(
    (n, c) => n + c.urls.filter((u) => u.trim()).length,
    0,
  );
  const roles = users.filter((u) => u.role.trim()).map((u) => u.role.trim().toUpperCase());

  // R2 #167 posture: every manifest row is a real, currently-configured value.
  const manifestRows: Array<[string, string]> = [
    ["Snapshot", manifest ? `${manifest.snapshot_version} · CURRENT` : "NONE YET — FIRST CRAWL CREATES IT"],
    ["Capabilities", String(namedCaps.length)],
    ["Entry points", String(entryUrlCount)],
    ["Roles", roles.length > 0 ? roles.join(" · ") : "—"],
    ["Cadence", cadence === "weekly" ? "WEEKLY · MON 04:00 UTC" : "ON-DEMAND ONLY"],
    ["Depth", `${walkDepth} HOPS`],
    ["Diff vs", manifest ? manifest.snapshot_version : "—"],
    ["Promote", "GATED — REVIEW DIFF FIRST"],
    ["Latest", "FLIPS ON PROMOTE"],
  ];

  return (
    <AppShellV2 activeNav="personas" title="Crawl setup" surface="console">
      <div className="rconsole">
        <style>{CS_CSS}</style>

        {/* ── page header band ──────────────────────────────────── */}
        <div className="cs-bleed top">
          <div className="cs-wrap">
            <div className="pagehead">
              <h1>Feature pack — crawl setup</h1>
              <span className="snap mono">
                {manifest ? `LIBRARY · SNAPSHOT ${manifest.snapshot_version}` : "LIBRARY · NO SNAPSHOT YET"}
              </span>
              <span className="invariant mono">
                GENERATED — NEVER AUTHORED · THE PACK IS THE CONTROL ARM
              </span>
            </div>
          </div>
        </div>

        {/* ── two-zone layout: form + audit rail ────────────────── */}
        <div className="cs-bleed">
          <div className="cs-wrap">
            <div className="layout">
              {/* ── FORM COLUMN ─────────────────────────────────── */}
              <div className="formcol">
                {loading && (
                  <div className="loadline">Loading the saved crawl setup…</div>
                )}
                {loadError && (
                  <div role="alert" className="errbanner">
                    The saved setup could not be loaded: {loadError}
                  </div>
                )}
                {(validationError || save.state === "error") && (
                  <div role="alert" className="errbanner">
                    {validationError ?? (save.state === "error" ? save.message : null)}
                  </div>
                )}

                {!loading && (
                  <div className="formbody">
                    {/* ── 01 · Capabilities ──────────────────────── */}
                    <section className="section">
                      <div className="section-head">
                        <h2>01 · Capabilities</h2>
                      </div>
                      {caps.map((cap, i) => (
                        <div key={i} className="field">
                          <label htmlFor={`cap-${i}`} className="sublabel">
                            Capability {String(i + 1).padStart(2, "0")}
                          </label>
                          <div className="row">
                            <input
                              id={`cap-${i}`}
                              className="in mono"
                              value={cap.name}
                              onChange={(e) => setCapName(i, e.target.value)}
                              placeholder="e.g. onboarding-checklist"
                            />
                            {caps.length > 1 && (
                              <RemoveButton
                                label={`Remove capability ${i + 1}`}
                                onClick={() => removeCap(i)}
                              />
                            )}
                          </div>
                        </div>
                      ))}
                      {caps.length < MAX_CAPABILITIES && (
                        <AddButton onClick={() => setCaps((prev) => [...prev, emptyCapability()])}>
                          + ADD CAPABILITY
                        </AddButton>
                      )}
                      <div className="hint">
                        5–10 priority capabilities, each named as a slug — letters,
                        digits, “-” or “_” (e.g. onboarding-checklist). The walker
                        writes a reverse PRD and reverse-Figma spec for each.
                      </div>
                    </section>

                    {/* ── 02 · Entry points ──────────────────────── */}
                    <section className="section">
                      <div className="section-head">
                        <h2>02 · Entry points</h2>
                      </div>
                      {caps.map((cap, i) => (
                        <div key={i} className="field">
                          <label className="sublabel">
                            {cap.name.trim() ? cap.name.trim() : `Capability ${String(i + 1).padStart(2, "0")}`}
                          </label>
                          {cap.urls.map((url, j) => (
                            <div key={j} className="urlrow" style={{ marginTop: j === 0 ? 0 : 8 }}>
                              <span className="url-tag mono">{String(j + 1).padStart(2, "0")}</span>
                              <input
                                className="in mono"
                                value={url}
                                onChange={(e) => setCapUrl(i, j, e.target.value)}
                                placeholder="https://staging.yourapp.dev/path"
                                aria-label={`Entry URL ${j + 1} for capability ${i + 1}`}
                              />
                              {cap.urls.length > 1 && (
                                <RemoveButton
                                  label={`Remove entry URL ${j + 1} of capability ${i + 1}`}
                                  onClick={() => removeCapUrl(i, j)}
                                />
                              )}
                            </div>
                          ))}
                          {cap.urls.length < MAX_ENTRY_URLS && (
                            <AddButton onClick={() => addCapUrl(i)}>+ ADD ENTRY URL</AddButton>
                          )}
                        </div>
                      ))}
                      <div className="hint">
                        1–3 URLs per capability. The walker authenticates, enters here,
                        and walks each flow about 3 hops deep.
                      </div>
                    </section>

                    {/* ── 03 · Access ────────────────────────────── */}
                    <section className="section">
                      <div className="section-head">
                        <h2>03 · Access</h2>
                      </div>
                      <div className="field">
                        <label htmlFor="sandbox-url" className="sublabel">
                          Sandbox tenant
                        </label>
                        <input
                          id="sandbox-url"
                          className="in mono"
                          value={sandboxUrl}
                          onChange={(e) => setSandboxUrl(e.target.value)}
                          placeholder="https://sandbox.yourapp.dev"
                        />
                        <div className="hint">
                          Staging or sandbox only — the walker never touches production
                          data.
                        </div>
                      </div>
                      {users.map((user, i) => (
                        <div key={i} className="field grid2">
                          <div>
                            <label htmlFor={`role-${i}`} className="sublabel">
                              Role
                            </label>
                            <input
                              id={`role-${i}`}
                              className="in mono"
                              value={user.role}
                              onChange={(e) => setUser(i, { role: e.target.value })}
                              placeholder="admin"
                            />
                          </div>
                          <div>
                            <label htmlFor={`username-${i}`} className="sublabel">
                              Test login
                            </label>
                            <div className="row">
                              <input
                                id={`username-${i}`}
                                className="in mono"
                                value={user.username}
                                onChange={(e) => setUser(i, { username: e.target.value })}
                                placeholder="crawler-admin@yourapp.dev"
                              />
                              {users.length > 1 && (
                                <RemoveButton
                                  label={`Remove test login ${i + 1}`}
                                  onClick={() =>
                                    setUsers((prev) => prev.filter((_, idx) => idx !== i))
                                  }
                                />
                              )}
                            </div>
                          </div>
                          <div className="field-wide">
                            <label htmlFor={`password-${i}`} className="sublabel">
                              Password
                            </label>
                            <input
                              id={`password-${i}`}
                              className="in mono"
                              type="password"
                              value={user.password}
                              onChange={(e) => setUser(i, { password: e.target.value })}
                              autoComplete="off"
                              placeholder="••••••••"
                            />
                          </div>
                        </div>
                      ))}
                      {users.length < MAX_TEST_USERS && (
                        <AddButton
                          onClick={() =>
                            setUsers((prev) => [
                              ...prev,
                              { role: "", username: "", password: "" },
                            ])
                          }
                        >
                          + ADD ROLE
                        </AddButton>
                      )}
                      <div className="field">
                        <label htmlFor="ip-note" className="sublabel">
                          IP allowlist note
                        </label>
                        <input
                          id="ip-note"
                          className="in"
                          value={ipNote}
                          onChange={(e) => setIpNote(e.target.value)}
                          placeholder="e.g. egress IPs allowlisted in Cloudflare WAF"
                        />
                        <div className="hint">
                          One test login per role — role gating is captured in the
                          reverse-Figma spec. Passwords are encrypted at rest and never
                          shown again, so re-enter them whenever you re-save. Allowlist
                          the walker&apos;s egress IPs first.
                        </div>
                      </div>
                    </section>

                    {/* ── 04 · Run ───────────────────────────────── */}
                    <section className="section">
                      <div className="section-head">
                        <h2>04 · Run</h2>
                      </div>
                      <div className="field grid2">
                        <div>
                          <label htmlFor="cadence" className="sublabel">
                            Cadence
                          </label>
                          <select
                            id="cadence"
                            className="in"
                            value={cadence}
                            onChange={(e) => setCadence(e.target.value as CrawlCadence)}
                          >
                            <option value="weekly">WEEKLY · MONDAY 04:00 UTC</option>
                            <option value="on_demand">ON-DEMAND ONLY</option>
                          </select>
                        </div>
                        <div>
                          <label htmlFor="walk-depth" className="sublabel">
                            Walk depth
                          </label>
                          <select
                            id="walk-depth"
                            className="in"
                            value={walkDepth}
                            onChange={(e) => setWalkDepth(Number(e.target.value))}
                          >
                            {[2, 3, 4, 5, 6, 7, 8].map((d) => (
                              <option key={d} value={d}>
                                {d} HOPS{d === 6 ? " · DEFAULT" : ""}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div className="hint">
                        Walk depth is how many hops from each capability&apos;s entry URL
                        the crawler explores before stopping — it caps every capability
                        alike. The default 6 sits above the deepest real flow (checkout,
                        refunds), so it&apos;s a safety ceiling, not a budget you tune
                        per crawl; raise it only if a deep flow gets truncated.
                      </div>
                      <div className="hint">
                        Each crawl produces a new versioned snapshot and a diff against
                        the prior one. Promotion to latest is gated on the diff review —
                        running sims keep their frozen slice either way.
                      </div>
                    </section>
                  </div>
                )}
              </div>

              {/* ── AUDIT RAIL — crawl manifest ──────────────────── */}
              <aside className="auditcol" aria-label="Crawl manifest and run status">
                <div className="rail-inner">
                  {/* THE MANIFEST — primary audit surface */}
                  <div className="manifest-block elevated">
                    <div className="rail-head">
                      <span className="ttl">Crawl manifest</span>
                    </div>
                    <dl className="manifest">
                      {manifestRows.map(([dt, dd]) => (
                        <div key={dt} style={{ display: "contents" }}>
                          <dt>{dt}</dt>
                          <dd>{dd}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>

                  {/* Save setup — config persists, not a live reading (ink, no lime) */}
                  <div className="rail-actions">
                    <button
                      type="button"
                      className="btn primary"
                      onClick={handleSave}
                      disabled={loading || save.state === "saving"}
                    >
                      {save.state === "saving" ? "Saving..." : "Save setup"}
                    </button>
                    {save.state === "saved" && (
                      <div className="saved-cap mono">
                        SAVED {save.at ? new Date(save.at).toISOString().replace("T", " · ").slice(0, 18) + " UTC" : ""}
                      </div>
                    )}
                  </div>

                  {/* Crawl trigger + watch (#193) */}
                  <div className="rail-watch">
                    <button
                      type="button"
                      className="btn secondary"
                      onClick={handleStartCrawl}
                      disabled={crawlStarting || isInFlight(crawl)}
                    >
                      {crawlStarting
                        ? "Dispatching..."
                        : isInFlight(crawl)
                          ? "Crawl in flight"
                          : "Start crawl"}
                    </button>
                    {crawlError && (
                      <div role="alert" className="rail-alert">
                        {crawlError}
                      </div>
                    )}
                    {crawl && (
                      <div className="watch-body">
                        <div className="w-id mono">CRAWL {crawl.id}</div>
                        <div className="w-state mono">{crawlStatusLine(crawl)}</div>
                        <div className="ts mono">DISPATCHED {utcStamp(crawl.created_at)}</div>
                        {crawl.completed_at && (
                          <div className="ts mono">SETTLED {utcStamp(crawl.completed_at)}</div>
                        )}
                        {crawl.status === "failed" && crawl.error && (
                          <div role="alert" className="rail-alert">
                            {crawl.error}
                          </div>
                        )}
                        {crawl.run_url && (
                          <a
                            className="ts link mono"
                            href={crawl.run_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            CI RUN ↗
                          </a>
                        )}
                      </div>
                    )}
                    <div className="rail-cap mono">
                      THE CRAWL RUNS IN CI (~40 MIN) AND PUBLISHES ON ITS OWN —
                      CLOSING THIS TAB CHANGES NOTHING.
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </div>
    </AppShellV2>
  );
}

// ── row furniture ───────────────────────────────────────────────────────────

function AddButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" className="btn-add mono" onClick={onClick}>
      {children}
    </button>
  );
}

function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="btn-x" aria-label={label} onClick={onClick}>
      ×
    </button>
  );
}

// ── scoped dark Console tokens + layout (palette mirrors crawl-setup.html).
//    The `.cs-bleed` helper breaks the header + layout out of the .v2-appmain
//    section padding; a centered `.cs-wrap` re-pads.
const CS_CSS = `
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
.rconsole .elevated{box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.rconsole h1,.rconsole h2{color:var(--text-hi); text-wrap:balance;}

/* full-bleed bands — negate .v2-appmain section padding */
.rconsole .cs-bleed{
  margin-left:calc(-1 * var(--space-section,48px));
  margin-right:calc(-1 * var(--space-section,48px));
}
.rconsole .cs-bleed.top{margin-top:calc(-1 * var(--space-section,48px));}
.rconsole .cs-wrap{max-width:1320px; margin:0 auto; width:100%;}

/* page header */
.rconsole .pagehead{padding:40px 40px 0; display:flex; align-items:baseline;
  gap:18px; flex-wrap:wrap;}
.rconsole .pagehead h1{font-size:2rem; font-weight:600; letter-spacing:-.025em;
  line-height:1.08; margin:0;}
.rconsole .pagehead .snap{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.07em; color:var(--text-mut);}
.rconsole .pagehead .invariant{margin-left:auto; font-size:10px;
  letter-spacing:.08em; color:var(--text-mut); border:1px solid rgba(51,64,92,.7);
  border-radius:var(--r-well); padding:3px 8px; white-space:nowrap;}

/* layout grid — manifest is the primary audit surface */
.rconsole .layout{display:grid; grid-template-columns:1fr 408px; gap:0;
  align-items:start;}
.rconsole .formcol{padding:40px 40px 96px; min-width:0;}
.rconsole .auditcol{position:sticky; top:52px; align-self:start;
  border-left:1px solid rgba(51,64,92,.5); min-height:calc(100vh - 52px);}

/* form-level state lines / banners — alert is border + word, never a fill */
.rconsole .loadline{color:var(--text-mut); font-size:14px;}
.rconsole .errbanner{margin-bottom:16px; padding:12px 16px;
  border-left:2px solid var(--alert); background:var(--console-800);
  border-radius:var(--r-well); color:var(--text); font-size:14px;
  line-height:1.5; max-width:620px;}
.rconsole .formbody{max-width:620px;}

/* sections / form */
.rconsole .section{margin-top:48px;}
.rconsole .section:first-of-type{margin-top:0;}
.rconsole .section-head{display:flex; align-items:baseline; gap:12px;
  padding-bottom:10px; border-bottom:1px solid rgba(51,64,92,.5); margin-bottom:24px;}
.rconsole .section-head h2{font-size:1.0rem; font-weight:550; letter-spacing:.06em;
  text-transform:uppercase; color:var(--text-mut);}
.rconsole .field{margin-top:24px;}
.rconsole .field:first-of-type{margin-top:0;}
.rconsole .sublabel{display:block; font-family:var(--font-mono); font-size:11px;
  font-weight:500; letter-spacing:.08em; text-transform:uppercase;
  color:var(--text-mut); margin-bottom:8px;}
.rconsole .row{display:flex; gap:8px;}
.rconsole .grid2{display:grid; grid-template-columns:1fr 1fr; gap:16px;}
.rconsole .field-wide{grid-column:1 / -1;}
.rconsole input.in,.rconsole select.in{width:100%; height:36px;
  background:var(--console-700); border:1px solid rgba(51,64,92,.7);
  border-radius:var(--r-well); color:var(--text-hi); padding:0 12px; font-size:14px;
  font-family:var(--font-sans); outline:none;
  transition:border-color .14s,box-shadow .14s;}
.rconsole input.in::placeholder{color:var(--text-mut); opacity:.7;}
.rconsole input.in.mono,.rconsole select.in{font-family:var(--font-mono); font-size:13px;}
.rconsole input.in:focus,.rconsole select.in:focus{border-color:var(--signal-dim);
  box-shadow:0 0 0 2px rgba(57,184,148,.35);}
.rconsole select.in{appearance:none; -webkit-appearance:none; cursor:pointer;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' fill='none'><path d='M4 6l4 4 4-4' stroke='%23929BAE' stroke-width='1.3' stroke-linecap='round' stroke-linejoin='round'/></svg>");
  background-repeat:no-repeat; background-position:right 10px center; padding-right:32px;}
.rconsole .hint{font-size:13px; color:var(--text-mut); margin-top:10px;
  line-height:1.55; max-width:62ch;}

.rconsole .urlrow{display:flex; gap:8px;}
.rconsole .url-tag{flex-shrink:0; width:36px; height:36px; display:grid;
  place-items:center; font-size:11px; color:var(--text-mut);
  border:1px solid rgba(51,64,92,.4); border-radius:var(--r-well);
  background:var(--console-800);}

.rconsole .btn-x{flex-shrink:0; width:36px; height:36px; background:transparent;
  border:1px solid rgba(51,64,92,.7); border-radius:var(--r-well);
  color:var(--text-mut); font-size:16px; line-height:1; cursor:pointer;
  transition:color .14s,border-color .14s;}
.rconsole .btn-x:hover{color:var(--text-hi); border-color:var(--alert);}
.rconsole .btn-add{margin-top:12px; background:transparent;
  border:1px solid rgba(51,64,92,.7); border-radius:var(--r-well); padding:7px 12px;
  font-size:11px; letter-spacing:.05em; color:var(--text-mut); cursor:pointer;
  transition:color .14s,background .14s;}
.rconsole .btn-add:hover{color:var(--text-hi); background:var(--console-800);}

/* audit rail */
.rconsole .rail-inner{display:flex; flex-direction:column;}
.rconsole .manifest-block{background:var(--console-800);}
.rconsole .rail-head{padding:18px 24px 12px; display:flex; align-items:baseline;
  justify-content:space-between; gap:10px;}
.rconsole .rail-head .ttl{font-size:1.0rem; font-weight:500; letter-spacing:.06em;
  text-transform:uppercase; color:var(--text-mut);}
.rconsole .manifest{padding:2px 24px 18px; display:grid;
  grid-template-columns:auto 1fr; gap:0 18px; align-content:start; margin:0;}
.rconsole .manifest dt,.rconsole .manifest dd{padding:8px 0;
  border-top:1px solid rgba(51,64,92,.4); align-self:center;}
.rconsole .manifest dt:first-of-type,.rconsole .manifest dd:first-of-type{border-top:none;}
.rconsole .manifest dt{font-family:var(--font-mono); font-size:11px;
  letter-spacing:.06em; text-transform:uppercase; color:var(--text-mut);}
.rconsole .manifest dd{margin:0; font-family:var(--font-mono); font-size:13px;
  font-weight:500; color:var(--text-hi); overflow-wrap:break-word; min-width:0;
  text-align:right;}

.rconsole .rail-actions{padding:18px 24px; border-top:1px solid rgba(51,64,92,.5);
  display:flex; flex-direction:column; gap:12px;}
.rconsole .rail-watch{padding:18px 24px; border-top:1px solid rgba(51,64,92,.5);
  display:flex; flex-direction:column; gap:12px;}
.rconsole .btn{height:36px; border-radius:var(--r-well); font-weight:500;
  font-size:14px; font-family:var(--font-sans); display:inline-flex;
  align-items:center; justify-content:center; gap:8px; cursor:pointer;
  border:1px solid transparent; transition:background .14s,border-color .14s;}
.rconsole .btn:disabled{opacity:.5; cursor:not-allowed;}
.rconsole .btn.primary{background:var(--console-700); border-color:rgba(51,64,92,.9);
  color:var(--text-hi); box-shadow:inset 0 1px 0 rgba(255,255,255,.05);}
.rconsole .btn.primary:hover:not(:disabled){background:var(--console-750);}
.rconsole .btn.secondary{background:transparent; border-color:rgba(51,64,92,.9);
  color:var(--text-hi);}
.rconsole .btn.secondary:hover:not(:disabled){background:var(--console-800);}
.rconsole .saved-cap{font-size:11px; letter-spacing:.04em; color:var(--text-mut);}

.rconsole .watch-body{display:flex; flex-direction:column; gap:3px;}
.rconsole .w-id{font-size:11px; letter-spacing:.04em; color:var(--text-mut);}
.rconsole .w-state{font-size:12px; letter-spacing:.03em; color:var(--text-hi);}
.rconsole .ts{font-size:11px; letter-spacing:.03em; color:var(--text-mut);}
.rconsole a.ts.link{color:var(--text);}
.rconsole a.ts.link:hover{color:var(--text-hi);}
.rconsole .rail-cap{font-size:11px; letter-spacing:.03em; line-height:1.55;
  color:var(--text-mut);}
.rconsole .rail-alert{padding:8px 10px; border-left:2px solid var(--alert);
  background:var(--console-800); border-radius:var(--r-well); color:var(--text);
  font-size:12px; line-height:1.45; overflow-wrap:break-word;}

.rconsole a:focus-visible,.rconsole button:focus-visible,
.rconsole input:focus-visible,.rconsole select:focus-visible{
  outline:2px solid var(--signal-dim); outline-offset:2px;}

@media (max-width:1080px){
  .rconsole .layout{grid-template-columns:1fr;}
  .rconsole .auditcol{position:static; border-left:none;
    border-top:1px solid rgba(51,64,92,.5); min-height:0;}
  .rconsole .grid2{grid-template-columns:1fr;}
}
@media (max-width:1024px){
  .rconsole .cs-bleed{
    margin-left:calc(-1 * var(--space-room,24px));
    margin-right:calc(-1 * var(--space-room,24px));
  }
  .rconsole .cs-bleed.top{margin-top:calc(-1 * var(--space-room,24px));}
  .rconsole .pagehead{padding:24px 24px 0;}
  .rconsole .formcol{padding:24px 24px 64px;}
}
@media (prefers-reduced-motion:reduce){.rconsole *{animation:none!important;}}
`;

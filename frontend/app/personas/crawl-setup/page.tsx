"use client";

// Feature pack — crawl setup + re-crawl window (#171), fire-and-watch
// trigger (#193).
//
// "Save setup" PUTs /crawl-setup; "Start crawl" POSTs /crawls, which
// dispatches the walker in sidira-crawler CI and returns immediately. The
// browser is never load-bearing — the workflow itself publishes the pack by
// flipping the latest pointer; this page only watches via GET /crawls/{id}.
// Pending states are honest text, never spinners (DESIGN.md §8.6).
//
// Invariant (#171): the pack is GENERATED — NEVER AUTHORED. This window
// configures WHAT the walker crawls (capability names, entry URLs, sandbox
// logins); it never reads or edits reverse-PRD / reverse-Figma content.

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
import { TOKENS, FONT_SANS, FONT_MONO, TNUM } from "@/lib/design";

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

function validate(
  caps: CapabilityDraft[],
  sandboxUrl: string,
  users: TestUserDraft[],
): string | null {
  if (caps.length === 0) return "Name at least one capability to crawl.";
  for (const cap of caps) {
    if (!cap.name.trim()) return "Every capability needs a name.";
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

export default function CrawlSetupPage() {
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
    <main style={{ fontFamily: FONT_SANS, color: TOKENS.ink }}>
      {/* Page strip — same zone grammar as the wizard (DESIGN.md §7) */}
      <header
        style={{
          padding: "20px 24px 16px",
          borderBottom: `0.75px solid ${TOKENS.rule}`,
          display: "flex",
          alignItems: "baseline",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" }}>
          Feature pack — crawl setup
        </h1>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: TOKENS.inkMuted,
            letterSpacing: "0.06em",
            ...TNUM,
          }}
        >
          {manifest ? `LIBRARY · SNAPSHOT ${manifest.snapshot_version}` : "LIBRARY · NO SNAPSHOT YET"}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontFamily: FONT_MONO,
            fontSize: 10,
            letterSpacing: "0.08em",
            color: TOKENS.inkMuted,
            border: `0.75px solid ${TOKENS.rule}`,
            borderRadius: 2,
            padding: "3px 8px",
            whiteSpace: "nowrap",
          }}
        >
          GENERATED — NEVER AUTHORED · THE PACK IS THE CONTROL ARM
        </span>
      </header>

      {/* Two-zone panel: setup form + crawl-manifest inspector rail */}
      <div style={{ display: "flex", alignItems: "stretch" }}>
        <div style={{ flex: 1, minWidth: 0, padding: 24 }}>
          {loading && (
            <div style={{ color: TOKENS.inkMuted, fontSize: 14 }}>
              Loading the saved crawl setup…
            </div>
          )}
          {loadError && (
            <div role="alert" style={errorBannerStyle}>
              The saved setup could not be loaded: {loadError}
            </div>
          )}
          {(validationError || save.state === "error") && (
            <div role="alert" style={errorBannerStyle}>
              {validationError ?? (save.state === "error" ? save.message : null)}
            </div>
          )}

          {!loading && (
            <div style={{ maxWidth: 620 }}>
              {/* ── 01 · Capabilities ───────────────────────── */}
              <section>
                <div style={sectionLabelStyle}>01 · Capabilities</div>
                {caps.map((cap, i) => (
                  <div key={i} style={fieldStyle}>
                    <label htmlFor={`cap-${i}`} style={sublabelStyle}>
                      Capability {String(i + 1).padStart(2, "0")}
                    </label>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        id={`cap-${i}`}
                        value={cap.name}
                        onChange={(e) => setCapName(i, e.target.value)}
                        placeholder="e.g. onboarding-checklist"
                        style={{ ...inputStyle, fontFamily: FONT_MONO, fontSize: 13 }}
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
                <div style={hintStyle}>
                  5–10 priority capabilities by name — the walker writes a reverse
                  PRD and reverse-Figma spec for each.
                </div>
              </section>

              {/* ── 02 · Entry points ───────────────────────── */}
              <section style={sectionStyle}>
                <div style={sectionLabelStyle}>02 · Entry points</div>
                {caps.map((cap, i) => (
                  <div key={i} style={fieldStyle}>
                    <label style={sublabelStyle}>
                      {cap.name.trim() ? cap.name.trim() : `Capability ${String(i + 1).padStart(2, "0")}`}
                    </label>
                    {cap.urls.map((url, j) => (
                      <div key={j} style={{ display: "flex", gap: 8, marginTop: j === 0 ? 0 : 8 }}>
                        <input
                          value={url}
                          onChange={(e) => setCapUrl(i, j, e.target.value)}
                          placeholder="https://staging.yourapp.dev/path"
                          style={{ ...inputStyle, fontFamily: FONT_MONO, fontSize: 13 }}
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
                <div style={hintStyle}>
                  1–3 URLs per capability. The walker authenticates, enters here,
                  and walks each flow about 3 hops deep.
                </div>
              </section>

              {/* ── 03 · Access ─────────────────────────────── */}
              <section style={sectionStyle}>
                <div style={sectionLabelStyle}>03 · Access</div>
                <div style={fieldStyle}>
                  <label htmlFor="sandbox-url" style={sublabelStyle}>
                    Sandbox tenant
                  </label>
                  <input
                    id="sandbox-url"
                    value={sandboxUrl}
                    onChange={(e) => setSandboxUrl(e.target.value)}
                    placeholder="https://sandbox.yourapp.dev"
                    style={{ ...inputStyle, fontFamily: FONT_MONO, fontSize: 13 }}
                  />
                  <div style={hintStyle}>
                    Staging or sandbox only — the walker never touches production
                    data.
                  </div>
                </div>
                {users.map((user, i) => (
                  <div key={i} style={{ ...fieldStyle, ...fieldRowStyle }}>
                    <div>
                      <label htmlFor={`role-${i}`} style={sublabelStyle}>
                        Role
                      </label>
                      <input
                        id={`role-${i}`}
                        value={user.role}
                        onChange={(e) => setUser(i, { role: e.target.value })}
                        placeholder="admin"
                        style={{ ...inputStyle, fontFamily: FONT_MONO, fontSize: 13 }}
                      />
                    </div>
                    <div>
                      <label htmlFor={`username-${i}`} style={sublabelStyle}>
                        Test login
                      </label>
                      <div style={{ display: "flex", gap: 8 }}>
                        <input
                          id={`username-${i}`}
                          value={user.username}
                          onChange={(e) => setUser(i, { username: e.target.value })}
                          placeholder="crawler-admin@yourapp.dev"
                          style={{ ...inputStyle, fontFamily: FONT_MONO, fontSize: 13 }}
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
                    <div style={{ gridColumn: "1 / -1" }}>
                      <label htmlFor={`password-${i}`} style={sublabelStyle}>
                        Password
                      </label>
                      <input
                        id={`password-${i}`}
                        type="password"
                        value={user.password}
                        onChange={(e) => setUser(i, { password: e.target.value })}
                        autoComplete="off"
                        placeholder="••••••••"
                        style={{ ...inputStyle, fontFamily: FONT_MONO, fontSize: 13 }}
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
                <div style={fieldStyle}>
                  <label htmlFor="ip-note" style={sublabelStyle}>
                    IP allowlist note
                  </label>
                  <input
                    id="ip-note"
                    value={ipNote}
                    onChange={(e) => setIpNote(e.target.value)}
                    placeholder="e.g. egress IPs allowlisted in Cloudflare WAF"
                    style={inputStyle}
                  />
                  <div style={hintStyle}>
                    One test login per role — role gating is captured in the
                    reverse-Figma spec. Passwords are encrypted at rest and never
                    shown again, so re-enter them whenever you re-save. Allowlist
                    the walker&apos;s egress IPs first.
                  </div>
                </div>
              </section>

              {/* ── 04 · Run ────────────────────────────────── */}
              <section style={sectionStyle}>
                <div style={sectionLabelStyle}>04 · Run</div>
                <div style={{ ...fieldStyle, ...fieldRowStyle }}>
                  <div>
                    <label htmlFor="cadence" style={sublabelStyle}>
                      Cadence
                    </label>
                    <select
                      id="cadence"
                      value={cadence}
                      onChange={(e) => setCadence(e.target.value as CrawlCadence)}
                      style={selectStyle}
                    >
                      <option value="weekly">WEEKLY · MONDAY 04:00 UTC</option>
                      <option value="on_demand">ON-DEMAND ONLY</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="walk-depth" style={sublabelStyle}>
                      Walk depth
                    </label>
                    <select
                      id="walk-depth"
                      value={walkDepth}
                      onChange={(e) => setWalkDepth(Number(e.target.value))}
                      style={selectStyle}
                    >
                      {[2, 3, 4, 5, 6, 7, 8].map((d) => (
                        <option key={d} value={d}>
                          {d} HOPS{d === 6 ? " · DEFAULT" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div style={hintStyle}>
                  Walk depth is how many hops from each capability&apos;s entry URL
                  the crawler explores before stopping — it caps every capability
                  alike. The default 6 sits above the deepest real flow (checkout,
                  refunds), so it&apos;s a safety ceiling, not a budget you tune
                  per crawl; raise it only if a deep flow gets truncated.
                </div>
                <div style={hintStyle}>
                  Each crawl produces a new versioned snapshot and a diff against
                  the prior one. Promotion to latest is gated on the diff review —
                  running sims keep their frozen slice either way.
                </div>
              </section>
            </div>
          )}
        </div>

        {/* ── Crawl manifest — inspector rail ──────────────── */}
        <aside
          style={{
            width: 340,
            flexShrink: 0,
            borderLeft: `0.75px solid ${TOKENS.rule}`,
            background: TOKENS.paperElevated,
            boxShadow: "inset 1px 1px 0 rgba(255, 255, 255, 0.55)",
          }}
        >
          <div style={{ position: "sticky", top: 0, display: "flex", flexDirection: "column" }}>
            <div
              style={{
                padding: "16px 20px 12px",
                borderBottom: `0.75px solid ${TOKENS.rule}`,
              }}
            >
              <span style={{ ...sectionLabelStyle, border: "none", paddingBottom: 0 }}>
                Crawl manifest
              </span>
            </div>
            <dl
              style={{
                margin: 0,
                padding: "14px 20px 16px",
                display: "grid",
                gridTemplateColumns: "auto 1fr",
                gap: "3px 16px",
                alignContent: "start",
              }}
            >
              {manifestRows.map(([dt, dd]) => (
                <div key={dt} style={{ display: "contents" }}>
                  <dt
                    style={{
                      fontSize: 11,
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      color: TOKENS.inkMuted,
                      paddingTop: 1,
                    }}
                  >
                    {dt}
                  </dt>
                  <dd
                    style={{
                      margin: 0,
                      fontFamily: FONT_MONO,
                      fontSize: 12,
                      color: TOKENS.ink,
                      minWidth: 0,
                      overflowWrap: "break-word",
                      ...TNUM,
                    }}
                  >
                    {dd}
                  </dd>
                </div>
              ))}
            </dl>
            <div
              style={{
                padding: "16px 20px",
                borderTop: `0.75px solid ${TOKENS.rule}`,
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <button
                type="button"
                onClick={handleSave}
                disabled={loading || save.state === "saving"}
                style={{
                  ...primaryBtnStyle,
                  opacity: loading || save.state === "saving" ? 0.5 : 1,
                  cursor: loading || save.state === "saving" ? "not-allowed" : "pointer",
                }}
              >
                {save.state === "saving" ? "Saving..." : "Save setup"}
              </button>
              {save.state === "saved" && (
                <div style={railCaptionStyle}>
                  SAVED {save.at ? new Date(save.at).toISOString().replace("T", " · ").slice(0, 18) + " UTC" : ""}
                </div>
              )}
            </div>

            {/* ── Crawl trigger + watch (#193) ─────────────── */}
            <div
              style={{
                padding: "16px 20px",
                borderTop: `0.75px solid ${TOKENS.rule}`,
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <button
                type="button"
                onClick={handleStartCrawl}
                disabled={crawlStarting || isInFlight(crawl)}
                style={{
                  ...secondaryBtnStyle,
                  opacity: crawlStarting || isInFlight(crawl) ? 0.5 : 1,
                  cursor:
                    crawlStarting || isInFlight(crawl) ? "not-allowed" : "pointer",
                }}
              >
                {crawlStarting
                  ? "Dispatching..."
                  : isInFlight(crawl)
                    ? "Crawl in flight"
                    : "Start crawl"}
              </button>
              {crawlError && (
                <div role="alert" style={railAlertStyle}>
                  {crawlError}
                </div>
              )}
              {crawl && (
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  <div style={railCaptionStyle}>CRAWL {crawl.id}</div>
                  <div style={{ ...railCaptionStyle, color: TOKENS.ink }}>
                    {crawlStatusLine(crawl)}
                  </div>
                  <div style={railCaptionStyle}>
                    DISPATCHED {utcStamp(crawl.created_at)}
                  </div>
                  {crawl.completed_at && (
                    <div style={railCaptionStyle}>
                      SETTLED {utcStamp(crawl.completed_at)}
                    </div>
                  )}
                  {crawl.status === "failed" && crawl.error && (
                    <div role="alert" style={railAlertStyle}>
                      {crawl.error}
                    </div>
                  )}
                  {crawl.run_url && (
                    <a
                      href={crawl.run_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ ...railCaptionStyle, color: TOKENS.ink, textDecoration: "none" }}
                    >
                      CI RUN ↗
                    </a>
                  )}
                </div>
              )}
              <div style={railCaptionStyle}>
                THE CRAWL RUNS IN CI (~40 MIN) AND PUBLISHES ON ITS OWN —
                CLOSING THIS TAB CHANGES NOTHING.
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}

// ── row furniture ───────────────────────────────────────────────────────

function AddButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
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

function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
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

// ── shared styles — instrument posture (DESIGN.md §7.4), mirrors the
// wizard's vocabulary ────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
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

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  fontFamily: FONT_MONO,
  fontSize: 13,
};

const sectionStyle: React.CSSProperties = {
  marginTop: 28,
};

const sectionLabelStyle: React.CSSProperties = {
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

const sublabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: TOKENS.inkMuted,
  marginBottom: 6,
};

const hintStyle: React.CSSProperties = {
  fontSize: 12,
  color: TOKENS.inkMuted,
  marginTop: 6,
  lineHeight: 1.45,
  maxWidth: "52ch",
};

const fieldStyle: React.CSSProperties = {
  marginTop: 16,
};

const fieldRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 16,
};

const primaryBtnStyle: React.CSSProperties = {
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

const secondaryBtnStyle: React.CSSProperties = {
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

const railAlertStyle: React.CSSProperties = {
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

const railCaptionStyle: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  color: TOKENS.inkMuted,
  letterSpacing: "0.04em",
  lineHeight: 1.5,
  ...TNUM,
};

const errorBannerStyle: React.CSSProperties = {
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

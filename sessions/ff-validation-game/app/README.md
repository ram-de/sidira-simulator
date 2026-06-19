# Moved → `ram-de/sidira-ff-game`

The **Split The Loot** friends-&-family validation game app (Vite/React SPA +
Express + SQLite) was **extracted into its own repo on 2026-06-18**:

> **https://github.com/ram-de/sidira-ff-game**

It now lives at that repo's **root** (so `package.json` / `server/` / `deploy/`
sit at the top level — a clean systemd `WorkingDirectory` with no subdir symlink).
Fresh git history; full provenance is in this repo's PR history.

## What stayed here (sidira-simulator)

- **Design + research docs** — `../DESIGN_DECISIONS.md`,
  `../INDIA_CHENNAI_RECRUITMENT.md`, `../context.md`, and the authoritative spec
  `../../agent-behavior-spec/ff-app-design/FF_GAME_DESIGN.md`.
- **The offline validation harness** — `../harness/` (`predict.py` → seal
  `PREREG_FF.json`, `score.py`, the synthetic machinery test). The harness is
  self-contained: it carries its own audited `obvious_priors.json` /
  `obvious_priors_AUDIT.md` and references nothing under the (now-moved) app.
- **The persona pack the harness runs against** —
  `../../../backend/sidira_simulator/adapters/friends_family_panel_v1.json`
  (and its loader). The pack is currently labeled `synthetic` and the harness
  refuses to seal a real run against it without `--allow-synthetic`.

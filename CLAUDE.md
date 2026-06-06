<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **sidira-simulator** (4282 symbols, 7467 relationships, 154 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/sidira-simulator/context` | Codebase overview, check index freshness |
| `gitnexus://repo/sidira-simulator/clusters` | All functional areas |
| `gitnexus://repo/sidira-simulator/processes` | All execution flows |
| `gitnexus://repo/sidira-simulator/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## Worktree Rule

All PR and feature branch work MUST be done through an isolated worktree.

### Always Do

- **MUST call `EnterWorktree` before starting any branch or PR work.** Never edit code on a named branch in the main checkout — always get a fresh worktree first.
- After the PR is merged (or abandoned), call `ExitWorktree` to clean up.
- The only exception is session file commits (`/pythia-session save`) — those are committed directly on `main` via the branch-hop dance, never through a worktree.

### Never Do

- NEVER make code edits on a feature branch in the main checkout.
- NEVER commit code changes (non-session) directly to `main`.

### Why

Worktrees give each PR an isolated filesystem, preventing stale state, accidental cross-contamination between branches, and the "wrong branch" class of errors. The `bgIsolation: worktree` setting in `.claude/settings.json` enforces this for background agents automatically; the rule above extends it to foreground sessions.

## Design System

`DESIGN.md` at the repo root is the canonical source of truth for every
visual, UI, and brand decision. Read it before:

- Adding or editing any UI component.
- Touching colors, typography, spacing, radius, or motion in CSS / Tailwind.
- Creating a new SVG, image, or marketing surface.
- Building a new page or screen.
- Reviewing a PR that touches `frontend/` for visual correctness.

The mark, the wordmark, and the lockup files live in
`frontend/public/brand/` and `frontend/app/icon.svg`. Reuse them; do not
recreate them. The dual-color "founder-mode" variants are reserved for the
cofounder / about / press / anniversary surfaces and the in-product
aperture-close animation only — never for the favicon, nav, or dashboard.

When QAing or reviewing UI changes, flag any code that violates DESIGN.md
(refuse list in §10) or that deviates from the locked specs without an
accompanying DESIGN.md update in the same PR. The design system and the code
that consumes it stay in lockstep.

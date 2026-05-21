#!/usr/bin/env python3
"""
Project-scoped session state management for Pythia (cross-repo, shared between founders via git).

Sessions live at <repo>/sessions/<domain>/context.md and are committed alongside code,
so both founders see each other's working state on `git pull`.

Usage:
  session_state.py list              — list all sessions with status
  session_state.py active            — print name of single active session (exit 0=one, 1=none, 2=multiple)
  session_state.py read <domain>     — print session file content
  session_state.py status <domain>   — print just the status line
"""
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    """Resolve the git repo toplevel for the current working directory."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return Path(out)
    except subprocess.CalledProcessError:
        print("Not inside a git repo. /session must be invoked from within a Pythia repo.", file=sys.stderr)
        sys.exit(2)


VAULT_PATH = repo_root() / "sessions"


def get_session_file(domain: str) -> Path:
    return VAULT_PATH / domain / "context.md"


def parse_frontmatter(content: str) -> dict:
    meta = {}
    if not content.startswith("---"):
        return meta
    lines = content.split("\n")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta


def cmd_list():
    if not VAULT_PATH.exists():
        print("No sessions found.")
        return
    sessions = []
    for d in sorted(VAULT_PATH.iterdir()):
        if not d.is_dir():
            continue
        ctx = d / "context.md"
        if not ctx.exists():
            continue
        meta = parse_frontmatter(ctx.read_text())
        status = meta.get("status", "unknown")
        description = ""
        for line in ctx.read_text().split("\n"):
            if line.startswith("# Session:"):
                description = line.replace("# Session:", "").strip()
                break
        sessions.append((d.name, status, description))

    if not sessions:
        print("No sessions found.")
        return

    active = [(n, s, d) for n, s, d in sessions if s == "active"]
    closed = [(n, s, d) for n, s, d in sessions if s != "active"]

    if active:
        print("ACTIVE:")
        for name, _, desc in active:
            print(f"  {name:<25} {desc}")
    if closed:
        print("CLOSED:")
        for name, status, desc in closed:
            print(f"  {name:<25} [{status}] {desc}")


def cmd_active():
    if not VAULT_PATH.exists():
        sys.exit(1)
    active = []
    for d in VAULT_PATH.iterdir():
        if not d.is_dir():
            continue
        ctx = d / "context.md"
        if not ctx.exists():
            continue
        meta = parse_frontmatter(ctx.read_text())
        if meta.get("status") == "active":
            active.append(d.name)
    if len(active) == 0:
        sys.exit(1)
    elif len(active) == 1:
        print(active[0])
        sys.exit(0)
    else:
        for name in active:
            print(name)
        sys.exit(2)


def cmd_read(domain: str):
    f = get_session_file(domain)
    if not f.exists():
        print(f"No session found: {domain}", file=sys.stderr)
        sys.exit(1)
    print(f.read_text())


def cmd_status(domain: str):
    f = get_session_file(domain)
    if not f.exists():
        print("none")
        sys.exit(1)
    meta = parse_frontmatter(f.read_text())
    print(meta.get("status", "unknown"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list()
    elif cmd == "active":
        cmd_active()
    elif cmd == "read" and len(sys.argv) >= 3:
        cmd_read(sys.argv[2])
    elif cmd == "status" and len(sys.argv) >= 3:
        cmd_status(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)

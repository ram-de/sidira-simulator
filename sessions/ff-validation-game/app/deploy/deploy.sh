#!/usr/bin/env bash
# ============================================================================
# deploy.sh — build + (re)deploy ff-validation-game on the EC2 host.
# ----------------------------------------------------------------------------
# Run ON the EC2 box (Amazon Linux 2023, arm64). It pulls the latest code into
# the deploy dir, installs prod deps, builds the SPA, and restarts the systemd
# service (which triggers the graceful WAL-checkpoint shutdown of the old PID).
#
# First-time host setup (EBS mount, user, Node, systemd unit, CloudFront, TLS)
# is documented in DEPLOY.md — this script is the steady-state redeploy.
#
#   sudo ./deploy.sh                 # pull + build + restart from origin/main
#   sudo ./deploy.sh --no-pull       # build + restart current working tree
# ============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ff-validation-game}"
SERVICE="${SERVICE:-ff-validation-game}"
DATA_DIR="${DATA_DIR:-/data}"
GIT_REF="${GIT_REF:-origin/main}"
PULL=1

for arg in "$@"; do
  case "$arg" in
    --no-pull) PULL=0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

echo "==> Deploying $SERVICE from $APP_DIR"

# The SQLite dir must exist and be writable by the service user before we start.
if [ ! -d "$DATA_DIR" ]; then
  echo "ERROR: $DATA_DIR does not exist — mount the EBS volume first (see DEPLOY.md)." >&2
  exit 1
fi

cd "$APP_DIR"

if [ "$PULL" -eq 1 ]; then
  echo "==> Fetching $GIT_REF"
  git fetch --all --prune
  git reset --hard "$GIT_REF"
fi

# The app lives in a subdir of the repo; cd into it for build.
cd "$APP_DIR/sessions/ff-validation-game/app" 2>/dev/null || cd "$APP_DIR"

echo "==> Installing dependencies (incl. dev — vite is needed for the build)"
npm ci

echo "==> Building SPA (dist/)"
npm run build

echo "==> Type-check / lint"
npm run lint

echo "==> Restarting service (graceful SIGTERM → WAL checkpoint on old PID)"
systemctl restart "$SERVICE"

echo "==> Waiting for healthcheck…"
for i in $(seq 1 15); do
  if curl -fsS "http://127.0.0.1:${PORT:-5180}/healthz" >/dev/null; then
    echo "==> Healthy. Deploy complete."
    exit 0
  fi
  sleep 1
done

echo "ERROR: healthcheck did not pass within 15s — check: journalctl -u $SERVICE -n 50" >&2
exit 1

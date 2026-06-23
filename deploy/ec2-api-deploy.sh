#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${SIDIRA_REPO_DIR:-/opt/sidira/repo}"
DEPLOY_BRANCH="${SIDIRA_DEPLOY_BRANCH:-main}"
AWS_REGION="${AWS_REGION:-us-east-1}"
PARAM_PREFIX="${SIDIRA_PARAM_PREFIX:-/sidira/prod}"
ENV_FILE="${SIDIRA_API_ENV_FILE:-/opt/sidira/api.env}"
COMPOSE_ENV_FILE="${SIDIRA_COMPOSE_ENV_FILE:-${ENV_FILE}.compose}"
LOCAL_CRED_KEY_FILE="${SIDIRA_LOCAL_CRED_KEY_FILE:-/opt/sidira/local_cred_key}"
DEPLOY_KEY="${SIDIRA_DEPLOY_KEY:-/root/.ssh/sidira_deploy}"
CONTAINER_UID="${SIDIRA_CONTAINER_UID:-10001}"
CONTAINER_GID="${SIDIRA_CONTAINER_GID:-10001}"

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required on the EC2 instance to read ${PARAM_PREFIX} parameters" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required on the EC2 instance" >&2
  exit 1
fi

ssm_value() {
  local name="$1"
  local output
  local rc

  set +e
  output="$(aws ssm get-parameter \
    --region "$AWS_REGION" \
    --name "${PARAM_PREFIX}/${name}" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text 2>&1)"
  rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    printf '%s' "$output"
    return 0
  fi
  if [[ "$output" == *"ParameterNotFound"* ]]; then
    return 0
  fi

  echo "failed to read ${PARAM_PREFIX}/${name}: ${output}" >&2
  return "$rc"
}

sanitize_value() {
  printf '%s' "$1" | tr -d '\r\n'
}

write_env() {
  local key="$1"
  local value="$2"
  if [[ -n "$value" && "$value" != "None" ]]; then
    local raw_value
    local compose_value
    raw_value="$(sanitize_value "$value")"
    compose_value="${raw_value//\$/\$\$}"
    printf '%s=%s\n' "$key" "$raw_value" >> "$ENV_FILE"
    printf '%s=%s\n' "$key" "$compose_value" >> "$COMPOSE_ENV_FILE"
  fi
}

default_value() {
  local value="$1"
  local fallback="$2"
  if [[ -z "$value" || "$value" == "None" ]]; then
    printf '%s' "$fallback"
  else
    printf '%s' "$value"
  fi
}

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "repo not found at ${REPO_DIR}; clone sidira-simulator there first" >&2
  exit 1
fi

if [[ -f "$DEPLOY_KEY" ]]; then
  export GIT_SSH_COMMAND="ssh -i ${DEPLOY_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
fi

cd "$REPO_DIR"
git fetch origin "$DEPLOY_BRANCH"
git checkout -B "$DEPLOY_BRANCH" FETCH_HEAD

install -d -m 700 "$(dirname "$ENV_FILE")"
install -d -m 700 "$(dirname "$COMPOSE_ENV_FILE")"
umask 077
: > "$ENV_FILE"
: > "$COMPOSE_ENV_FILE"

customer_id="$(ssm_value SIDIRA_CUSTOMER_ID)"
cors_origins="$(ssm_value SIDIRA_CORS_ORIGINS)"
max_agents="$(ssm_value SIDIRA_MAX_AGENTS)"
cred_mode="$(ssm_value SIDIRA_CRED_MODE)"
local_artifacts="$(ssm_value SIDIRA_LOCAL_ARTIFACTS)"
local_cred_key="$(ssm_value SIDIRA_LOCAL_CRED_KEY)"
internal_api_key="$(ssm_value SIDIRA_INTERNAL_API_KEY)"
clerk_secret_key="$(ssm_value SIDIRA_CLERK_SECRET_KEY)"
clerk_authorized_parties="$(ssm_value SIDIRA_CLERK_AUTHORIZED_PARTIES)"
clerk_webhook_secret="$(ssm_value SIDIRA_CLERK_WEBHOOK_SECRET)"
web_proxy_basic_auth_user="$(ssm_value SIDIRA_WEB_PROXY_BASIC_AUTH_USER)"
web_proxy_basic_auth_hash="$(ssm_value SIDIRA_WEB_PROXY_BASIC_AUTH_HASH)"
database_url="$(ssm_value DATABASE_URL)"
auto_migrate="$(ssm_value SIDIRA_AUTO_MIGRATE)"
persona_build_mode="$(ssm_value SIDIRA_PERSONA_BUILD_MODE)"

if [[ -z "$internal_api_key" || "$internal_api_key" == "None" ]]; then
  echo "missing required ${PARAM_PREFIX}/SIDIRA_INTERNAL_API_KEY; create a SecureString for the backend gateway token" >&2
  exit 1
fi

if [[ -z "$web_proxy_basic_auth_user" || "$web_proxy_basic_auth_user" == "None" ]]; then
  echo "missing required ${PARAM_PREFIX}/SIDIRA_WEB_PROXY_BASIC_AUTH_USER; set it to the Amplify access-control username" >&2
  exit 1
fi

if [[ -z "$web_proxy_basic_auth_hash" || "$web_proxy_basic_auth_hash" == "None" ]]; then
  echo "missing required ${PARAM_PREFIX}/SIDIRA_WEB_PROXY_BASIC_AUTH_HASH; store a Caddy-compatible bcrypt hash for the Amplify access-control password" >&2
  exit 1
fi

if [[ -z "$local_cred_key" || "$local_cred_key" == "None" ]]; then
  install -d -m 700 "$(dirname "$LOCAL_CRED_KEY_FILE")"
  if [[ ! -s "$LOCAL_CRED_KEY_FILE" ]]; then
    openssl rand -base64 32 | tr '+/' '-_' > "$LOCAL_CRED_KEY_FILE"
    chmod 600 "$LOCAL_CRED_KEY_FILE"
  fi
  local_cred_key="$(cat "$LOCAL_CRED_KEY_FILE")"
fi

write_env SIDIRA_CUSTOMER_ID "$(default_value "$customer_id" "streamly_sample")"
write_env SIDIRA_CORS_ORIGINS "$(default_value "$cors_origins" "https://sidira.ai,https://app.sidira.ai")"
write_env SIDIRA_MAX_AGENTS "$(default_value "$max_agents" "100")"
write_env SIDIRA_CRED_MODE "$(default_value "$cred_mode" "local")"
write_env SIDIRA_LOCAL_CRED_KEY "$local_cred_key"
write_env SIDIRA_LOCAL_ARTIFACTS "$(default_value "$local_artifacts" "/app/local-artifacts")"
write_env SIDIRA_INTERNAL_API_KEY "$internal_api_key"
# Optional: when both are unset the Clerk gate stays disabled (write_env skips
# empty values), preserving the pre-auth deploy behavior.
write_env SIDIRA_CLERK_SECRET_KEY "$clerk_secret_key"
write_env SIDIRA_CLERK_AUTHORIZED_PARTIES "$clerk_authorized_parties"
# Clerk webhook signing secret (whsec_…). Independent of the session gate above:
# /webhooks/clerk is signature-verified and safe to enable in prod on its own,
# since it never sees app traffic. Unset -> the endpoint 503s (refuses to act on
# unverifiable deliveries); write_env skips empty values.
write_env SIDIRA_CLERK_WEBHOOK_SECRET "$clerk_webhook_secret"
write_env SIDIRA_WEB_PROXY_BASIC_AUTH_USER "$web_proxy_basic_auth_user"
write_env SIDIRA_WEB_PROXY_BASIC_AUTH_HASH "$web_proxy_basic_auth_hash"
write_env DATABASE_URL "$database_url"
write_env SIDIRA_AUTO_MIGRATE "$auto_migrate"
# #268 Phase 2: the worker only actually runs builds when BOTH (a) Postgres is
# configured (it claims via a DB-level lock and exits otherwise) AND (b) docker
# compose is available (the non-compose `docker run` branch below starts only
# sidira-api, never the worker). Default to "worker" only when both hold — that's
# the supported prod shape for persona builds. In the degraded shapes (no DB /
# no compose) persona builds aren't really supported: there's no worker, and the
# API image omits the ML stack by design (#268), so a build can't run there
# either way. Default those to "inprocess" so a submitted build at least fails
# fast and visibly ("sidira-personas not installed") rather than sitting PENDING
# forever waiting on a worker that was never started. An explicit SSM value wins.
if docker compose version >/dev/null 2>&1; then
  compose_available=1
else
  compose_available=0
fi
if [[ -n "$database_url" && "$database_url" != "None" && "$compose_available" == "1" ]]; then
  persona_build_mode_default="worker"
else
  persona_build_mode_default="inprocess"
fi
write_env SIDIRA_PERSONA_BUILD_MODE "$(default_value "$persona_build_mode" "$persona_build_mode_default")"

# Optional secrets passed straight through from Parameter Store. Each is
# omitted from the env file when its SSM param is absent (write_env skips
# empty/None), so the app falls back to its unconfigured behavior.
# SIDIRA_CRAWLER_DISPATCH_TOKEN is the GitHub PAT that lets POST /crawls
# dispatch crawl.yml (#193); without it the crawl routes 503 by design.
# SIDIRA_CRAWLER_CREDENTIALS_TOKEN is the CI-only shared secret the crawler
# presents to GET /internal/crawl-credentials/{customer} (#206 Slice C);
# without it the credential-pull route 503s and no logins are delivered.
# R2_PACK_* (#208) configure a read-only store for crawler-published Feature
# Packs: setting R2_PACK_BUCKET makes the backend serve a customer's latest
# pack live from R2 (no per-crawl import) while writes stay on the local
# bind-mount. Distinct from R2_BUCKET, which would flip the whole store.
# #206 Slice C: the two crawler tokens are paired. SIDIRA_CRAWLER_DISPATCH_TOKEN
# enables POST /crawls; once it is enabled, every real-tenant crawl pulls logins
# at run start with SIDIRA_CRAWLER_CREDENTIALS_TOKEN, and the dispatch preflight
# now 503s without it. Shipping the first without the second yields a backend
# whose "Start crawl" is broken for real tenants, so fail fast on that
# half-configured state. (Neither set = crawls simply disabled, still a valid
# deploy — that is why these stay out of the always-required checks above.)
dispatch_token="$(ssm_value SIDIRA_CRAWLER_DISPATCH_TOKEN)"
credentials_token="$(ssm_value SIDIRA_CRAWLER_CREDENTIALS_TOKEN)"
if [[ -n "$dispatch_token" && "$dispatch_token" != "None" ]] \
   && [[ -z "$credentials_token" || "$credentials_token" == "None" ]]; then
  echo "crawl dispatch is enabled (SIDIRA_CRAWLER_DISPATCH_TOKEN present) but ${PARAM_PREFIX}/SIDIRA_CRAWLER_CREDENTIALS_TOKEN is missing; real-tenant POST /crawls would 503 — set the credential-pull token (see deploy/REDEPLOY.md) or remove the dispatch token to disable crawls" >&2
  exit 1
fi

for key in \
  GROQ_API_KEY \
  ANTHROPIC_API_KEY \
  OPENAI_API_KEY \
  R2_BUCKET \
  R2_ENDPOINT_URL \
  R2_ACCESS_KEY_ID \
  R2_SECRET_ACCESS_KEY \
  R2_PACK_BUCKET \
  R2_PACK_ENDPOINT_URL \
  R2_PACK_ACCESS_KEY_ID \
  R2_PACK_SECRET_ACCESS_KEY \
  SIDIRA_CRAWLER_DISPATCH_TOKEN \
  SIDIRA_CRAWLER_CREDENTIALS_TOKEN
do
  value="$(ssm_value "$key")"
  write_env "$key" "$value"
done

install -d -m 755 "$REPO_DIR/local-artifacts"
chown -R "${CONTAINER_UID}:${CONTAINER_GID}" "$REPO_DIR/local-artifacts"
chmod -R u+rwX,go+rX "$REPO_DIR/local-artifacts"

if [[ "$compose_available" == "1" ]]; then
  # #468: reclaim BEFORE building. The 8GB root often runs >90% full, and a
  # stale build cache can starve even the API build on this small box. Guarded
  # so a prune failure never fails the deploy. (A second reclaim runs after the
  # restart, below, once the new running images are safe from pruning.)
  docker builder prune -af || true
  docker image prune -f || true

  # #468: deploy the API + Caddy FIRST, on their own, as the critical path. This
  # MUST NOT be coupled to the persona-worker image, whose ML stack
  # (numpy/scipy/scikit-learn/hdbscan) can fail to build on this small box
  # (disk/OOM). Previously a single `build` (all services) + `up -d` meant a
  # worker-build failure aborted the whole deploy under `set -e` *before* the
  # API was ever restarted, so every deploy needed a manual api-only restart.
  SIDIRA_API_ENV_FILE="$COMPOSE_ENV_FILE" \
    docker compose -p sidira -f deploy/docker-compose.api.yml build api
  SIDIRA_API_ENV_FILE="$COMPOSE_ENV_FILE" \
    docker compose -p sidira -f deploy/docker-compose.api.yml up -d --no-deps api caddy

  # #268 Phase 2 worker — best-effort and NON-FATAL. If the ML image can't build
  # here, the API stays up on the new build and the already-running worker keeps
  # serving its previous image (it changes rarely; the durable fix is an off-box
  # build, #293). Both the build (if-guard) AND the start (|| warn) are guarded so
  # neither trips `set -e` and aborts the final reclaim/`docker ps`.
  if SIDIRA_API_ENV_FILE="$COMPOSE_ENV_FILE" \
       docker compose -p sidira -f deploy/docker-compose.api.yml build worker; then
    SIDIRA_API_ENV_FILE="$COMPOSE_ENV_FILE" \
      docker compose -p sidira -f deploy/docker-compose.api.yml up -d --no-deps worker \
      || echo "WARNING: persona-worker image built but failed to start (see #468). API is up; worker left on its previous container." >&2
  else
    echo "WARNING: persona-worker image build failed (disk/OOM on this box; see #468/#293). API deployed; worker left on its previous image." >&2
  fi

  # #268 Phase 2: the ML-heavy worker image balloons Docker's build cache, and
  # the 8GB EC2 root disk fills up → the NEXT deploy fails "No space left". Run
  # this reclaim AFTER the restarts so the running images aren't pruned. Guarded
  # so a prune failure never fails the deploy.
  docker builder prune -af || true
  docker image prune -f || true
else
  docker network create sidira >/dev/null 2>&1 || true
  docker build -t sidira-api:latest backend
  docker pull caddy:2-alpine
  docker rm -f sidira-api sidira-caddy >/dev/null 2>&1 || true
  docker run -d \
    --name sidira-api \
    --restart unless-stopped \
    --network sidira \
    --network-alias api \
    --env-file "$ENV_FILE" \
    -e PORT=8000 \
    -v "$REPO_DIR/local-artifacts:/app/local-artifacts:rw" \
    sidira-api:latest
  docker run -d \
    --name sidira-caddy \
    --restart unless-stopped \
    --network sidira \
    --env-file "$ENV_FILE" \
    -p 80:80 \
    -p 443:443 \
    -v "$REPO_DIR/deploy/Caddyfile.api:/etc/caddy/Caddyfile:ro" \
    -v sidira_caddy_data:/data \
    -v sidira_caddy_config:/config \
    caddy:2-alpine
fi

docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

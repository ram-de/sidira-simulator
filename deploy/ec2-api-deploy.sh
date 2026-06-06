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
web_proxy_basic_auth_user="$(ssm_value SIDIRA_WEB_PROXY_BASIC_AUTH_USER)"
web_proxy_basic_auth_hash="$(ssm_value SIDIRA_WEB_PROXY_BASIC_AUTH_HASH)"
database_url="$(ssm_value DATABASE_URL)"
auto_migrate="$(ssm_value SIDIRA_AUTO_MIGRATE)"

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
write_env SIDIRA_MAX_AGENTS "$(default_value "$max_agents" "50")"
write_env SIDIRA_CRED_MODE "$(default_value "$cred_mode" "local")"
write_env SIDIRA_LOCAL_CRED_KEY "$local_cred_key"
write_env SIDIRA_LOCAL_ARTIFACTS "$(default_value "$local_artifacts" "/app/local-artifacts")"
write_env SIDIRA_INTERNAL_API_KEY "$internal_api_key"
# Optional: when both are unset the Clerk gate stays disabled (write_env skips
# empty values), preserving the pre-auth deploy behavior.
write_env SIDIRA_CLERK_SECRET_KEY "$clerk_secret_key"
write_env SIDIRA_CLERK_AUTHORIZED_PARTIES "$clerk_authorized_parties"
write_env SIDIRA_WEB_PROXY_BASIC_AUTH_USER "$web_proxy_basic_auth_user"
write_env SIDIRA_WEB_PROXY_BASIC_AUTH_HASH "$web_proxy_basic_auth_hash"
write_env DATABASE_URL "$database_url"
write_env SIDIRA_AUTO_MIGRATE "$auto_migrate"

for key in \
  GROQ_API_KEY \
  ANTHROPIC_API_KEY \
  OPENAI_API_KEY \
  R2_BUCKET \
  R2_ENDPOINT_URL \
  R2_ACCESS_KEY_ID \
  R2_SECRET_ACCESS_KEY
do
  value="$(ssm_value "$key")"
  write_env "$key" "$value"
done

install -d -m 755 "$REPO_DIR/local-artifacts"
chown -R "${CONTAINER_UID}:${CONTAINER_GID}" "$REPO_DIR/local-artifacts"
chmod -R u+rwX,go+rX "$REPO_DIR/local-artifacts"

if docker compose version >/dev/null 2>&1; then
  SIDIRA_API_ENV_FILE="$COMPOSE_ENV_FILE" \
    docker compose -p sidira -f deploy/docker-compose.api.yml build
  SIDIRA_API_ENV_FILE="$COMPOSE_ENV_FILE" \
    docker compose -p sidira -f deploy/docker-compose.api.yml up -d
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

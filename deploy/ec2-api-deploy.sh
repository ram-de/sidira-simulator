#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${SIDIRA_REPO_DIR:-/opt/sidira/repo}"
DEPLOY_BRANCH="${SIDIRA_DEPLOY_BRANCH:-main}"
AWS_REGION="${AWS_REGION:-us-east-1}"
PARAM_PREFIX="${SIDIRA_PARAM_PREFIX:-/sidira/prod}"
ENV_FILE="${SIDIRA_API_ENV_FILE:-/opt/sidira/api.env}"
LOCAL_CRED_KEY_FILE="${SIDIRA_LOCAL_CRED_KEY_FILE:-/opt/sidira/local_cred_key}"
DEPLOY_KEY="${SIDIRA_DEPLOY_KEY:-/root/.ssh/sidira_deploy}"

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
  aws ssm get-parameter \
    --region "$AWS_REGION" \
    --name "${PARAM_PREFIX}/${name}" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text 2>/dev/null || true
}

sanitize_value() {
  printf '%s' "$1" | tr -d '\r\n'
}

write_env() {
  local key="$1"
  local value="$2"
  if [[ -n "$value" && "$value" != "None" ]]; then
    printf '%s=%s\n' "$key" "$(sanitize_value "$value")" >> "$ENV_FILE"
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
umask 077
: > "$ENV_FILE"

customer_id="$(ssm_value SIDIRA_CUSTOMER_ID)"
cors_origins="$(ssm_value SIDIRA_CORS_ORIGINS)"
max_agents="$(ssm_value SIDIRA_MAX_AGENTS)"
cred_mode="$(ssm_value SIDIRA_CRED_MODE)"
local_artifacts="$(ssm_value SIDIRA_LOCAL_ARTIFACTS)"
local_cred_key="$(ssm_value SIDIRA_LOCAL_CRED_KEY)"

if [[ -z "$local_cred_key" || "$local_cred_key" == "None" ]]; then
  install -d -m 700 "$(dirname "$LOCAL_CRED_KEY_FILE")"
  if [[ ! -s "$LOCAL_CRED_KEY_FILE" ]]; then
    openssl rand -hex 32 > "$LOCAL_CRED_KEY_FILE"
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

for key in \
  GROQ_API_KEY \
  ANTHROPIC_API_KEY \
  OPENAI_API_KEY \
  DATABASE_URL \
  R2_BUCKET \
  R2_ENDPOINT_URL \
  R2_ACCESS_KEY_ID \
  R2_SECRET_ACCESS_KEY
do
  write_env "$key" "$(ssm_value "$key")"
done

docker rm -f sidira-api sidira-caddy >/dev/null 2>&1 || true

if docker compose version >/dev/null 2>&1; then
  docker compose -p sidira -f deploy/docker-compose.api.yml up -d --build
else
  docker network create sidira >/dev/null 2>&1 || true
  docker build -t sidira-api:latest backend
  docker run -d \
    --name sidira-api \
    --restart unless-stopped \
    --network sidira \
    --network-alias api \
    --env-file "$ENV_FILE" \
    -e PORT=8000 \
    -v "$REPO_DIR/local-artifacts:/app/local-artifacts:ro" \
    sidira-api:latest
  docker run -d \
    --name sidira-caddy \
    --restart unless-stopped \
    --network sidira \
    -p 80:80 \
    -p 443:443 \
    -v "$REPO_DIR/deploy/Caddyfile.api:/etc/caddy/Caddyfile:ro" \
    -v sidira_caddy_data:/data \
    -v sidira_caddy_config:/config \
    caddy:2-alpine
fi

docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

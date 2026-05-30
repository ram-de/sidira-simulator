# Sidira Deployment Helpers

This directory contains the browser-console-friendly production bootstrap path.

## Backend API on a small AWS VM

Use this when avoiding a local AWS CLI profile:

1. Create a small EC2 instance from the AWS Console.
2. Attach `SidiraApiProdRole` as the instance profile so the server can read
   only `/sidira/prod/*` parameters.
3. Attach an Elastic IP.
4. Point `api.sidira.ai` at that IP.
5. Use SSM Session Manager / RunCommand from the AWS browser console. Avoid SSH
   unless there is a specific operational reason.
6. Install Docker, Git, and AWS CLI on the instance, then clone this repo to
   `/opt/sidira/repo`.
7. Store production secrets as Parameter Store `SecureString` values under
   `/sidira/prod/*`; do not put them in GitHub, chat, or EC2 user-data. The
   deploy requires `/sidira/prod/SIDIRA_INTERNAL_API_KEY`,
   `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_USER`, and
   `/sidira/prod/SIDIRA_WEB_PROXY_BASIC_AUTH_HASH`. Amplify should only receive
   the non-secret proxy base URL.
8. Run the EC2 deploy helper:

```bash
cd /opt/sidira/repo
sudo SIDIRA_DEPLOY_BRANCH=main ./deploy/ec2-api-deploy.sh
```

The deploy helper writes `/opt/sidira/api.env`, pulls the selected branch, reads
available `/sidira/prod/*` parameters through the instance role, builds the API
image, and starts the API plus Caddy. Caddy terminates HTTPS and proxies to the
backend; the FastAPI app requires `X-Sidira-Internal-Key` for all API paths
except `/health`. Browser traffic goes through the Next.js same-origin `/api`
proxy, which forwards the browser Basic Auth header to Caddy. Caddy validates
that header at runtime and only then adds `X-Sidira-Internal-Key` server-side.
When Docker Compose is available, the helper also writes a Compose-safe
`/opt/sidira/api.env.compose` file so bcrypt `$` characters are not interpreted
as Compose variable expansion. The fallback `docker run --env-file` path keeps
using the raw env file.
Missing optional provider keys are omitted from the env file; configure at least
`/sidira/prod/GROQ_API_KEY` before expecting model-backed simulations. #68 is
merged, so durable metadata can now be enabled by setting
`/sidira/prod/DATABASE_URL` as a SecureString and setting
`/sidira/prod/SIDIRA_AUTO_MIGRATE=1` only for the deployment that should run
Alembic migrations.

If running manually from the repo root instead, create `/opt/sidira/api.env`
with backend production environment variables, prepare the artifact tree for the
container user, and run:

```bash
sudo install -d -m 755 local-artifacts
sudo chown -R 10001:10001 local-artifacts
sudo chmod -R u+rwX,go+rX local-artifacts
docker compose -f deploy/docker-compose.api.yml up -d --build
```

Caddy terminates HTTPS for `api.sidira.ai` and proxies to the FastAPI
container. The backend image is built from `backend/Dockerfile`.

For local compose validation before the production env file exists, set
`SIDIRA_API_ENV_FILE` to a temporary env file path.

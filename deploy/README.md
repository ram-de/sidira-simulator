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
   `/sidira/prod/*`; do not put them in GitHub, chat, or EC2 user-data.
8. Run the EC2 deploy helper:

```bash
cd /opt/sidira/repo
sudo SIDIRA_DEPLOY_BRANCH=main ./deploy/ec2-api-deploy.sh
```

The deploy helper writes `/opt/sidira/api.env`, pulls the selected branch, reads
available `/sidira/prod/*` parameters through the instance role, builds the API
image, and starts the API plus Caddy. Missing optional provider keys are omitted
from the env file; configure at least `/sidira/prod/GROQ_API_KEY` before
expecting model-backed simulations.

If running manually from the repo root instead, create `/opt/sidira/api.env`
with backend production environment variables and run:

```bash
docker compose -f deploy/docker-compose.api.yml up -d --build
```

Caddy terminates HTTPS for `api.sidira.ai` and proxies to the FastAPI
container. The backend image is built from `backend/Dockerfile`.

For local compose validation before the production env file exists, set
`SIDIRA_API_ENV_FILE` to a temporary env file path.

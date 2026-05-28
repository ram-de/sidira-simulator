# Sidira Deployment Helpers

This directory contains the browser-console-friendly production bootstrap path.

## Backend API on a small AWS VM

Use this when avoiding a local AWS CLI profile:

1. Create a small Lightsail or EC2 instance from the AWS Console.
2. Attach a static public IP.
3. Point `api.sidira.ai` at that IP.
4. SSH from the AWS browser console, install Docker, and clone this repo.
5. Create `/opt/sidira/api.env` with backend production environment variables.
6. From the repo root, run:

```bash
docker compose -f deploy/docker-compose.api.yml up -d --build
```

Caddy terminates HTTPS for `api.sidira.ai` and proxies to the FastAPI
container. The backend image is built from `backend/Dockerfile`.

For local compose validation before the production env file exists, set
`SIDIRA_API_ENV_FILE` to a temporary env file path.

# Backend redeploy runbook — api.sidira.ai

This runbook is written to be executed by an AI agent (codex, Claude Code) or a
human. It assumes nothing beyond this repo and, for the deploy step itself,
access to the AWS account (console or a configured `aws` CLI).

## When this applies

**Every time a PR that touches `backend/` merges to `main`.** The two halves of
the app deploy asymmetrically:

- **Frontend** — AWS Amplify auto-builds on every push to `main`. Nothing to do.
- **Backend** — the FastAPI container on EC2 is redeployed **manually**. Until
  someone runs this runbook, production keeps serving the previous build.

Symptom of forgetting: the live frontend calls a route the deployed backend
does not have yet and the UI shows a banner like
`HTTP 404: {"detail":"Not Found"}`, while older routes on the same page still
work. (This happened with the `/crawl-setup` window from PR #187.)

## Steps

### 1. Confirm the backend is actually stale

```bash
curl -s https://api.sidira.ai/health
```

Expect `{"status":"ok",...}` — the API is up, just old. You cannot probe
individual routes from outside (Caddy requires Basic Auth +
`X-Sidira-Internal-Key`, and the `/api` proxy on app.sidira.ai requires a Clerk
session), so route-level verification happens on the instance in step 4.

### 2. Decide whether this deploy must run migrations

Check whether the merged work added a file under `backend/alembic/versions/`:

```bash
git fetch origin main && git diff --name-only <previously-deployed-sha>..origin/main -- backend/alembic/versions/
```

(If the previously deployed SHA is unknown, read it off the instance in step 3
via `git -C /opt/sidira/repo log -1 --oneline` before deploying.)

- **New migration AND prod uses Postgres** (`/sidira/prod/DATABASE_URL` is set
  in SSM Parameter Store): set `/sidira/prod/SIDIRA_AUTO_MIGRATE` to `1` before
  deploying, otherwise the new tables never get created and the new endpoints
  500. Per `deploy/README.md`, this flag should be `1` only for the deployment
  that runs the migrations — reset it to `0` afterwards.
- **No new migration, or prod is on the in-memory repos**: skip this step.

### 3. Run the deploy on the EC2 instance

The instance is the one whose Elastic IP `api.sidira.ai` resolves to
(`dig +short api.sidira.ai`). Prefer SSM over SSH (`deploy/README.md`).

**Via AWS console** (works with zero local setup): Console → Systems Manager →
Session Manager → start a session on the API instance, then:

```bash
cd /opt/sidira/repo
sudo SIDIRA_DEPLOY_BRANCH=main ./deploy/ec2-api-deploy.sh
```

**Via local `aws` CLI**, if a profile with SSM permissions exists:

```bash
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --targets "Key=instanceIds,Values=<instance-id>" \
  --parameters 'commands=["cd /opt/sidira/repo && sudo SIDIRA_DEPLOY_BRANCH=main ./deploy/ec2-api-deploy.sh"]' \
  --comment "sidira backend redeploy"
```

Then poll the command result with `aws ssm get-command-invocation`.

The script fetches `origin/main`, rebuilds the API image, rereads
`/sidira/prod/*` parameters, and restarts the `sidira-api` + `sidira-caddy`
containers. It is idempotent — re-running it is safe.

### 4. Verify

On the instance (SSM session or another `send-command`):

```bash
# Deployed SHA matches origin/main
git -C /opt/sidira/repo log -1 --oneline

# Containers were recreated just now
docker ps --format 'table {{.Names}}\t{{.Status}}'

# The new route(s) exist — lists every path the running API serves
docker exec sidira-api python -c "import urllib.request, json; print('\n'.join(sorted(json.load(urllib.request.urlopen('http://localhost:8000/openapi.json'))['paths'])))"
```

(The API container only exposes port 8000 on the internal Docker network, hence
`docker exec` rather than curl from the host.)

Finally, reload the affected page on https://app.sidira.ai — the 404 banner
should be gone.

### 5. Clean up

If you set `SIDIRA_AUTO_MIGRATE=1` in step 2, set it back to `0` in Parameter
Store now.

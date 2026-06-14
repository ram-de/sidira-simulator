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

### 2b. Ensure any new secrets exist in Parameter Store

`ec2-api-deploy.sh` builds the container env from a fixed set of
`/sidira/prod/*` parameters. When a merged PR introduces a new secret that the
backend reads, the parameter must exist **before** the deploy runs, otherwise
the script omits it and the feature silently runs in its unconfigured state.

Known additions:

- **#193 crawl trigger** — `POST /crawls` reads `SIDIRA_CRAWLER_DISPATCH_TOKEN`
  (a GitHub PAT with Actions read+write on `ram-de/sidira-crawler`). Store it as
  a `SecureString`; without it the crawl routes 503 by design. The deploy
  script reads it via the optional-secrets loop.

  ```bash
  aws ssm put-parameter --region us-east-1 \
    --name /sidira/prod/SIDIRA_CRAWLER_DISPATCH_TOKEN \
    --type SecureString --value '<the PAT>' --overwrite
  ```

  The local dev value lives in `backend/.env` as
  `SIDIRA_CRAWLER_DISPATCH_TOKEN=` — copy that exact value. Rotate the PAT at
  expiry (it has passed through a chat transcript).

- **#206 Slice C per-customer credential pull** — two params, both load-bearing
  the moment this deploys:

  1. `SIDIRA_LOCAL_CRED_KEY` (+ `SIDIRA_CRED_MODE=local`) — the at-rest key that
     encrypts crawl-setup passwords. **Now required:** `PUT /crawl-setup` 503s if
     it is unset (we refuse to store a login we cannot protect). The deploy
     script already reads both via `ssm_value`, but the param must exist first.
     Generate a base64 32-byte AESGCM key:

     ```bash
     KEY=$(python3 -c 'import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')
     aws ssm put-parameter --region us-east-1 --name /sidira/prod/SIDIRA_LOCAL_CRED_KEY \
       --type SecureString --value "$KEY" --overwrite
     aws ssm put-parameter --region us-east-1 --name /sidira/prod/SIDIRA_CRED_MODE \
       --type String --value local --overwrite
     ```

     > **Do not rotate this key once setups are saved** — existing blobs were
     > encrypted under it and become undecryptable if it changes. Re-saving each
     > setup is the only re-key path until KMS mode (Phase 5) lands.

  2. `SIDIRA_CRAWLER_CREDENTIALS_TOKEN` — the CI-only bearer the crawler presents
     to `GET /internal/crawl-credentials/{customer}`. Sibling to the dispatch
     token; without it the pull route 503s and the crawler logs in nowhere.
     **Now also required to dispatch:** `POST /crawls` fails closed with a 503 for
     any real tenant when this is unset, rather than starting a ~40-min walk whose
     credential pull would 503 (the sandbox demo is exempt — it never pulls). Must
     match the value configured as a secret on `ram-de/sidira-crawler` (set there
     in the crawler PR, which deploys **after** this endpoint is live).

     ```bash
     TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')
     aws ssm put-parameter --region us-east-1 \
       --name /sidira/prod/SIDIRA_CRAWLER_CREDENTIALS_TOKEN \
       --type SecureString --value "$TOKEN" --overwrite
     # then mirror $TOKEN into the crawler repo's CI secret of the same name.
     ```

- **#208 live Feature Pack read** — when `R2_PACK_BUCKET` is set the backend
  serves each customer's latest pack live from the crawler's R2 bucket
  (`get_featurepack_store()` → `R2ArtifactStore`), eliminating the manual
  per-crawl `local-artifacts/` import. **Read-only** creds scoped to the
  `customers/` prefix are sufficient — only feature-pack *reads* route to R2;
  agent memory, feedback, run-state, persona packs all stay on the local
  bind-mount (`get_store()`). Do **not** set `R2_BUCKET` for this — that is a
  global switch that would route every write to R2 and demand read-write creds.

  The bucket is **`sidira-artifacts`** (verified 2026-06-13: it holds
  `customers/<org-id>/featurepacks/…` for the live org + `streamly-sandbox`).
  This is the same bucket the crawler publishes to — its name lives only in the
  `R2_BUCKET` GitHub Actions secret on `ram-de/sidira-crawler` (not in any
  source file), so confirm it in the Cloudflare R2 dashboard rather than
  guessing. The R2 token must be **R2 → API → Object Read only**, scoped to that
  bucket. Endpoint is the bucket's S3 API URL
  (`https://<account-id>.r2.cloudflarestorage.com`).

  ```bash
  for kv in \
    R2_PACK_BUCKET=sidira-artifacts \
    R2_PACK_ENDPOINT_URL='https://<account-id>.r2.cloudflarestorage.com' \
    R2_PACK_ACCESS_KEY_ID='<read-only key id>' \
    R2_PACK_SECRET_ACCESS_KEY='<read-only secret>'; do
    aws ssm put-parameter --region us-east-1 \
      --name "/sidira/prod/${kv%%=*}" --type SecureString \
      --value "${kv#*=}" --overwrite
  done
  ```

  `R2_PACK_ENDPOINT_URL`/`_ACCESS_KEY_ID`/`_SECRET_ACCESS_KEY` fall back to the
  generic `R2_*` vars when unset, but those are absent in prod, so set all four.
  Until these exist the backend keeps reading `local-artifacts/` (today's
  behavior) — so this deploy is safe to run before the params are added; the
  live-read just stays dormant.

  > **Verify credential lengths before deploying.** An R2 access key id is
  > exactly **32** chars and the secret is **64** chars. A paste mangle (extra
  > shell text, embedded newline) is silently stored by `put-parameter` and only
  > surfaces at runtime as an opaque HTTP 500 — `read_text` catches `NoSuchKey`
  > but lets every other `ClientError` propagate, so a bad credential reads as
  > `botocore … InvalidArgument: Credential access key has length N, should be
  > 32`, not a config error. Guard the set, then read it back:
  >
  > ```bash
  > read -rsp 'R2 Access Key ID (32): ' AKID; echo;  echo "len=${#AKID}"   # MUST be 32
  > read -rsp 'R2 Secret (64): '       SAK;  echo;  echo "len=${#SAK}"     # MUST be 64
  > # only put-parameter if both lengths match; then confirm what landed:
  > aws ssm get-parameter --region us-east-1 --name /sidira/prod/R2_PACK_ACCESS_KEY_ID \
  >   --with-decryption --query Parameter.Value --output text | awk '{print "stored len:", length($0)}'
  > ```
  >
  > (Hit during the #208 deploy, 2026-06-13: the access-key param was stored as
  > 647 chars and the Library 500'd until it was re-set cleanly.)

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

> **Self-modifying-script gotcha:** when the merged change edits
> `deploy/ec2-api-deploy.sh` *itself*, run the deploy **twice**. The first
> invocation fetches the new commit but keeps executing the script body it
> started with, so any newly-added logic (e.g. a new SSM param in the secrets
> loop) does not run. The first run lands the updated script on disk; the
> second run executes it. Verify in step 4 — if a just-added secret reads back
> as unconfigured, that's this gotcha; re-run the deploy. (Hit during the #204
> dispatch-token deploy, 2026-06-12.)

### 4. Verify

On the instance (SSM session or another `send-command`):

```bash
# Deployed SHA matches origin/main
git -C /opt/sidira/repo log -1 --oneline

# Containers were recreated just now
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'

# The new route(s) exist — lists every path the deployed code serves
sudo docker exec sidira-api python -c "from sidira_simulator.main import app; print('\n'.join(sorted({r.path for r in app.routes})))"
```

For the #193 deploy specifically, also confirm the migration ran and the
dispatch token reached the container:

```bash
# crawl_runs table exists (migration 010) — Postgres prod only. get_engine()
# is async, so inspect() must run through run_sync on a connection.
sudo docker exec sidira-api python -c "
import asyncio
from sqlalchemy import inspect
from sidira_simulator.adapters.postgres import get_engine
async def main():
    async with get_engine().connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    print('crawl_runs present:', 'crawl_runs' in names)
asyncio.run(main())
"

# The dispatch token is wired (prints True, never the secret itself)
sudo docker exec sidira-api python -c "from sidira_simulator.adapters.github_actions import dispatch_configured; print('dispatch_configured:', dispatch_configured())"
```

(The route check imports the app in-process instead of calling
`/openapi.json` over HTTP: the `internal_api_key_gate` middleware 404s
keyless requests even from localhost, and the Clerk gate behind it would
still 401 — neither gate is in play when reading `app.routes` directly.)

Finally, reload the affected page on https://app.sidira.ai — the 404 banner
should be gone.

> **`/health` version is not a deploy freshness signal.** `__version__` in
> `backend/sidira_simulator/__init__.py` is a hand-bumped constant (still
> `0.1.0`), so `/health` reports `0.1.0` no matter how recent the deploy. Judge
> freshness by the deployed SHA (`git -C /opt/sidira/repo log -1`) and the
> route/migration checks above, never by the health version.

### 5. Clean up

If you set `SIDIRA_AUTO_MIGRATE=1` in step 2, set it back to `0` in Parameter
Store now.

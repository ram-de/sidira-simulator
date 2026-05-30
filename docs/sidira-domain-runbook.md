# Sidira Domain and Metadata Runbook

Canonical Phase 4.7 hostnames:

| Surface | Hostname | Purpose |
|---|---|---|
| Marketing/root | `sidira.ai` | Public entry point. Can redirect to the app while marketing is not live. |
| Marketing alias | `www.sidira.ai` | Convenience alias; permanently redirects to `sidira.ai`. |
| Frontend app | `app.sidira.ai` | Next.js customer-facing simulator. |
| Backend API | `api.sidira.ai` | FastAPI service consumed by the frontend. |

## Current Audit (2026-05-29)

- `sidira.ai` is added to Amplify custom domains and now returns CloudFront A
  answers via Route 53.
- `app.sidira.ai` is added to Amplify custom domains and now returns a
  CloudFront-backed DNS answer.
- `www.sidira.ai` is added to Amplify custom domains and now returns a
  CloudFront-backed DNS answer. The frontend middleware redirects it to
  `https://sidira.ai`.
- `api.sidira.ai` resolves to the production API Elastic IP
  `32.194.187.147`.
- Route 53 public hosted zone exists: `Z01279103CLJX7PS4TEFN`.
- Namecheap registrar nameservers were updated to Route 53 Custom DNS on
  2026-05-28. Public `dig NS sidira.ai` now returns the Route 53 delegation.
- Route 53 assigned nameservers:
  `ns-1394.awsdns-46.org`, `ns-844.awsdns-41.net`,
  `ns-1649.awsdns-14.co.uk`, `ns-474.awsdns-59.com`.
- Amplify app exists: `sidira-simulator` / app ID `dbzf69xeoypqa`.
- Temporary #115 branch deployment is live at
  `https://codex-115-sidira-domain-metadata.dbzf69xeoypqa.amplifyapp.com`.
  Smoke check returned HTTP 200 and rendered the Sidira home page.
- Amplify custom domain setup is available for `sidira.ai` with an Amplify
  managed certificate. The root, `app`, and `www` hostnames are mapped to
  `codex/115-sidira-domain-metadata`.
- HTTPS smoke checks returned HTTP 200 for `https://app.sidira.ai` with normal
  resolution and for `https://sidira.ai` when pointed at the freshly resolved
  CloudFront target; local resolver cache may lag the public apex DNS answer
  for a short period.
- GitHub Project #1 is titled Sidira.
- The simulator repo is renamed to `ram-de/sidira-simulator`; local `origin` should point to `git@github.com-personal:ram-de/sidira-simulator.git`.
- `pythia-personas` and `pythia-crawler` descriptions/homepages use Sidira metadata, but their repo/package names remain unchanged until producer rename work is explicitly scheduled.
- Backend API baseline is live on EC2 instance `i-04b155fafcc90042b`
  (`sidira-api-prod`, `t4g.micro`, Elastic IP `32.194.187.147`) behind
  Caddy. `GET https://api.sidira.ai/health` returns
  `{"status":"ok","version":"0.1.0"}`.
- The API container currently uses the checked-in `streamly_sample` artifact
  fixture (`SIDIRA_CUSTOMER_ID=streamly_sample`) mounted read/write from
  `/opt/sidira/repo/local-artifacts` to `/app/local-artifacts`, because
  simulations write run state and agent memory under the same artifact root.
- `GET https://api.sidira.ai/capabilities` returns the
  `streamly_sample` manifest, and `GET https://api.sidira.ai/simulations`
  returns `[]`.
- `GET https://api.sidira.ai/models` returns Groq-backed models after
  `/sidira/prod/GROQ_API_KEY` was added as an SSM `SecureString` and the API
  was redeployed through the EC2 helper.
- Amplify global access control is enabled for `sidira.ai`, `www.sidira.ai`,
  and the preview branch. Unauthenticated browser requests return HTTP 401 with
  `WWW-Authenticate: Basic realm="Login"`.
- Direct backend access is still gated by the internal API key middleware:
  `/health` remains public, while non-health routes return 404 without the
  `x-sidira-internal-key` header.

## Deploy Environment

Frontend:

```bash
SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai
SIDIRA_INTERNAL_API_KEY=<same value as /sidira/prod/SIDIRA_INTERNAL_API_KEY>
```

Backend:

```bash
SIDIRA_CORS_ORIGINS=https://sidira.ai,https://app.sidira.ai
SIDIRA_CUSTOMER_ID=streamly_sample
SIDIRA_LOCAL_ARTIFACTS=/app/local-artifacts
```

Keep local development on `http://127.0.0.1:3000` and `http://127.0.0.1:8000`.

## Recommended AWS Shape

Use this as the first production topology:

| Surface | AWS service | Notes |
|---|---|---|
| DNS | Route 53 hosted zone for `sidira.ai` | Keep Namecheap as registrar; replace Namecheap nameservers with the four Route 53 nameservers. |
| Frontend | AWS Amplify Hosting | Deploys `frontend/` from GitHub using the root `amplify.yml`. Add custom domains `sidira.ai`, `www.sidira.ai`, and `app.sidira.ai`. |
| Backend | EC2 instance | Browser-console-friendly path with proper secret handling: attach an IAM instance profile, build `backend/Dockerfile` on the instance, and run `deploy/docker-compose.api.yml` behind Caddy for `api.sidira.ai`. |
| Database | Optional Postgres, code merged in #68 | Store the managed Postgres URL as `/sidira/prod/DATABASE_URL`, enable `SIDIRA_AUTO_MIGRATE=1` only for the deployment that should run Alembic, and verify list/detail/agent reloads before relying on durable metadata. |
| Artifacts | Cloudflare R2 for now | Keep the existing artifact contract; switching storage is a separate migration. |

## Production Postgres Provider Decision

#68 only wired the app to use Postgres when `DATABASE_URL` exists. It did not
create the production database. Track the actual provider/provisioning work in
[#128](https://github.com/ram-de/sidira-simulator/issues/128).

For the current alpha footprint (roughly 4-5 users, light daily usage), prefer
the lowest-ops managed Postgres option:

| Provider | Use when | Tradeoff |
|---|---|---|
| Neon | We only need managed/serverless Postgres for Sidira metadata. | Lowest-ops and likely cheapest for intermittent alpha traffic. |
| Supabase | We expect to use its platform features later: Auth, Storage, Realtime, or auto APIs. | Supabase is not a Postgres replacement; it is managed Postgres plus backend platform services. More product surface than we need today. |
| AWS RDS Postgres | We need AWS-native VPC/IAM/control-plane integration. | More AWS-native, but heavier and likely more expensive for the current alpha. |

Decision: start with Neon unless we deliberately want Supabase Auth or Storage
soon. RDS is a later upgrade path if AWS-native isolation/control becomes more
important than low operational overhead.

Current #128 bootstrap status:

- Neon project `sidira-prod` exists in AWS `us-east-1` on the Free plan for the
  current alpha footprint.
- `/sidira/prod/DATABASE_URL` is configured in SSM Parameter Store as a
  `SecureString`.
- The live SSM URL was sanitized to remove `channel_binding=require`; asyncpg
  does not accept that provider query parameter. The backend URL normalizer also
  strips it so future Neon copy/paste URLs do not break production startup or
  migrations.
- `/sidira/prod/SIDIRA_AUTO_MIGRATE` was set to `1` for the first
  database-enabled backend deploy, then set back to `0`.
- EC2 Run Command deployment `34b86c61-1323-4c77-87b8-3c53193fa6c2` succeeded
  after disabling auto-migrate, so `/opt/sidira/api.env` has the safe steady-
  state value.
- EC2 Run Command `e014adae-02ae-4af9-b7ce-43073c8eb219` refreshed the backend
  env, ran Alembic upgrade, and confirmed production is at `008 (head)`.
- Full persistence smoke passed via EC2 Run Command
  `3b53c2e7-e9c3-4bd3-9e47-50fb68a2d7a2`: created production simulation
  `4b7fe54e-66ae-4696-9de7-308d06f846e7`, observed it complete with one agent,
  verified list/detail/agents, redeployed the backend, then verified the same
  records still loaded from Postgres.
- `GET https://api.sidira.ai/health` returns 200 after the redeploy, while
  direct non-health routes still return 404 without the internal key.

Do not use AWS App Runner for the first deployment unless the AWS account already
has App Runner access. AWS now says App Runner is no longer open to new
customers, so Lightsail Containers is the lower-friction AWS-native backend path
for a new personal account only after we have a clean image-publishing path. If
we are avoiding local AWS CLI profiles, start with a small EC2 instance instead
so the server can use an IAM role to read only Sidira production secrets.

## Secrets And Credentials

Keep production secrets out of GitHub, Amplify public variables, user-data, PR
bodies, and docs. Production browser traffic should use the same-origin Next
`/api` proxy. Amplify receives the backend origin as a server-side variable
(`SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai`) plus the temporary internal
API key as a server-side secret (`SIDIRA_INTERNAL_API_KEY`). The Next build
uses `frontend/next.config.js` to make those values available to server routes;
do not expose either value through `NEXT_PUBLIC_*` config. This is an
alpha-stage gateway-token workaround: Amplify/Next SSR env values can be
readable to users with deployment artifact access. The real model-provider
keys stay only on the backend host, and #124 tracks moving web proxy auth off
build artifacts before broader access.

Store backend secrets under `/sidira/prod/*` in AWS-managed secret storage:

```bash
/sidira/prod/GROQ_API_KEY
/sidira/prod/ANTHROPIC_API_KEY
/sidira/prod/OPENAI_API_KEY
/sidira/prod/R2_BUCKET
/sidira/prod/R2_ENDPOINT_URL
/sidira/prod/R2_ACCESS_KEY_ID
/sidira/prod/R2_SECRET_ACCESS_KEY
/sidira/prod/SIDIRA_LOCAL_CRED_KEY
/sidira/prod/SIDIRA_INTERNAL_API_KEY
/sidira/prod/DATABASE_URL
/sidira/prod/SIDIRA_AUTO_MIGRATE
```

Use Parameter Store `SecureString` for lightweight provider/R2 keys. Use
Secrets Manager for credentials where rotation/lifecycle management matters,
especially database credentials. The #68 backend wiring is merged; once
`/sidira/prod/DATABASE_URL` is set, pair the first database-enabled rollout with
an explicit `/sidira/prod/SIDIRA_AUTO_MIGRATE=1` deployment when you want app
startup to run Alembic migrations. The EC2 instance role should have least-
privilege access to read only the Sidira production paths and decrypt only the
matching KMS key.

Current production bootstrap status:

- IAM role `SidiraApiProdRole` is attached to the EC2 instance through
  instance profile `SidiraApiProdProfile`.
- The role can read `/sidira/prod/*` Parameter Store paths and decrypt matching
  SSM SecureString values through the AWS-managed SSM/KMS path.
- `/sidira/prod/GROQ_API_KEY` is configured as a `SecureString`; optional
  Anthropic/OpenAI keys can be added later under the same prefix.
- `/sidira/prod/DATABASE_URL` is configured as a `SecureString` for the Neon
  production database. If copying from Neon, remove `channel_binding=require`;
  asyncpg does not accept it.
- `/sidira/prod/SIDIRA_AUTO_MIGRATE` should normally stay `0`; set it to `1`
  only for an intentional migration deployment, then immediately return it to
  `0` and redeploy so the runtime env file is refreshed.
- `/sidira/prod/SIDIRA_INTERNAL_API_KEY` is required before deploying the
  backend from `main`; set the same value in Amplify as the server-side
  `SIDIRA_INTERNAL_API_KEY` environment variable.
- The EC2 deployment uses `/opt/sidira/api.env` generated on the instance by
  `deploy/ec2-api-deploy.sh`. The helper reads approved `/sidira/prod/*`
  parameters at deploy time and fails on access/KMS/region errors rather than
  restarting with a partially empty secret file.

## Local vs Production Config

Local development stays file-backed. By default, browser code calls the
same-origin `/api` proxy and the proxy forwards to the local API:

```bash
# frontend/.env.local
SIDIRA_API_BASE_INTERNAL=http://127.0.0.1:8000

# Optional direct browser-to-backend mode, bypassing the Next proxy:
# NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000

# backend/.env
SIDIRA_CUSTOMER_ID=demo
SIDIRA_LOCAL_ARTIFACTS=../local-artifacts
SIDIRA_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SIDIRA_CRED_MODE=local
```

Production config belongs in AWS-managed environment variables, not committed
files:

```bash
# Amplify server-side environment variables
SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai
SIDIRA_INTERNAL_API_KEY=<same value as /sidira/prod/SIDIRA_INTERNAL_API_KEY>

# EC2/Docker environment variables
SIDIRA_CUSTOMER_ID=streamly_sample
SIDIRA_CORS_ORIGINS=https://sidira.ai,https://app.sidira.ai
SIDIRA_LOCAL_ARTIFACTS=/app/local-artifacts
SIDIRA_INTERNAL_API_KEY=<from Parameter Store SecureString>
GROQ_API_KEY=<from Parameter Store SecureString>
ANTHROPIC_API_KEY=<optional>
OPENAI_API_KEY=<optional>
R2_BUCKET=<artifact bucket>
R2_ENDPOINT_URL=<r2 endpoint>
R2_ACCESS_KEY_ID=<r2 access key>
R2_SECRET_ACCESS_KEY=<r2 secret key>
```

## AWS Console Checklist

Route 53:

- Create a public hosted zone for `sidira.ai`. Done: `Z01279103CLJX7PS4TEFN`.
- Copy the four NS values from the hosted zone. Done:
  `ns-1394.awsdns-46.org`, `ns-844.awsdns-41.net`,
  `ns-1649.awsdns-14.co.uk`, `ns-474.awsdns-59.com`.
- In Namecheap, set Domain > Nameservers to Custom DNS and paste the four Route
  53 nameservers. Done 2026-05-28.
- Verify DNS propagation with `dig NS sidira.ai`. Done; public delegation now
  returns the Route 53 nameservers.

Amplify Hosting:

- Create an Amplify app from GitHub repo `ram-de/sidira-simulator`. Done:
  app ID `dbzf69xeoypqa`.
- Select the branch to deploy. Done for the temporary #115 deployment:
  `codex/115-sidira-domain-metadata`. After #115 merges, connect or switch the
  production branch to `main`.
- Mark it as a monorepo app with app root `frontend`. Done.
- Confirm environment variable `AMPLIFY_MONOREPO_APP_ROOT=frontend`. Done.
- Remove any production `NEXT_PUBLIC_API_BASE=https://api.sidira.ai` setting so
  browser traffic uses `/api`; set `SIDIRA_API_BASE_INTERNAL=https://api.sidira.ai`
  and server-side `SIDIRA_INTERNAL_API_KEY=<same value as Parameter Store>`.
- Let Amplify use the root `amplify.yml`. Done. The build spec fails fast when
  either proxy variable is missing, writes both into `frontend/.env.production`
  before `next build`, and `frontend/next.config.js` passes them into the server
  route bundle. Do not commit that generated file. Treat the proxy token as a
  revocable alpha gateway token until #124 replaces this with runtime-secret
  proxy auth.
- Add custom domains `sidira.ai`, `www.sidira.ai`, and `app.sidira.ai`; let
  Amplify create or show the required DNS records in Route 53. Done.
  `www.sidira.ai` redirects to the apex through the frontend middleware.

Backend API EC2 VM:

- Create an IAM role named `SidiraApiProdRole` with read access only to
  `/sidira/prod/*` secret paths and the matching KMS decrypt permission. Done.
- Create a small EC2 instance from the AWS Console and attach
  `SidiraApiProdRole` as the instance profile. Done:
  `i-04b155fafcc90042b`.
- Attach an Elastic IP. Done: `32.194.187.147`.
- Add an `A` record for `api.sidira.ai` pointing to that IP. Done.
- Open inbound ports `80` and `443`; do not open SSH unless there is a specific
  operational need. Done through security group `sidira-api-sg`.
- Use SSM Session Manager / RunCommand for administration instead of SSH. Done.
- Add the read-only GitHub deploy key
  `SHA256:Z5gu5BOLJL5nRyGl9YUdkJWSuiKyHxRxhk9MWrmUC8c` to
  `ram-de/sidira-simulator`. Done.
- Create `/sidira/prod/SIDIRA_INTERNAL_API_KEY` as a Parameter Store
  `SecureString`, and set the same value in Amplify as the server-side
  `SIDIRA_INTERNAL_API_KEY` variable before switching the live deployment to
  `main`.
- Clone `ram-de/sidira-simulator`, build `backend/Dockerfile`, and run
  `sidira-api` plus `sidira-caddy` Docker containers. Done.
- Create `/opt/sidira/api.env` on the instance with the backend environment
  variables listed above, loaded from AWS-managed secrets. Done through
  `deploy/ec2-api-deploy.sh`.
- From the repo root on the instance, run the API image behind Caddy. Done with
  the current branch image; next deploy should use
  `sudo SIDIRA_DEPLOY_BRANCH=main ./deploy/ec2-api-deploy.sh` after #115
  merges.
- If validating compose before the production env file exists, set
  `SIDIRA_API_ENV_FILE` to a temporary env file path.
- Verify `https://api.sidira.ai/health` returns `{"status":"ok"}`.

## DNS And HTTPS Checklist

- Point `sidira.ai` at the chosen frontend/edge provider. Done via Amplify /
  CloudFront.
- Point `www.sidira.ai` at the frontend and redirect it to `https://sidira.ai`.
  Done via Amplify / CloudFront plus Next middleware.
- Point `app.sidira.ai` at the Next.js deployment. Done via Amplify /
  CloudFront.
- Point `api.sidira.ai` at the FastAPI deployment. Done: A record to
  `32.194.187.147`.
- Enable provider-managed HTTPS certificates for all three names. Done for
  `sidira.ai`, `www.sidira.ai`, and `app.sidira.ai` through Amplify managed
  certificates; done for `api.sidira.ai` through Caddy/Let's Encrypt on EC2.
- Verify `GET https://api.sidira.ai/health` returns `{"status":"ok"}`. Done.
- Verify the frontend can call the API through the same-origin `/api` proxy
  without exposing the internal API key to browser JavaScript. Done for
  `https://sidira.ai/simulations/new`; capabilities load and no console errors
  were observed.

## Pause Or Resume Backend

Use this when the frontend can stay up, but live API/model calls should stop
temporarily, for example to prevent accidental Groq usage during development.
Run commands through AWS Console > Systems Manager > Run Command against EC2
instance `i-04b155fafcc90042b`.

Pause API traffic:

```bash
cd /opt/sidira/repo
docker compose -p sidira -f deploy/docker-compose.api.yml stop api
```

Resume API traffic:

```bash
cd /opt/sidira/repo
docker compose -p sidira -f deploy/docker-compose.api.yml start api
```

If the host was deployed through the fallback non-Compose path, use
`docker stop sidira-api` and `docker start sidira-api` instead.

Expected behavior while paused:

- `https://sidira.ai` and `https://app.sidira.ai` still load from Amplify.
- API calls through `https://api.sidira.ai` fail because Caddy cannot reach the
  stopped API container.
- No Sidira request path can trigger provider calls while `sidira-api` is
  stopped.

Stronger options:

- Stop EC2 instance `i-04b155fafcc90042b` from the EC2 console when the whole
  backend host should be offline.
- Rotate or revoke `/sidira/prod/GROQ_API_KEY` in Parameter Store when a key may
  have been exposed outside AWS-managed secret storage.
- Remove or blank `/sidira/prod/GROQ_API_KEY` and redeploy if the backend should
  stay up without Groq-backed simulation capability.

## GitHub Metadata Checklist

- Rename the GitHub Project title from Pythia to Sidira.
- Update repo descriptions to use Sidira.
- Simulator repo is renamed to `sidira-simulator`.
- Producer repo names remain `pythia-personas` and `pythia-crawler` until their packages are renamed intentionally.

## Rollback Notes

- GitHub repo renames create redirects, but local clones should still run:
  `git remote set-url origin git@github.com-personal:ram-de/sidira-simulator.git`.
- Keep the temporary `pythia-simulator` CLI alias and `PYTHIA_*` env fallbacks until after the first Sidira deployment has soaked.
- Revert frontend API routing locally with
  `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`; only use a direct production API
  base if the backend/Caddy internal-key gate is also disabled.
- Revert backend CORS by restoring the previous `SIDIRA_CORS_ORIGINS` deploy value.

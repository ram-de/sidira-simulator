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
- `GET https://api.sidira.ai/models` currently returns no configured models
  because provider API keys have not been stored on the instance yet. The
  frontend renders this state without a fetch error.

## Deploy Environment

Frontend:

```bash
NEXT_PUBLIC_API_BASE=https://api.sidira.ai
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
| Database | Neon Postgres for now | Keep the existing `DATABASE_URL`; move later only if AWS consolidation becomes valuable. |
| Artifacts | Cloudflare R2 for now | Keep the existing artifact contract; switching storage is a separate migration. |

Do not use AWS App Runner for the first deployment unless the AWS account already
has App Runner access. AWS now says App Runner is no longer open to new
customers, so Lightsail Containers is the lower-friction AWS-native backend path
for a new personal account only after we have a clean image-publishing path. If
we are avoiding local AWS CLI profiles, start with a small EC2 instance instead
so the server can use an IAM role to read only Sidira production secrets.

## Secrets And Credentials

Keep production secrets out of GitHub, Amplify frontend variables, user-data,
PR bodies, and docs. Amplify should only receive public frontend config:
`NEXT_PUBLIC_API_BASE=https://api.sidira.ai`.

Store backend secrets under `/sidira/prod/*` in AWS-managed secret storage:

```bash
/sidira/prod/GROQ_API_KEY
/sidira/prod/ANTHROPIC_API_KEY
/sidira/prod/OPENAI_API_KEY
/sidira/prod/DATABASE_URL
/sidira/prod/R2_BUCKET
/sidira/prod/R2_ENDPOINT_URL
/sidira/prod/R2_ACCESS_KEY_ID
/sidira/prod/R2_SECRET_ACCESS_KEY
/sidira/prod/SIDIRA_LOCAL_CRED_KEY
```

Use Parameter Store `SecureString` for lightweight provider/R2 keys. Use
Secrets Manager for credentials where rotation/lifecycle management matters,
especially database credentials. The EC2 instance role should have least-
privilege access to read only the Sidira production paths and decrypt only the
matching KMS key.

Current production bootstrap status:

- IAM role `SidiraApiProdRole` is attached to the EC2 instance through
  instance profile `SidiraApiProdProfile`.
- The role can read `/sidira/prod/*` Parameter Store paths and decrypt matching
  SSM SecureString values through the AWS-managed SSM/KMS path.
- Provider keys are not configured yet. Add at least
  `/sidira/prod/GROQ_API_KEY` before expecting live model-backed simulations.
- The first EC2 deployment uses `/opt/sidira/api.env` generated on the instance.
  The branch now includes `deploy/ec2-api-deploy.sh` to replace the manual
  bootstrap with a repeatable deploy/start script that reads approved
  `/sidira/prod/*` parameters at deploy time.

## Local vs Production Config

Local development stays file-backed and points the browser at the local API:

```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000

# backend/.env
SIDIRA_CUSTOMER_ID=demo
SIDIRA_LOCAL_ARTIFACTS=../local-artifacts
SIDIRA_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SIDIRA_CRED_MODE=local
```

Production config belongs in AWS-managed environment variables, not committed
files:

```bash
# Amplify environment variable
NEXT_PUBLIC_API_BASE=https://api.sidira.ai

# EC2/Docker environment variables
SIDIRA_CUSTOMER_ID=streamly_sample
SIDIRA_CORS_ORIGINS=https://sidira.ai,https://app.sidira.ai
SIDIRA_LOCAL_ARTIFACTS=/app/local-artifacts
DATABASE_URL=<neon pooled postgres url>
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
- Set `NEXT_PUBLIC_API_BASE=https://api.sidira.ai`. Done.
- Let Amplify use the root `amplify.yml`. Done.
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
- Clone `ram-de/sidira-simulator`, build `backend/Dockerfile`, and run
  `sidira-api` plus `sidira-caddy` Docker containers. Done.
- Create `/opt/sidira/api.env` on the instance with the backend environment
  variables listed above, loaded from AWS-managed secrets. Partially done:
  current file is instance-local and excludes provider keys. Branch now includes
  `deploy/ec2-api-deploy.sh` for the repeatable version.
- From the repo root on the instance, run the API image behind Caddy. Done with
  the current branch image; next deploy should use
  `sudo SIDIRA_DEPLOY_BRANCH=main ./deploy/ec2-api-deploy.sh` after #115
  merges and provider keys are in Parameter Store.
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
- Verify the frontend can call the API without a CORS failure from
  `https://sidira.ai` and `https://app.sidira.ai`. Done for
  `https://sidira.ai/simulations/new`; capabilities load and no console errors
  were observed.

## GitHub Metadata Checklist

- Rename the GitHub Project title from Pythia to Sidira.
- Update repo descriptions to use Sidira.
- Simulator repo is renamed to `sidira-simulator`.
- Producer repo names remain `pythia-personas` and `pythia-crawler` until their packages are renamed intentionally.

## Rollback Notes

- GitHub repo renames create redirects, but local clones should still run:
  `git remote set-url origin git@github.com-personal:ram-de/sidira-simulator.git`.
- Keep the temporary `pythia-simulator` CLI alias and `PYTHIA_*` env fallbacks until after the first Sidira deployment has soaked.
- Revert frontend API routing by setting `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000` locally or to the prior backend URL in production.
- Revert backend CORS by restoring the previous `SIDIRA_CORS_ORIGINS` deploy value.

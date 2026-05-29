# Sidira Domain and Metadata Runbook

Canonical Phase 4.7 hostnames:

| Surface | Hostname | Purpose |
|---|---|---|
| Marketing/root | `sidira.ai` | Public entry point. Can redirect to the app while marketing is not live. |
| Frontend app | `app.sidira.ai` | Next.js customer-facing simulator. |
| Backend API | `api.sidira.ai` | FastAPI service consumed by the frontend. |

## Current Audit (2026-05-28)

- `sidira.ai` is added to Amplify custom domains and now returns CloudFront A
  answers via Route 53.
- `app.sidira.ai` is added to Amplify custom domains and now returns a
  CloudFront-backed DNS answer.
- `api.sidira.ai` has no DNS answer yet.
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
  managed certificate. The root and `app` hostnames are both mapped to
  `codex/115-sidira-domain-metadata`.
- HTTPS smoke checks returned HTTP 200 for `https://app.sidira.ai` with normal
  resolution and for `https://sidira.ai` when pointed at the freshly resolved
  CloudFront target; local resolver cache may lag the public apex DNS answer
  for a short period.
- GitHub Project #1 is titled Sidira.
- The simulator repo is renamed to `ram-de/sidira-simulator`; local `origin` should point to `git@github.com-personal:ram-de/sidira-simulator.git`.
- `pythia-personas` and `pythia-crawler` descriptions/homepages use Sidira metadata, but their repo/package names remain unchanged until producer rename work is explicitly scheduled.

## Deploy Environment

Frontend:

```bash
NEXT_PUBLIC_API_BASE=https://api.sidira.ai
```

Backend:

```bash
SIDIRA_CORS_ORIGINS=https://sidira.ai,https://app.sidira.ai
```

Keep local development on `http://127.0.0.1:3000` and `http://127.0.0.1:8000`.

## Recommended AWS Shape

Use this as the first production topology:

| Surface | AWS service | Notes |
|---|---|---|
| DNS | Route 53 hosted zone for `sidira.ai` | Keep Namecheap as registrar; replace Namecheap nameservers with the four Route 53 nameservers. |
| Frontend | AWS Amplify Hosting | Deploys `frontend/` from GitHub using the root `amplify.yml`. Add custom domains `sidira.ai` and `app.sidira.ai`. |
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
SIDIRA_CUSTOMER_ID=demo
SIDIRA_CORS_ORIGINS=https://sidira.ai,https://app.sidira.ai
DATABASE_URL=<neon pooled postgres url>
GROQ_API_KEY=<from secrets manager / console env>
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
- Add custom domains `sidira.ai` and `app.sidira.ai`; let Amplify create or show
  the required DNS records in Route 53. Done; Amplify reports the custom domain
  as available.

Backend API EC2 VM:

- Create an IAM role named `SidiraApiProdRole` with read access only to
  `/sidira/prod/*` secret paths and the matching KMS decrypt permission.
- Create a small EC2 instance from the AWS Console and attach
  `SidiraApiProdRole` as the instance profile.
- Attach an Elastic IP.
- Add an `A` record for `api.sidira.ai` pointing to that IP.
- Open inbound ports `22`, `80`, and `443`.
- Use the AWS browser SSH console to install Docker and clone
  `ram-de/sidira-simulator`.
- Create `/opt/sidira/api.env` on the instance with the backend environment
  variables listed above, loaded from AWS-managed secrets. Do not commit this
  file and do not put secrets in EC2 user-data.
- From the repo root on the instance, run:
  `docker compose -f deploy/docker-compose.api.yml up -d --build`.
- If validating compose before the production env file exists, set
  `SIDIRA_API_ENV_FILE` to a temporary env file path.
- Verify `https://api.sidira.ai/health` returns `{"status":"ok"}`.

## DNS And HTTPS Checklist

- Point `sidira.ai` at the chosen frontend/edge provider. Done via Amplify /
  CloudFront.
- Point `app.sidira.ai` at the Next.js deployment. Done via Amplify /
  CloudFront.
- Point `api.sidira.ai` at the FastAPI deployment.
- Enable provider-managed HTTPS certificates for all three names. Done for
  `sidira.ai` and `app.sidira.ai` through Amplify managed certificates; still
  needed for `api.sidira.ai`.
- Verify `GET https://api.sidira.ai/health` returns `{"status":"ok"}`.
- Verify the frontend can call the API without a CORS failure from `https://sidira.ai` and `https://app.sidira.ai`.

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

# Sidira Domain and Metadata Runbook

Canonical Phase 4.7 hostnames:

| Surface | Hostname | Purpose |
|---|---|---|
| Marketing/root | `sidira.ai` | Public entry point. Can redirect to the app while marketing is not live. |
| Frontend app | `app.sidira.ai` | Next.js customer-facing simulator. |
| Backend API | `api.sidira.ai` | FastAPI service consumed by the frontend. |

## Current Audit (2026-05-28)

- `sidira.ai` resolves to `162.255.119.57`, but HTTPS does not currently answer on port 443.
- `app.sidira.ai` has no DNS answer yet.
- `api.sidira.ai` has no DNS answer yet.
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

# Lightsail container environment variables
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

- Create a public hosted zone for `sidira.ai`.
- Copy the four NS values from the hosted zone.
- In Namecheap, set Domain > Nameservers to Custom DNS and paste the four Route
  53 nameservers.
- Expect DNS propagation to take minutes to hours; keep checking with
  `dig NS sidira.ai`.

Amplify Hosting:

- Create an Amplify app from GitHub repo `ram-de/sidira-simulator`.
- Select the branch to deploy (`main` for production).
- Mark it as a monorepo app with app root `frontend`.
- Confirm environment variable `AMPLIFY_MONOREPO_APP_ROOT=frontend`.
- Set `NEXT_PUBLIC_API_BASE=https://api.sidira.ai`.
- Let Amplify use the root `amplify.yml`.
- Add custom domains `sidira.ai` and `app.sidira.ai`; let Amplify create or show
  the required DNS records in Route 53.

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

- Point `sidira.ai` at the chosen frontend/edge provider.
- Point `app.sidira.ai` at the Next.js deployment.
- Point `api.sidira.ai` at the FastAPI deployment.
- Enable provider-managed HTTPS certificates for all three names.
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

# F&F validation game — LIVE deployment (ops record)

Provisioned 2026-06-19 via AWS CLI. **URL: https://play.sidira.ai** (live, valid Let's Encrypt TLS).
App repo: `ram-de/sidira-ff-game`. Account 897729137726, region us-east-1. All resources tagged
`project=ff-validation-game`.

## Resources
| thing | id |
|---|---|
| EC2 (t4g.small, AL2023 arm64, IMDSv2-only) | `i-07d2a5b4c5f2ff946` |
| Public IP | `13.222.172.200` |
| Hostname (Route53 A in sidira.ai zone) | `play.sidira.ai` |
| Security group (80/443 only) | `sg-0bb02bd0bf2af2919` |
| Durable data volume (10 GB gp3, /data, DeleteOnTermination=false) | attached `/dev/sdf` → `/dev/nvme1n1` |
| SSM role + instance profile (remote access, no inbound SSH) | `ff-validation-game-ssm` |
| Deploy mechanism | cloud-init: clone via read-only deploy key → npm build → systemd `ff-game` + `caddy` |

**Verified in prod:** HTTPS+valid cert, SPA 200, `/healthz` 200, fresh players get a server-assigned
arm (never leaked to client), `ff-game`+`caddy` active, `/data` mounted, **two-table firewall holds**
(`player_features` has NO arm/outcome/task_id). Cost ~$12/mo (~$4 with a 1-yr savings plan).

## ⚠️ BEFORE the real run — reset test data
The DB currently has ~9 feature / 5 outcome rows from provisioning smoke-tests. Wipe them so they
don't pollute the real pack (SSM, no SSH needed):
```
aws ssm send-command --instance-ids i-07d2a5b4c5f2ff946 --document-name AWS-RunShellScript \
  --parameters 'commands=["systemctl stop ff-game","rm -f /data/ff.db /data/ff.db-wal /data/ff.db-shm","systemctl start ff-game"]'
```

## Data-pull (after recruitment) — pull the de-identified features + sealed outcomes
Run the export ON the box, then base64 the CSVs out (DB is small). The de-identified
`player_features.csv` is the ONLY thing `run_pipeline` sees; `player_outcomes.csv` stays sealed.
```
# 1) export on the box
aws ssm send-command --instance-ids i-07d2a5b4c5f2ff946 --document-name AWS-RunShellScript \
  --parameters 'commands=["cd /opt/ff-validation-game && node scripts/export_features.js /data/ff.db /tmp/out && ls -l /tmp/out"]'
# 2) retrieve (base64 via a second send-command per file, or scp over SSM start-session w/ the session-manager-plugin)
```
Then the SEALED ROLE-SEPARATED validation: rebuild the pack from `player_features.csv` via
`run_pipeline(friends_family.yaml, require_llm=True)` (the synthetic seal-guard won't trip — the
real pack isn't marked synthetic); engine-runner seals `harness/predict.py`; a DIFFERENT person runs
`harness/score.py` and verifies the pack-SHA → GO/NO-GO.

## Teardown (one pass — all by tag)
```
aws ec2 terminate-instances --instance-ids i-07d2a5b4c5f2ff946
# /data volume has DeleteOnTermination=false → delete it explicitly after the instance is gone:
aws ec2 delete-volume --volume-id <the /data vol>   # find via: ec2 describe-volumes --filters Name=tag:project,Values=ff-validation-game
aws route53 change-resource-record-sets ... DELETE play.sidira.ai A 13.222.172.200   # zone Z01279103CLJX7PS4TEFN
aws ec2 delete-security-group --group-id sg-0bb02bd0bf2af2919
aws iam remove-role-from-instance-profile --instance-profile-name ff-validation-game-ssm --role-name ff-validation-game-ssm
aws iam delete-instance-profile --instance-profile-name ff-validation-game-ssm
aws iam detach-role-policy --role-name ff-validation-game-ssm --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam delete-role --role-name ff-validation-game-ssm
gh repo deploy-key delete <id> --repo ram-de/sidira-ff-game
```

## Updating the app
Push to `ram-de/sidira-ff-game` main, then SSM: `cd /opt/ff-validation-game && git pull && npm install && npm run build && systemctl restart ff-game`.

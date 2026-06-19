# DEPLOY — ff-validation-game (Split The Loot)

AWS-minimal production deploy: **one small EC2** (`t4g.small`, Amazon Linux
2023, arm64) running the Express app with **SQLite on a durable EBS volume**,
fronted by **CloudFront + ACM TLS**. No load balancer, no RDS, no container
orchestrator — this is a friends-&-family validation game, sized accordingly.

This runbook is deploy-READY: it does **not** provision live infra (that needs
the founder's AWS creds + billing + console). Run the steps with founder creds.

```
Internet ──HTTPS──▶ CloudFront (ACM cert, TLS) ──HTTPS──▶ EC2 t4g.small
                                                            │ Node + systemd
                                                            │ Express :5180
                                                            └─ SQLite on /data (EBS gp3)
```

The app serves the built `dist/` SPA **and** the API on one port (`5180`) in
`NODE_ENV=production`. CloudFront terminates TLS and proxies to the origin.

---

## 0. Prerequisites

- AWS account with the AWS CLI configured (`aws sts get-caller-identity` works).
- A domain you control (for the TLS cert + CloudFront alias), e.g. `game.sidira.ai`.
- An EC2 key pair for SSH.
- Region: pick one near your players (examples use `ap-south-1`).

You can provision the EC2 + EBS + SG two ways:
- **CloudFormation** (fast): `deploy/infra.cfn.yaml` (steps inline in §2 below), or
- **CLI** (explicit): the `aws ec2` commands in §2-ALT.

CloudFront + ACM (§5) are always done separately (cross-region cert + DNS).

---

## 1. Estimated monthly cost (~$10–15)

| Item | Spec | Est. / mo (ap-south-1, on-demand) |
|------|------|-----------------------------------|
| EC2 `t4g.small` | 2 vCPU arm64, 2 GB, 24/7 | ~$12 |
| EBS gp3 data volume | 8 GB | ~$0.70 |
| EBS snapshots | ~8 GB churned, daily | ~$0.40 |
| CloudFront | F&F traffic, <1 GB egress | ~$0–1 (often free tier) |
| ACM cert | public cert | $0 |
| Route 53 (if used) | 1 hosted zone | ~$0.50 |
| **Total** | | **~$11–15 / mo** |

Drop to **~$4/mo** with a 1-year `t4g.small` reserved/savings plan if this
runs long. A `t4g.micro` (1 GB) also works for tiny N but leaves no headroom
for the build — keep `small`.

---

## 2. Provision EC2 + EBS + SG (CloudFormation)

```bash
aws cloudformation deploy \
  --region ap-south-1 \
  --template-file deploy/infra.cfn.yaml \
  --stack-name ff-validation-game \
  --parameter-overrides \
      KeyName=YOUR_KEYPAIR \
      SshCidr=$(curl -s https://checkip.amazonaws.com)/32 \
      VpcId=vpc-xxxx \
      SubnetId=subnet-xxxx \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation describe-stacks --stack-name ff-validation-game \
  --region ap-south-1 --query 'Stacks[0].Outputs'
```

Note the `PublicDns` output (the CloudFront origin) and `InstanceId`. The EBS
data volume is **attached but not formatted** — that's the one-time §3 step
(formatting in automation risks wiping data on instance replace).

### 2-ALT. Provision via CLI (instead of CloudFormation)

```bash
# Security group: 443 from anywhere (CloudFront), SSH from your IP only.
SG=$(aws ec2 create-security-group --group-name ff-game --description "ff-game" \
       --vpc-id vpc-xxxx --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $SG \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG \
  --protocol tcp --port 22 --cidr $(curl -s https://checkip.amazonaws.com)/32

# Latest AL2023 arm64 AMI via SSM public parameter.
AMI=$(aws ssm get-parameter \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 \
  --query Parameter.Value --output text)

# Instance.
IID=$(aws ec2 run-instances --image-id $AMI --instance-type t4g.small \
  --key-name YOUR_KEYPAIR --security-group-ids $SG --subnet-id subnet-xxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ff-validation-game}]' \
  --query 'Instances[0].InstanceId' --output text)

# 8 GB gp3 data volume, attached as /dev/sdf (mounted in §3).
AZ=$(aws ec2 describe-instances --instance-ids $IID \
  --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' --output text)
VOL=$(aws ec2 create-volume --size 8 --volume-type gp3 --availability-zone $AZ \
  --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=ff-validation-game-data}]' \
  --query VolumeId --output text)
aws ec2 wait volume-available --volume-ids $VOL
aws ec2 attach-volume --instance-id $IID --volume-id $VOL --device /dev/sdf
```

---

## 3. One-time host setup (SSH in)

```bash
ssh -i YOUR_KEY.pem ec2-user@<PublicDns>
```

```bash
# --- Format + mount the EBS data volume at /data (ONE TIME ONLY) -----------
# The attached device shows up as a /dev/nvme*n1 device (NOT the root volume).
lsblk                                  # identify the 8 GB device, e.g. nvme1n1
DEV=/dev/nvme1n1
# Only run mkfs if the volume is BLANK — `blkid $DEV` must print nothing first,
# or you will WIPE existing data on a reattached volume.
sudo blkid $DEV || sudo mkfs -t xfs $DEV
sudo mkdir -p /data
# Persistent mount by UUID so a device-name change across reboots can't break it.
UUID=$(sudo blkid -s UUID -o value $DEV)
echo "UUID=$UUID /data xfs defaults,nofail 0 2" | sudo tee -a /etc/fstab
sudo mount -a
df -h /data                            # confirm mounted

# --- Service user + Node 20 (arm64) ----------------------------------------
sudo useradd --system --create-home --shell /usr/sbin/nologin appuser || true
sudo chown appuser:appuser /data
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs git

# --- App code ---------------------------------------------------------------
sudo mkdir -p /opt/ff-validation-game
sudo chown appuser:appuser /opt/ff-validation-game
sudo -u appuser git clone https://github.com/<org>/sidira-simulator.git /opt/ff-validation-game

# --- Env file + systemd unit ------------------------------------------------
APP=/opt/ff-validation-game/sessions/ff-validation-game/app
sudo cp $APP/deploy/.env.example /etc/ff-validation-game.env   # edit if needed
sudo cp $APP/deploy/ff-validation-game.service /etc/systemd/system/

# better-sqlite3 is a native arm64 module — first build needs the toolchain.
sudo dnf install -y gcc-c++ make python3
```

> The systemd unit's `WorkingDirectory=/opt/ff-validation-game` plus
> `ExecStart=/usr/bin/node server/index.js` assume the app's `server/` is
> reachable from there. Since the app lives in `sessions/ff-validation-game/app/`,
> either set `WorkingDirectory` to that subdir in the unit, or symlink it:
> `sudo ln -s sessions/ff-validation-game/app/server /opt/ff-validation-game/server`
> and `... /node_modules` / `dist`. Simplest: edit the unit's `WorkingDirectory`
> to the `app` subdir. Pick one and keep it consistent with `deploy.sh`.

---

## 4. First build + start

```bash
cd $APP
sudo -u appuser npm ci
sudo -u appuser npm run build
sudo systemctl daemon-reload
sudo systemctl enable --now ff-validation-game

# Verify the origin is healthy.
curl -fsS http://127.0.0.1:5180/healthz   # -> {"ok":true}
journalctl -u ff-validation-game -n 30
```

Steady-state redeploys (after first setup) are one command:

```bash
sudo /opt/ff-validation-game/sessions/ff-validation-game/app/deploy/deploy.sh
```

`deploy.sh` pulls `origin/main`, `npm ci`, builds, lint-checks, restarts the
service (graceful SIGTERM → WAL checkpoint on the old PID), and polls `/healthz`.

---

## 5. CloudFront + ACM TLS + DNS

**5a. Request the cert (ACM, us-east-1 — CloudFront requires us-east-1):**
```bash
aws acm request-certificate --region us-east-1 \
  --domain-name game.sidira.ai --validation-method DNS \
  --query CertificateArn --output text
# Then add the CNAME validation record ACM gives you to your DNS, and wait for
# the cert to reach status ISSUED:
aws acm describe-certificate --region us-east-1 --certificate-arn <ARN> \
  --query 'Certificate.Status'
```

**5b. Create the CloudFront distribution:**
- **Origin:** the EC2 `PublicDns` from §2, origin protocol **HTTPS only**
  (or HTTP if you don't run TLS on the origin — see note below), origin port
  matching how you expose the app.
- **Viewer protocol policy:** Redirect HTTP → HTTPS.
- **Alternate domain (CNAME):** `game.sidira.ai`.
- **Custom SSL cert:** the ACM ARN from 5a.
- **Allowed methods:** GET, HEAD, OPTIONS, **POST, PUT, PATCH, DELETE** (the
  `/api/*` writes are POSTs — without these CloudFront blocks them).
- **Cache policy:** `CachingDisabled` for `/api/*` and `/healthz`; default
  caching for static assets (the app already sets `immutable` on hashed assets
  and `no-cache` on `index.html`).
- **Origin health check:** path `/healthz` (200 = healthy).

> **Origin TLS note:** the SG opens **443** to the origin, so the cleanest setup
> is TLS at the origin too. Easiest path on a single box: run **Caddy** or
> **nginx** on the EC2 listening on 443 with its own cert (Caddy auto-provisions
> via Let's Encrypt) and reverse-proxying to `127.0.0.1:5180`. Alternatively,
> set the SG/origin to port 80 (HTTP) and have CloudFront use HTTP to the origin
> — acceptable for F&F since CloudFront still serves viewers over HTTPS, but the
> origin hop is then unencrypted. The app itself does not terminate TLS.

**5c. DNS:** point `game.sidira.ai` (CNAME / Route 53 ALIAS) at the CloudFront
distribution domain (`dxxxx.cloudfront.net`).

**5d. Verify end-to-end:**
```bash
curl -fsS https://game.sidira.ai/healthz       # -> {"ok":true}
curl -fsS 'https://game.sidira.ai/api/session'  # -> mints a token + config JSON
```

---

## 6. Backups (EBS snapshots) + pulling the SQLite file

### Automated daily snapshots (AWS Backup / DLM)
Create a Data Lifecycle Manager policy on the data volume tag
`Name=ff-validation-game-data`:
```bash
# Simplest: AWS Backup plan with a daily rule + 7-day retention on the volume.
# Or a DLM snapshot lifecycle policy: daily at a quiet hour, retain 7.
```
WAL + `synchronous=NORMAL` means a snapshot taken live is crash-consistent;
SQLite recovers cleanly on next open. For a *guaranteed* clean point-in-time
snapshot, briefly stop the service first (`systemctl stop ff-validation-game`,
snapshot, `start`) — the graceful stop checkpoints the WAL into `ff.db`.

### Pull the SQLite file for the offline `run_pipeline` export
The feature export (`scripts/export_features.js`) is run **offline / locally**
to preserve the role separation (the engine operator must not open the sealed
answer key). Pull the DB file, then export locally:
```bash
# On the box, checkpoint so ff.db is self-contained, then copy it down.
sudo systemctl stop ff-validation-game      # graceful → WAL folded into ff.db
scp -i YOUR_KEY.pem ec2-user@<PublicDns>:/data/ff.db ./ff.db
sudo systemctl start ff-validation-game

# Locally, run the firewalled export (Table A and Table B → two separate CSVs).
FF_DB_PATH=./ff.db npm run export:features
# -> exports/player_features.csv  (PRE-TREATMENT only — the run_pipeline input)
# -> exports/player_outcomes.csv  (SEALED answer key — do NOT feed to the engine)
```
> The `payout_contacts` table (PII) is **never** touched by the export — keep it
> that way.

---

## 7. Operations cheatsheet

```bash
sudo systemctl status ff-validation-game        # is it up?
journalctl -u ff-validation-game -f             # tail logs
sudo systemctl restart ff-validation-game       # graceful restart (checkpoints WAL)
curl -fsS http://127.0.0.1:5180/healthz         # origin liveness
```

**Rollback:** `cd $APP && sudo -u appuser git reset --hard <good-sha> && \
sudo $APP/deploy/deploy.sh --no-pull`.

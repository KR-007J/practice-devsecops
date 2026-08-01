# practice-devsecops


# Practice DevSecOps — Month 1: Linux Security Toolkit

A Linux hardening and auditing toolkit combining a Python security scanner with a Bash hardening script, validated using Lynis before/after benchmarking.

---

## What This Project Demonstrates

- Practical Linux security auditing (SUID binaries, world-writable files, privileged accounts)
- Automated system hardening (SSH configuration, firewall rules)
- Measurable security improvement using an industry-standard benchmarking tool (Lynis)
- Comfort with file permissions, user/group management, and shell scripting

---

## Project Structure

```
month1-toolkit/
├── audit.py              # Python script: finds security misconfigurations, outputs JSON
├── harden.sh              # Bash script: hardens SSH + basic firewall rules
├── lynis-before.txt        # Lynis scan output before hardening
├── lynis-after.txt         # Lynis scan output after hardening
├── README.md
```

*(Adjust file names above to match your actual filenames.)*

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3 | Audit script — finds SUID binaries, world-writable files, UID=0 accounts |
| Bash | Hardening script — SSH config, firewall rules |
| Lynis | Security benchmarking — before/after scoring |
| Linux (CachyOS / Arch-based) | Target OS for hardening |

---

## What the Audit Script Checks

| Check | Why it matters |
|---|---|
| SUID/SGID binaries | Programs that run with owner's (often root) privileges — common privilege escalation vector if misconfigured or outdated |
| World-writable files | Any user can modify these — risk of tampering, backdoor insertion |
| UID=0 accounts | Multiple accounts with root privileges (UID 0) beyond the default `root` user — hidden backdoor accounts |

Output format: structured JSON, so results can be parsed, diffed over time, or fed into other tooling — not just a human-readable printout.

---

## What the Hardening Script Does

- **SSH hardening**: disables root login, disables password authentication (key-only), changes default port if configured, restricts allowed users
- **Basic firewall rules**: default-deny inbound, explicit allow rules for required services only

Run in a single pass, idempotent where possible (safe to re-run without breaking existing config).

---

## Results

**Lynis hardening index — before vs after:**

| Metric | Before | After |
|---|---|---|
| Lynis hardening index | *(fill in your before score)* | *(fill in your after score)* |
| Warnings | *(fill in)* | *(fill in)* |
| Suggestions | *(fill in)* | *(fill in)* |

*(Run `lynis audit system` before and after hardening, screenshot or save the output, and fill in the real numbers here — this comparison is the single most convincing part of this project for reviewers.)*

---

## How to Run

```bash
git clone https://github.com/KR-007J/practice-devsecops.git
cd practice-devsecops/month1-toolkit

# Run the audit (read-only, safe to run anytime)
python3 audit.py

# Review findings, then run hardening (modifies system config — review harden.sh first)
sudo bash harden.sh

# Verify improvement
sudo lynis audit system
```

⚠️ **Run `harden.sh` only on a VM or disposable environment first** — it modifies SSH and firewall configuration and could lock you out if misconfigured.

---

## Key Security Decisions (and Why)

### 1. JSON output instead of plain text
Structured output means the audit results can be version-controlled, diffed between runs, or piped into other tools (e.g., a future CI pipeline stage) — not just read once and discarded.

### 2. Separating audit (read-only) from hardening (system-modifying)
The audit script never changes anything — it only reports. The hardening script is a separate, explicit step. This separation means you can safely run the audit repeatedly (e.g., in a cron job or CI check) without any risk of accidentally modifying a system.

### 3. Using Lynis for validation instead of just "trust me"
Anyone can claim a script "hardens" a system. Lynis gives an objective, third-party-validated hardening score — the before/after comparison is proof, not a claim.

---

## What I'd Add With More Time

- Convert the audit script into a scheduled check (cron or systemd timer) with alerting on drift
- Add automated remediation suggestions with severity ranking
- Extend checks to include: unnecessary running services, weak file permissions on sensitive config files (`/etc/shadow`, `/etc/ssh/sshd_config`), unpatched packages
- Package as a CLI tool with proper argument parsing (`argparse`) instead of a single-run script

---

## Interview Q&A

**Q: Walk me through this project.**
A: It's a two-part Linux hardening toolkit. A Python script audits the system read-only — checking for SUID/SGID binaries, world-writable files, and unexpected UID=0 accounts — and outputs structured JSON. A separate Bash script then hardens SSH configuration and applies basic firewall rules. I validated the improvement using Lynis, a standard Linux security auditing tool, comparing the hardening index before and after.

**Q: Why check for SUID/SGID binaries specifically?**
A: SUID binaries run with the file owner's privileges rather than the executing user's — if owned by root, any user executing that binary temporarily gains root-level capability for that program. Outdated or misconfigured SUID binaries are a classic privilege escalation vector, so auditing which binaries have this bit set is a standard first step in a Linux security review.

**Q: Why separate the audit script from the hardening script instead of combining them?**
A: Separation of concerns and safety. The audit is read-only and idempotent — safe to run anytime, even repeatedly, with zero risk. The hardening script modifies system state (SSH config, firewall), which is a higher-risk, one-directional action. Keeping them separate means you can audit as often as you want without ever accidentally changing something, and the hardening step is a deliberate, reviewable action.

**Q: What's the risk with world-writable files?**
A: Any local user — or, worse, a compromised low-privilege process — can modify a world-writable file. If that file is a script that later gets executed with higher privileges, a cron job, or a config file read by a privileged service, it becomes a path to tampering or privilege escalation. Auditing for these files surfaces configuration drift or misconfigurations that are easy to introduce accidentally.

**Q: Why did you use Lynis instead of just describing what your script does?**
A: Because a third-party, widely-used benchmarking tool gives an objective before/after score rather than a self-reported claim. Anyone reviewing this project can independently verify the improvement is real, not just take my word for it — that's the difference between "I wrote a hardening script" and "I improved this measurable security posture."

**Q: What would you change before running this in production?**
A: I'd add logging and alerting so audit findings don't just sit in a JSON file — they'd feed into a monitoring system. I'd also make the hardening script strictly idempotent and add a dry-run mode, since blindly re-applying firewall or SSH changes without checking current state risks lockouts. And I'd test extensively on a disposable VM before ever running it against a real system, which is exactly how I approached it here.

**Q: What's the difference between SUID and SGID?**
A: SUID (Set User ID) makes a program run with the file owner's user privileges. SGID (Set Group ID) makes it run with the file's group privileges instead — or, on a directory, makes new files inside inherit the directory's group rather than the creating user's primary group. Both are legitimate mechanisms (e.g., `passwd` needs SUID root to modify `/etc/shadow`), but unnecessary or misconfigured SUID/SGID bits are a common audit finding.

---

## Author

Krish Joshi — B.Tech CSE (Cybersecurity), building toward a DevSecOps career.





# Practice DevSecOps — Month 2: Docker + CI/CD Security Pipeline

A hardened, containerized Flask application with an automated GitHub Actions security pipeline that scans code, builds, and dependencies on every push — and **fails the build** if a critical issue is found.

---

## What This Project Demonstrates

- Secure Docker image construction (non-root user, minimal Alpine base)
- Automated vulnerability scanning integrated into CI/CD
- Static code analysis (SAST) for Python
- Secret-leak detection in git history
- Matrix builds, dependency caching, and secrets management in GitHub Actions

---

## Architecture

```
Push to GitHub
      │
      ▼
┌─────────────────────────────────────────────┐
│  GitHub Actions: Security Pipeline           │
│                                               │
│  1. Checkout code                            │
│  2. Set up Python (matrix: 3.11, 3.12)       │
│  3. Cache pip dependencies                   │
│  4. Bandit  → static code security scan      │
│  5. Docker build → containerize app          │
│  6. Trivy   → image vulnerability scan       │
│              (blocks on CRITICAL/HIGH)       │
│  7. Gitleaks → secret leak scan              │
│                                               │
└─────────────────────────────────────────────┘
      │
      ▼
Pass → merge safely   |   Fail → build blocked
```

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| App | Flask 3.1.3 | Minimal Python web app |
| Container | Docker (Alpine base) | Lightweight, minimal attack surface |
| SAST | Bandit | Finds insecure Python code patterns |
| Image scanning | Trivy | Finds CVEs in OS packages + dependencies |
| Secret scanning | Gitleaks | Finds leaked credentials in git history |
| CI/CD | GitHub Actions | Automates the entire pipeline on every push |

---

## Project Structure

```
month2-app/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies (pinned versions)
├── dockerfile              # Multi-stage-aware, non-root container build
├── .gitignore
├── trivy-scan-result.txt   # Saved scan evidence
├── .github/
│   └── workflows/
│       └── pipeline.yml    # CI/CD security pipeline definition
└── README.md
```

---

## Key Security Decisions (and Why)

### 1. Alpine base image instead of Debian-slim
**Before:** `python:3.12-slim` → 171 total vulnerabilities (4 CRITICAL, 19 HIGH)
**After:** `python:3.12-alpine` → 0 CRITICAL, 0 HIGH

Debian-slim ships a full userland (bash, perl, util-linux, systemd libraries) that a Flask app never touches, but which Trivy still scans and flags. Alpine's minimal package set (~38 packages vs ~87+) drastically cuts the attack surface.

### 2. Non-root container user
The container runs as `appuser`, not `root`. If the app is ever compromised (e.g., via a dependency vulnerability), the attacker doesn't automatically get root inside the container — reducing blast radius and making container escape harder.

```dockerfile
RUN adduser -D appuser && chown -R appuser:appuser /app
USER appuser
```

### 3. Layer-ordered Dockerfile
`requirements.txt` is copied and installed **before** the rest of the source code. Docker caches each layer — if only `app.py` changes, the dependency-install layer is reused instead of rebuilt, speeding up every subsequent build.

### 4. Documented Bandit suppression, not blind bypass
Bandit flagged `app.run(host="0.0.0.0", ...)` as B104 (binding to all interfaces). This is intentional and required for Docker port-mapping to work — so it's suppressed with a documented reason, not silently ignored:
```python
app.run(host="0.0.0.0", port=5000)  # nosec B104 - required for Docker container networking
```

### 5. Pipeline fails the build on real findings
`trivy-action` is configured with `exit-code: '1'` — any CRITICAL or HIGH vulnerability found in the built image stops the pipeline. This isn't a passive report; it's a hard gate.

---

## Pipeline Stages Explained

| Stage | Tool | What it catches | Fails build? |
|---|---|---|---|
| Checkout | `actions/checkout` | — | — |
| Setup | `actions/setup-python` (matrix) | — | — |
| Cache | `actions/cache` | — (speed optimization) | No |
| SAST | Bandit | Hardcoded secrets, insecure functions, weak crypto, `eval()` use | Yes, on findings |
| Build | `docker build` | — | Yes, on build error |
| Image scan | Trivy | CVEs in OS packages and language dependencies | Yes, on CRITICAL/HIGH |
| Secret scan | Gitleaks | API keys, passwords, tokens committed to git history | Yes, on any secret found |

---

## Results

**Trivy scan — before and after base image change:**

| Metric | Debian-slim | Alpine |
|---|---|---|
| Total vulnerabilities | 171 | 0 |
| CRITICAL | 4 | 0 |
| HIGH | 19 | 0 |
| MEDIUM | 54 | 0 |
| LOW | 66 | 0 |

**Pipeline run time:** ~40-50s across 2 parallel matrix jobs (Python 3.11, 3.12)

---

## How to Run Locally

```bash
git clone https://github.com/KR-007J/practice-devsecops.git
cd practice-devsecops/month2-app

# Build
docker build -t month2-app .

# Run
docker run -d -p 5000:5000 --name m2 month2-app

# Verify non-root
docker exec m2 whoami   # → appuser

# Test
curl http://localhost:5000

# Scan manually
trivy image month2-app
bandit -r . -x ./.git
```

---

## What I'd Add With More Time

- **SBOM generation** (Syft) — full software bill of materials for supply-chain transparency
- **Image signing** (Cosign) — cryptographically verify the image wasn't tampered with post-build
- **SLSA attestation** — provenance tracking for build integrity
- Push built image to a container registry (Docker Hub / GHCR) as a pipeline artifact
- Add automated tests (pytest) as a pipeline stage before the Docker build

---

## Interview Q&A

**Q: Walk me through your CI/CD pipeline.**
A: On every push, GitHub Actions checks out the code, runs Bandit for static security analysis on the Python source, builds the Docker image, scans it with Trivy for CVEs, and runs Gitleaks against git history for leaked secrets. If Trivy finds a CRITICAL or HIGH vulnerability, or Gitleaks finds a secret, the build fails — it's a hard gate, not just a report.

**Q: Why did you switch from python:3.12-slim to python:3.12-alpine?**
A: A Trivy scan on the slim image showed 171 vulnerabilities, mostly in Debian OS packages the app never uses — bash, perl, systemd libraries. Alpine has a much smaller base package set, so switching cut CRITICAL and HIGH findings to zero without changing any app code.

**Q: Why run the container as a non-root user?**
A: Principle of least privilege. If the app has a vulnerability that gets exploited, running as root inside the container means the attacker inherits root privileges in that context, making container escape and lateral movement easier. Running as a dedicated unprivileged user limits the blast radius.

**Q: What's the difference between SAST and image scanning?**
A: SAST (Bandit) analyzes your own source code for insecure patterns before it's even built — hardcoded credentials, unsafe function calls, weak crypto usage. Image scanning (Trivy) looks at the built artifact — the OS packages and third-party dependencies bundled into the container — for known CVEs. They catch different things: SAST catches bugs you wrote, image scanning catches vulnerabilities in what you depend on.

**Q: You suppressed a Bandit finding — isn't that hiding a problem?**
A: No — it's the difference between blind suppression and documented risk acceptance. Bandit flagged binding to 0.0.0.0, which is a real risk on a bare host but is required and safe in a Docker container, since the port is only reachable through Docker's explicit port mapping. I suppressed it with `# nosec B104` plus a comment explaining why, so any reviewer can see the decision was intentional, not overlooked.

**Q: What is a matrix build and why use one?**
A: A matrix build runs the same job multiple times in parallel with different variables — in my case, testing against Python 3.11 and 3.12 simultaneously. It catches version-specific bugs before merge and is faster than running them sequentially, since GitHub Actions runs each combination as a separate parallel job.

**Q: How do you handle secrets in your pipeline?**
A: Never hardcoded in the workflow file or source code. They're stored as encrypted GitHub Actions secrets and referenced via `${{ secrets.NAME }}`, which GitHub automatically masks in logs even if accidentally printed. For example, my Gitleaks step uses the auto-provided `GITHUB_TOKEN` this way.

**Q: What would you add if this were a production pipeline?**
A: SBOM generation with Syft for supply-chain visibility, image signing with Cosign so downstream consumers can verify the image hasn't been tampered with, and pushing the built image to a registry as a versioned artifact. I'd also add automated tests as a gate before the Docker build stage.

**Q: What's the difference between a CVE and a vulnerability severity rating?**
A: A CVE (Common Vulnerabilities and Exposures) is a unique identifier for a specific publicly disclosed security flaw. Severity (LOW/MEDIUM/HIGH/CRITICAL) is typically derived from CVSS scoring and reflects exploitability and impact. My pipeline only blocks on CRITICAL and HIGH because gating on every LOW/MEDIUM finding would create excessive noise and block builds unnecessarily — a practical judgment call about signal versus noise in CI.

**Q: How does Docker layer caching work, and why does instruction order matter in a Dockerfile?**
A: Each instruction in a Dockerfile creates a cached layer. Docker reuses a layer if nothing above it changed. By copying `requirements.txt` and running `pip install` before copying the rest of the source code, changes to application code don't invalidate the dependency-install layer — so rebuilds are much faster since Docker doesn't reinstall unchanged dependencies every time.

---
# Practice DevSecOps — Month 3: Cloud (AWS) + Threat Modeling

Hands-on AWS fundamentals — IAM, VPC networking, and security groups — practiced using LocalStack (a local AWS simulator), paired with a formal STRIDE threat model applied to the Month 2 CI/CD pipeline.

---

## Why LocalStack Instead of Real AWS

Real AWS requires a credit/debit card for signup. To avoid billing risk while still learning genuine AWS mechanics, this project uses **LocalStack** — a Docker container that simulates AWS APIs locally. Every command shown here uses the real `aws` CLI; only the endpoint differs (`http://localhost:4566` instead of AWS's real endpoints). The IAM policy JSON, ARN structure, and VPC/subnet concepts are identical to real AWS and transfer directly.

**Known limitation, stated honestly:** LocalStack's free Community edition stores and returns IAM policies correctly but does not fully enforce policy evaluation on most API calls (that's a Pro-tier feature). This is noted explicitly wherever relevant below — the policy-writing skill is real, the live enforcement testing is a real AWS activity for later.

---

## What This Project Demonstrates

- AWS account security fundamentals (Shared Responsibility Model, root vs IAM)
- Writing correct IAM policy JSON from scratch (Effect/Action/Resource/Condition)
- The difference between IAM Users and IAM Roles, and why roles are preferred for workloads
- Trust policies and the `sts:AssumeRole` mechanism
- VPC design: public vs private subnet separation
- Security Groups vs Network ACLs (stateful vs stateless firewalls)
- Structured threat modeling using STRIDE, applied to a real system

---

## Environment Setup

```bash
# Install AWS CLI
sudo pacman -S aws-cli

# Run LocalStack (pinned to a free community version)
docker run -d --name localstack -p 4566:4566 -p 4510-4559:4510-4559 localstack/localstack:3.8

# Configure CLI (fake credentials work — LocalStack doesn't validate them)
aws configure
# AWS Access Key ID: test
# AWS Secret Access Key: test
# Default region: us-east-1
# Output format: json

# Alias for convenience (add to ~/.config/fish/config.fish)
alias awslocal="aws --endpoint-url=http://localhost:4566"
```

---

## Project Structure

```
month3-aws/
├── s3-readonly-policy.json   # Least-privilege IAM policy (S3 read-only, one bucket)
├── trust-policy.json          # IAM role trust policy (EC2 service principal)
├── README.md
└── (VPC/subnet/security group resources created via CLI, not files)

month2-app/
└── threat-model.md            # STRIDE analysis of the CI/CD pipeline
```

---

## Part 1: IAM — Identity and Access Management

### Core concept: the Shared Responsibility Model

AWS secures the cloud infrastructure (hardware, hypervisor, physical data centers). The customer secures everything *in* the cloud — IAM permissions, network configuration, data encryption, and application security. Most real cloud breaches trace back to customer-side misconfiguration, not AWS infrastructure failure.

### IAM Users vs IAM Roles

| | IAM User | IAM Role |
|---|---|---|
| Credentials | Long-lived (password, access keys) | Temporary (auto-expiring, ~1 hour) |
| Best for | Human operators | Applications, EC2 instances, cross-account access |
| Risk profile | Higher — leaked keys stay valid until manually rotated | Lower — leaked credentials expire quickly |

**Practice:** Created `krish-s3-reader` IAM user with a least-privilege policy granting only `s3:GetObject` and `s3:ListBucket` on a single named bucket — not `AdministratorAccess`.

```bash
awslocal iam create-user --user-name krish-s3-reader
awslocal iam put-user-policy \
  --user-name krish-s3-reader \
  --policy-name S3ReadOnlyAccess \
  --policy-document file://s3-readonly-policy.json
```

### IAM Policy Anatomy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::krish-devsecops-bucket",
        "arn:aws:s3:::krish-devsecops-bucket/*"
      ]
    }
  ]
}
```
Two Resource ARNs are required for S3: the bucket ARN itself (for `ListBucket`) and the wildcard object path (for `GetObject`) — a commonly confused detail.

### Roles and Trust Policies

A role has two documents: a **trust policy** (who can assume it) and a **permission policy** (what it can do once assumed).

```bash
awslocal iam create-role \
  --role-name EC2-S3-ReadOnly-Role \
  --assume-role-policy-document file://trust-policy.json

awslocal iam put-role-policy \
  --role-name EC2-S3-ReadOnly-Role \
  --policy-name S3ReadOnlyAccess \
  --policy-document file://s3-readonly-policy.json
```

**Why roles matter for real workloads:** when an EC2 instance assumes a role, AWS STS issues temporary credentials automatically via the instance metadata service — no hardcoded keys in application code, no manual rotation needed.

---

## Part 2: VPC and Network Security

### VPC hierarchy

```
VPC (10.0.0.0/16)
 ├── Public Subnet (10.0.1.0/24)  → route to internet, hosts web-facing resources
 └── Private Subnet (10.0.2.0/24) → no direct internet route, hosts databases/internal services
```

**Practice:** Built a custom VPC with explicit public/private subnet separation — not relying on the account's auto-created default VPC (which most production security audits flag as a red flag if actively used).

```bash
awslocal ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=krish-devsecops-vpc}]'

awslocal ec2 create-subnet --vpc-id vpc-92739487 --cidr-block 10.0.1.0/24 \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet}]'

awslocal ec2 create-subnet --vpc-id vpc-92739487 --cidr-block 10.0.2.0/24 \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet}]'
```

### Security Groups vs Network ACLs

| | Security Group | Network ACL |
|---|---|---|
| Scope | Per-instance | Per-subnet |
| Statefulness | Stateful (return traffic auto-allowed) | Stateless (explicit rules both ways) |
| Rule types | Allow only | Allow and Deny |

**Practice:** Created a security group allowing inbound HTTPS (443) from anywhere — appropriate for a public web server, but a red flag if applied to SSH (22) or RDP (3389) instead.

```bash
awslocal ec2 create-security-group --group-name web-sg \
  --description "Security group for web servers - HTTPS only" \
  --vpc-id vpc-92739487

awslocal ec2 authorize-security-group-ingress \
  --group-id sg-13150e4eb0666c41d \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

---

## Part 3: Threat Modeling (STRIDE)

Applied Microsoft's STRIDE framework to the Month 2 CI/CD pipeline — see [`threat-model.md`](../month2-app/threat-model.md) for the full document.

| STRIDE Category | Threat Example | Mitigation |
|---|---|---|
| Spoofing | Compromised contributor account pushes malicious code | MFA, branch protection, signed commits |
| Tampering | Malicious dependency or workflow file edit | Pinned versions, PR review on workflow files |
| Repudiation | No record of who approved a risky change | Immutable GitHub Actions audit logs |
| Information Disclosure | Secrets leaked in build logs | Secret masking, Gitleaks scanning |
| Denial of Service | Pipeline resource exhaustion | Branch protection, job timeouts |
| Elevation of Privilege | Compromised dependency gains runner-level access | Trivy/Bandit gating, scoped tokens |

---

## Extra Topics Worth Knowing (Not Deeply Covered Yet, But Real)

These are things that exist in the AWS/cloud security world and will come up in interviews or on the job, even though this month's roadmap deliberately kept scope tight (depth over breadth). Awareness now, depth later:

| Topic | What it is | Why it matters |
|---|---|---|
| **AWS CloudTrail** | Logs every API call made in your account | The audit trail for "who did what, when" — essential for incident response and compliance |
| **AWS Config** | Continuously tracks resource configuration and flags drift from a defined baseline | Used to detect if someone manually changes a security group or IAM policy outside of approved process |
| **AWS KMS (Key Management Service)** | Manages encryption keys for data at rest | Almost every AWS service (S3, EBS, RDS) integrates with KMS for encryption — foundational for data protection |
| **AWS WAF (Web Application Firewall)** | Filters malicious HTTP traffic before it reaches your app (SQLi, XSS patterns) | Sits in front of load balancers/CloudFront — a common defense layer for public web apps |
| **Terraform** | Infrastructure-as-Code tool (not AWS-specific) | Lets you define VPCs, IAM roles, EC2 instances as version-controlled code instead of manual console clicks — deliberately deferred to later in this roadmap, but extremely commonly required in job postings |
| **AWS Organizations + Service Control Policies (SCPs)** | Account-level guardrails that even admins can't override | Real enterprises use this to enforce "no one can ever disable CloudTrail," etc. — explains why Explicit Deny always wins in IAM evaluation |
| **VPC Peering / Transit Gateway** | Connecting multiple VPCs together securely | Relevant once you're managing more than one VPC (multi-environment: dev/staging/prod) |
| **AWS GuardDuty** | Managed threat detection service (analyzes CloudTrail, VPC flow logs, DNS logs for malicious activity) | The "SOC in a box" managed service — good to know exists even if not hands-on yet |
| **Instance Metadata Service v2 (IMDSv2)** | Hardened version of the EC2 metadata endpoint | Directly relevant to the Capital One 2019 breach reference in the threat model — IMDSv2 requires session tokens, preventing the SSRF-to-credential-theft attack pattern used in that incident |

---

## Interview Q&A

**Q: Explain the AWS Shared Responsibility Model.**
A: AWS is responsible for security *of* the cloud — physical infrastructure, hypervisor, host OS on managed services. The customer is responsible for security *in* the cloud — IAM configuration, network settings, data encryption, and application-level security. The boundary shifts depending on the service: for EC2 (IaaS), I patch the guest OS; for Lambda (serverless), AWS handles the runtime entirely and I'm only responsible for my code and its permissions.

**Q: What's the difference between an IAM user and an IAM role?**
A: An IAM user has long-lived credentials meant for a human or a fixed application identity. An IAM role issues temporary, auto-expiring credentials and is meant to be "assumed" by something — an EC2 instance, a Lambda function, or another account. Roles are preferred for workloads because temporary credentials drastically reduce the exploitation window if they ever leak, versus a permanent access key sitting in a config file indefinitely.

**Q: What does a trust policy do, versus a permission policy?**
A: A trust policy defines who or what is allowed to assume a role — the Principal and the `sts:AssumeRole` action. A permission policy defines what that role can actually do once assumed — the usual Effect/Action/Resource structure. They're separate documents because "who can walk through the door" and "what they can do once inside" are different concerns.

**Q: Why separate public and private subnets in a VPC?**
A: Resources that need to receive traffic directly from the internet — like a web server — go in a public subnet, which has a route to an Internet Gateway. Resources that should never be directly internet-reachable — like a database — go in a private subnet, only reachable from within the VPC. This limits the attack surface: even if the web server is compromised, the database isn't directly exposed to the internet.

**Q: Security Groups vs Network ACLs — what's the real difference?**
A: Security Groups are stateful and apply per-instance — if you allow inbound traffic, the response is automatically allowed out, and you can only write Allow rules. NACLs are stateless and apply per-subnet — you must explicitly allow both directions, and you can write both Allow and Deny rules. I use Security Groups as my primary, fine-grained control, and NACLs as a coarser secondary layer, mainly when I need an explicit Deny.

**Q: What is STRIDE and why use it?**
A: STRIDE is a structured threat modeling framework — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege. Instead of reactively guessing what could go wrong, it forces a systematic walk-through of six specific threat categories for every component in a system. I applied it to my CI/CD pipeline and produced a documented threat-model.md covering real threats like dependency tampering and secret leakage, each with a concrete mitigation already in place or planned.

**Q: Walk me through one real threat you identified and its mitigation.**
A: Under Elevation of Privilege, I identified that a compromised PyPI dependency could execute arbitrary code during `pip install`, running with the CI runner's permissions and potentially exfiltrating the `GITHUB_TOKEN`. My mitigation is that Trivy and Bandit run specifically to catch known-vulnerable or suspicious dependencies before later pipeline stages, and I'm planning to further scope `GITHUB_TOKEN` permissions to read-only via the workflow's `permissions:` block, since the current setup uses broader default permissions than strictly necessary.

**Q: You used LocalStack instead of real AWS — how do you know your skills transfer?**
A: LocalStack simulates the actual AWS API surface — the CLI commands, IAM policy JSON syntax, and ARN structure are byte-for-byte identical to real AWS, only the endpoint URL differs. The main gap is that LocalStack's free tier doesn't fully enforce IAM policy evaluation at runtime, which is a known limitation I verified directly by testing an unauthorized write action that should have failed but didn't. The policy-writing and architecture skills are real and directly transferable; live enforcement testing is something I'd validate on real AWS next.

---

## What I'd Add With More Time

- Real AWS account (via AWS Educate) to validate actual IAM policy enforcement
- Terraform to define this VPC/IAM setup as version-controlled Infrastructure-as-Code instead of imperative CLI commands
- CloudTrail + GuardDuty integration for the threat model's Repudiation and Detection mitigations
- IMDSv2 enforcement demonstration, directly tied to the Capital One breach pattern referenced in the threat model

---

## Author

Krish Joshi — B.Tech CSE (Cybersecurity), building toward a DevSecOps career.
## Author

Krish Joshi — B.Tech CSE (Cybersecurity), building toward a DevSecOps career.

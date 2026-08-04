# practice-devsecops

A hands-on DevSecOps portfolio covering containerized application security, CI/CD security automation, cloud IAM fundamentals, and Kubernetes admission control — built incrementally with real, verified evidence at each stage.

**Status:** Months 1 through 4 complete and verified below.
---

## Repository Structure (actual, as of this commit)

```
.
├── month1-toolkit/                # Linux audit + hardening scripts (see its own README)
├── app.py                        # Flask application
├── dockerfile                    # Multi-stage-aware, non-root container build
├── requirements.txt              # Pinned Python dependencies
├── .gitignore
├── .github/workflows/pipeline.yml # CI/CD security pipeline (Bandit, Trivy, Gitleaks)
├── trivy-scan-result.txt         # Saved Trivy scan evidence
├── threat-model.md               # STRIDE threat model of the CI/CD pipeline
├── month3-aws/
│   ├── s3-readonly-policy.json   # Least-privilege IAM policy
│   └── trust-policy.json         # IAM role trust policy
├── deployment.yaml               # Kubernetes Deployment (hardened)
├── service.yaml                  # Kubernetes Service
├── role.yaml                     # RBAC Role
├── rolebinding.yaml               # RBAC RoleBinding
├── policy-no-privileged.yaml     # Kyverno: blocks privileged containers
├── policy-require-nonroot.yaml   # Kyverno: requires runAsNonRoot
├── policy-require-limits.yaml    # Kyverno: requires resource limits
├── bad-pod.yaml                  # Test manifest: privileged (used to prove policy blocks it)
├── bad-pod-root.yaml             # Test manifest: missing runAsNonRoot
├── bad-pod-nolimits.yaml         # Test manifest: missing resource limits
└── README.md
```

---

## Month 1 — Linux Security Toolkit

A read-only Python audit script (SUID/SGID, world-writable files, UID=0 accounts) and a Bash hardening script, validated against real Lynis benchmark scans — including an honest account of a false-positive bug I found and fixed in the audit script, and why the hardening index did not move despite genuine config changes.

Full writeup, code, and Lynis evidence: [month1-toolkit/](./month1-toolkit)

---

## Part 1 — Docker + CI/CD Security Pipeline

### What it does

A Flask app, containerized with a hardened, non-root Alpine-based Docker image, scanned and gated by an automated GitHub Actions pipeline on every push.

### Pipeline stages

| Stage | Tool | What it catches | Blocks build? |
|---|---|---|---|
| SAST | Bandit | Insecure Python code patterns | Yes |
| Build | Docker | Build failures | Yes |
| Image scan | Trivy | CVEs in OS packages and dependencies | Yes, on CRITICAL/HIGH |
| Secret scan | Gitleaks | Leaked credentials in git history | Yes, on any finding |

Also includes: matrix builds across Python 3.11/3.12, pip dependency caching, and GitHub Secrets usage — see `.github/workflows/pipeline.yml`.

### Key result: base image hardening

| Metric | python:3.12-slim (Debian) | python:3.12-alpine |
|---|---|---|
| Total vulnerabilities | 171 | 0 |
| CRITICAL | 4 | 0 |
| HIGH | 19 | 0 |

Switching the base image alone eliminated every CRITICAL and HIGH finding — full scan evidence in `trivy-scan-result.txt`.

### Non-root enforcement

```dockerfile
RUN adduser -D appuser && chown -R appuser:appuser /app
USER appuser
```
Verified at runtime: `docker exec m2 whoami` → `appuser`, not `root`.

---

## Part 2 — AWS IAM Fundamentals (`month3-aws/`)

Practiced using **LocalStack** (a local AWS API simulator) to avoid requiring a credit card while learning genuine AWS mechanics — the CLI commands and policy JSON are identical to real AWS.

**Known, stated limitation:** LocalStack's free Community edition stores and returns IAM policies correctly but does not fully enforce policy evaluation at runtime (that's a Pro-tier feature). The policy-writing skill demonstrated here is real and directly transferable to real AWS; live enforcement testing was verified to have this specific gap, not assumed to work.

### `s3-readonly-policy.json` — least-privilege IAM policy

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
Grants only `GetObject` and `ListBucket` on one named bucket — not `AdministratorAccess`. Two Resource ARNs are required: the bucket itself (for `ListBucket`) and the object wildcard path (for `GetObject`).

### `trust-policy.json` — IAM role trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
Defines which principal (an EC2 instance, via its service principal) is allowed to assume a role — separate from what the role can *do*, which is defined by attaching a permission policy like the one above.

### VPC and networking (created via CLI, not stored as files)

Built a custom VPC (`10.0.0.0/16`) with explicit public (`10.0.1.0/24`) and private (`10.0.2.0/24`) subnet separation, and a Security Group restricting inbound traffic to port 443 only — commands documented in this project's development history.

---

## Part 3 — Kubernetes + Kyverno

### Environment

Local cluster via **k3d** (Kubernetes-in-Docker), `kubectl` for cluster interaction — zero cloud cost, fully reproducible.

### Hardened Deployment (`deployment.yaml`)

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
resources:
  requests:
    memory: "64Mi"
    cpu: "100m"
  limits:
    memory: "128Mi"
    cpu: "250m"
```

**Real debugging note:** initial deployment failed with `container has runAsNonRoot and image has non-numeric user (appuser), cannot verify user is non-root` — Kubernetes needs a numeric UID to verify non-root status before starting a container, and can't resolve a named user without starting it first. Fixed by running `docker run --rm month2-app:latest id appuser` to find the actual UID (1000), then adding `runAsUser: 1000` explicitly.

### RBAC (`role.yaml`, `rolebinding.yaml`)

A `pod-reader-sa` ServiceAccount bound to a Role granting only `get/list/watch` on Pods — verified with live authorization queries, not just "the YAML applied without error":

```
kubectl auth can-i list pods --as=system:serviceaccount:default:pod-reader-sa    → yes
kubectl auth can-i delete pods --as=system:serviceaccount:default:pod-reader-sa  → no
kubectl auth can-i list secrets --as=system:serviceaccount:default:pod-reader-sa → no
```

### Kyverno admission control (3 policies, all live-tested)

| Policy | Blocks | Verified with |
|---|---|---|
| `policy-no-privileged.yaml` | Privileged containers | `bad-pod.yaml` — rejected |
| `policy-require-nonroot.yaml` | Missing `runAsNonRoot` | `bad-pod-root.yaml` — rejected |
| `policy-require-limits.yaml` | Missing resource limits | `bad-pod-nolimits.yaml` — rejected |

Example rejection (privileged container attempt):
```
Error from server: error when creating "bad-pod.yaml": admission webhook
"validate.kyverno.svc-fail" denied the request:
resource Pod/default/bad-privileged-pod was blocked due to the following policies
disallow-privileged-containers:
  no-privileged-containers: 'validation error: Privileged containers are not allowed.
    rule no-privileged-containers failed at path /spec/containers/0/securityContext/privileged/'
```

After all three policies were active, the real `month2-app` Deployment (already compliant with all three) was redeployed and passed cleanly — confirming the policies enforce genuine security requirements without blocking valid workloads.

---

## STRIDE Threat Model (`threat-model.md`)

A full threat model of the CI/CD pipeline using Microsoft's STRIDE framework — Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege — each with a real threat scenario and a mitigation tied to what's actually implemented in this pipeline. See the file for the complete analysis, including an honest "Residual Risk & Future Work" section covering gaps not yet addressed.

---

## How to Run This Locally

```bash
git clone https://github.com/KR-007J/practice-devsecops.git
cd practice-devsecops

# Docker
docker build -t month2-app .
docker run -d -p 5000:5000 --name m2 month2-app
curl http://localhost:5000

# Kubernetes (requires k3d + kubectl)
k3d cluster create devsecops-cluster
docker build -t month2-app:latest .
k3d image import month2-app:latest -c devsecops-cluster
kubectl apply -f deployment.yaml -f service.yaml -f role.yaml -f rolebinding.yaml
kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.13.2/install.yaml
kubectl apply -f policy-no-privileged.yaml -f policy-require-nonroot.yaml -f policy-require-limits.yaml
```

---

## What's Next

- **Month 5** (planned): AI Security — OWASP LLM Top 10 threat modeling applied to a RAG chatbot architecture.
- Move IAM/VPC work from LocalStack to a real AWS account (via AWS Educate) to validate genuine policy enforcement.
- Add SBOM generation (Syft) and image signing (Cosign) to the CI/CD pipeline.

---

## Author

Krish Joshi — B.Tech CSE (Cybersecurity), building toward a DevSecOps career.

# Threat Model: CI/CD Security Pipeline

**System:** GitHub Actions security pipeline for a containerized Flask application
**Methodology:** STRIDE
**Author:** Krish Joshi
**Last updated:** August 2026

---

## 1. System Overview

This pipeline automatically scans, builds, and validates a Dockerized Flask application on every push to GitHub. It runs static code analysis (Bandit), builds a container image, scans that image for known vulnerabilities (Trivy), and scans the repository for leaked secrets (Gitleaks). A failure at any stage blocks the build — this is a security gate, not a passive report.

### Architecture

```
Developer                GitHub                   GitHub Actions Runner
    │                       │                              │
    │  git push             │                              │
    ├──────────────────────>│                              │
    │                       │  triggers workflow           │
    │                       ├─────────────────────────────>│
    │                       │                               │
    │                       │        ┌──────────────────────┴──────────────────────┐
    │                       │        │  1. Checkout code                            │
    │                       │        │  2. Set up Python (matrix: 3.11, 3.12)       │
    │                       │        │  3. Cache pip dependencies                   │
    │                       │        │  4. Bandit      → static code security scan  │
    │                       │        │  5. Docker build → containerize app          │
    │                       │        │  6. Trivy       → image vulnerability scan   │
    │                       │        │                    (blocks on CRITICAL/HIGH) │
    │                       │        │  7. Gitleaks    → secret leak scan           │
    │                       │        └──────────────────────┬──────────────────────┘
    │                       │                               │
    │                       │<──────────────────────────────┤
    │                       │   Pass → merge safely          │
    │                       │   Fail → build blocked         │
```

### Trust boundaries

- **Developer → GitHub**: authenticated via git credentials / SSH keys
- **GitHub → Actions Runner**: ephemeral, isolated compute environment provisioned per run
- **Runner → external registries**: pulls base images (Docker Hub) and dependency packages (PyPI) — both untrusted third parties by default
- **Runner → GitHub Secrets**: encrypted secrets injected at runtime, scoped to this repository

---

## 2. STRIDE Analysis

### S — Spoofing

**Threat:** An attacker impersonates a legitimate contributor — via a compromised GitHub account, stolen SSH key, or stolen personal access token — and pushes malicious code that the pipeline then builds and (if merged) deploys.

**Impact:** Malicious code enters the codebase under a trusted identity, bypassing informal trust assumptions about "who wrote this."

**Mitigations:**
- Multi-factor authentication enforced on the GitHub account
- Branch protection rules on `main` requiring pull request review before merge — no direct pushes
- GPG-signed commits to cryptographically verify author identity (planned enhancement)
- SSH key rotation and use of fine-grained personal access tokens with expiration dates instead of long-lived classic tokens

---

### T — Tampering

**Threat:** A malicious or compromised dependency is introduced into `requirements.txt`, or the workflow definition itself (`.github/workflows/pipeline.yml`) is modified to silently disable or weaken a security check (e.g., removing the Trivy `exit-code: '1'` gate).

**Impact:** The pipeline continues to report "green" while shipping vulnerable or malicious code — a false sense of security is more dangerous than no pipeline at all.

**Mitigations:**
- Dependency versions are explicitly pinned (`flask==3.1.3`), not left as open ranges — prevents silent upgrades to a compromised package version
- Changes to `.github/workflows/` require pull request review, same as application code — the pipeline definition is treated as security-critical code, not configuration boilerplate
- Dependabot alerts flag suspicious or vulnerable dependency changes automatically
- Docker base image pinned to a specific tag (`python:3.12-alpine`) rather than `latest`, reducing the risk of an unexpected upstream change

---

### R — Repudiation

**Threat:** A team member disables a security check, approves a risky merge, or triggers a deployment, and later denies having done so — with no reliable audit trail to prove otherwise.

**Impact:** Accountability gaps make incident investigation slow or impossible, and create room for insider threats to go undetected.

**Mitigations:**
- GitHub Actions run logs are immutable and permanently tied to the authenticated user who triggered them
- Every commit, PR approval, and workflow run is timestamped and attributed by GitHub's platform — this is a built-in mitigation the pipeline benefits from without extra configuration
- Branch protection history and PR review trails provide a durable record of who approved what, and when

---

### I — Information Disclosure

**Threat:** Secrets (API keys, tokens) are accidentally printed into build logs, which are semi-durable and potentially visible to anyone with repository read access. Separately, detailed CVE scan output could reveal to an attacker exactly which vulnerable dependency versions are in use, if that output were ever made public.

**Impact:** Leaked credentials enable unauthorized access to connected systems; detailed vulnerability disclosure gives an attacker a ready-made exploitation roadmap.

**Mitigations:**
- Secrets are stored exclusively as encrypted GitHub Actions secrets, never hardcoded in source or workflow files
- GitHub automatically masks known secret values in log output, even if a step accidentally echoes them
- Pipeline steps that reference secrets validate presence by length or boolean check (`echo "Secret loaded (length: ${#MY_SECRET})"`), never by printing the raw value
- Gitleaks runs on every push specifically to catch secrets that bypass these controls and get committed directly to the repository
- Trivy scan results are stored in the private repository, not published externally, limiting exposure of exact vulnerable versions in use

---

### D — Denial of Service

**Threat:** An attacker (or a misconfigured automation) floods the repository with junk pushes or pull requests, exhausting the GitHub Actions minutes quota and blocking legitimate builds. Separately, a dependency confusion or malicious package could trigger a resource-exhausting build loop.

**Impact:** Legitimate development work is blocked; in a paid GitHub plan, this could also translate into unexpected cost.

**Mitigations:**
- Branch protection rules restrict who can trigger workflow runs on protected branches
- Per-job timeout limits configured in the workflow prevent a single hung step from consuming resources indefinitely
- Rate limiting on PR/issue creation for public repositories (GitHub platform-level control)
- Matrix build scope is deliberately limited (2 Python versions) rather than expanded unnecessarily, keeping per-push resource consumption predictable

---

### E — Elevation of Privilege

**Threat:** A compromised or malicious third-party dependency executes arbitrary code during `pip install` (a known real-world attack vector — supply chain attacks via PyPI packages), running with the same permissions as the CI runner. This could be used to exfiltrate the `GITHUB_TOKEN` or other injected secrets, potentially enabling further access to the repository or connected systems.

**Impact:** A single compromised dependency escalates from "a Python package" to "an attacker with CI runner-level access," which may include write access to the repository depending on token scope.

**Mitigations:**
- Trivy and Bandit exist specifically to catch known-vulnerable or insecure dependencies **before** they run with meaningful permissions in a later stage
- `GITHUB_TOKEN` permissions are scoped to the minimum required for each workflow (read-only where write access isn't needed) via the workflow-level `permissions:` block — a planned hardening step beyond the current default
- Each Actions run executes in an ephemeral, isolated environment that is destroyed after the run — no persistent compromise across builds
- Alpine base image minimizes the number of OS-level packages present, reducing the overall dependency attack surface (validated via Trivy: 171 vulnerabilities on Debian-slim base reduced to 0 CRITICAL/HIGH on Alpine)

---

## 3. Summary Table

| Category | Primary Threat | Key Mitigation |
|---|---|---|
| Spoofing | Compromised contributor identity | MFA, branch protection, signed commits |
| Tampering | Malicious dependency or workflow edit | Pinned versions, PR review on workflow files |
| Repudiation | No audit trail for risky actions | Immutable GitHub Actions logs |
| Information Disclosure | Secret leakage in logs or commits | Secret masking, Gitleaks, no raw echo of values |
| Denial of Service | Pipeline resource exhaustion | Branch protection, job timeouts |
| Elevation of Privilege | Compromised dependency gains runner access | Trivy/Bandit gating, scoped tokens, ephemeral runners |

---

## 4. Residual Risk & Future Work

This threat model reflects the pipeline's current state. Known gaps not yet addressed:

- `GITHUB_TOKEN` permissions are currently using workflow defaults rather than an explicitly minimal scope — tightening this is the next planned hardening step
- No commit signing is currently enforced — GPG-signed commits would strengthen the Spoofing mitigation
- SBOM generation (Syft) and image signing (Cosign) are not yet implemented; they would provide supply-chain provenance beyond what Trivy's vulnerability scanning alone offers

This model should be revisited whenever the pipeline architecture changes materially — new stages, new external dependencies, or new deployment targets.

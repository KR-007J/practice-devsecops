# practice-devsecops








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

## Author

Krish Joshi — B.Tech CSE (Cybersecurity), building toward a DevSecOps career.

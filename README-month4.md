# Practice DevSecOps — Month 4: Kubernetes Basics + Kyverno

A hardened Kubernetes deployment of the Month 2 Flask application, running on a local k3d cluster, with RBAC least-privilege access and Kyverno admission control policies that actively block insecure deployments in real time.

---

## What This Project Demonstrates

- Core Kubernetes objects: Pods, Deployments, ReplicaSets, Services
- SecurityContext hardening enforced at the cluster level (not just Dockerfile-level)
- Real-world Kubernetes/Docker integration debugging (`runAsNonRoot` + named users)
- RBAC: Role, RoleBinding, and verified least-privilege enforcement
- Kyverno policy-as-code: 3 admission control policies, each proven to block bad deployments live

---

## Environment

Local cluster via **k3d** (lightweight Kubernetes-in-Docker) — zero cost, zero cloud dependency, fully reproducible.

```bash
# Install k3d (script verified before running — see note below)
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# Create cluster
k3d cluster create devsecops-cluster

# Install kubectl
sudo pacman -S kubectl
```

**Security note on the install script:** before piping any install script to bash, I fetched and manually reviewed the script content — confirmed it only downloads from k3d's official GitHub Releases over HTTPS/TLS 1.2, verifies SHA256 checksum of the downloaded binary, and contains no obfuscated code or unexpected network calls. Standard practice before running any `curl | bash` command.

---

## Project Structure

```
month2-app/
├── deployment.yaml           # Hardened Deployment manifest
├── service.yaml               # ClusterIP Service
├── role.yaml                  # RBAC Role (least-privilege)
├── rolebinding.yaml            # RBAC RoleBinding
├── policy-no-privileged.yaml   # Kyverno: blocks privileged containers
├── policy-require-nonroot.yaml # Kyverno: requires runAsNonRoot
├── policy-require-limits.yaml  # Kyverno: requires resource limits
└── README.md
```

---

## Part 1: Deploying the App

### Core concept: declarative vs imperative

Docker commands are imperative — "do this now." Kubernetes is declarative — you describe desired state in YAML, and a continuous control loop reconciles actual state toward it. If a Pod crashes, Kubernetes notices the mismatch and recreates it automatically, without manual intervention.

### The Deployment manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: month2-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: month2-app
  template:
    metadata:
      labels:
        app: month2-app
    spec:
      containers:
        - name: month2-app
          image: month2-app:latest
          imagePullPolicy: Never
          ports:
            - containerPort: 5000
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

**Key decisions:**
- `replicas: 2` — basic availability; one Pod failing doesn't take the app down
- `resources.limits` — prevents a single misbehaving Pod from starving other workloads on the same Node (a resource-exhaustion / Denial-of-Service risk, directly tied to the Month 3 threat model's "D" category)
- `securityContext` — cluster-enforced hardening, not just a Dockerfile convention

---

## Part 2: A Real Debugging Story — `runAsNonRoot` vs Named Users

### The problem

First deployment attempt failed with:
```
Error: container has runAsNonRoot and image has non-numeric user (appuser),
cannot verify user is non-root
```

### Root cause

The Dockerfile creates a non-root user by **name** (`adduser -D appuser` + `USER appuser`), which works perfectly in plain Docker. But Kubernetes' `runAsNonRoot: true` check needs to verify a **numeric UID** before starting the container — and it refuses to start the container just to resolve a username, since that would defeat the purpose of a pre-start safety check.

### Fix

```bash
docker run --rm month2-app:latest id appuser
# uid=1000(appuser) gid=1000(appuser)
```
Added the explicit numeric UID to the SecurityContext:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
```

**Why this matters beyond just fixing the error:** this is a genuinely common real-world Docker/Kubernetes friction point. Many production Dockerfiles use `USER 1000` (numeric) directly instead of a named user for exactly this reason — it avoids this exact class of Kubernetes admission failure.

---

## Part 3: RBAC — Least Privilege on Kubernetes

### Role (namespace-scoped permission set)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader-role
  namespace: default
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
```

### RoleBinding (attaches Role to a ServiceAccount)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
  namespace: default
subjects:
  - kind: ServiceAccount
    name: pod-reader-sa
    namespace: default
roleRef:
  kind: Role
  name: pod-reader-role
  apiGroup: rbac.authorization.k8s.io
```

### Verified enforcement (not just "it applied")

```bash
kubectl auth can-i list pods --as=system:serviceaccount:default:pod-reader-sa
# yes
kubectl auth can-i delete pods --as=system:serviceaccount:default:pod-reader-sa
# no
kubectl auth can-i list secrets --as=system:serviceaccount:default:pod-reader-sa
# no
```

This is real, live-tested RBAC enforcement — a `ServiceAccount` scoped to read-only Pod access, verified unable to delete Pods or read Secrets, proving the least-privilege boundary genuinely holds.

---

## Part 4: Kyverno — Admission Control Policy-as-Code

### Why admission control matters beyond CI scanning

Trivy and Bandit (from Month 2) scan code and images **before** deployment, inside CI. But nothing stops someone from manually running `kubectl apply` with an insecure manifest that never passed through CI. Kyverno closes that gap by enforcing policy **at the cluster's admission boundary itself** — every request to create a resource is validated in real time, regardless of how it arrives.

### Installation

```bash
kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.13.2/install.yaml
kubectl get pods -n kyverno
```

### Policy 1 — Disallow privileged containers

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: Enforce
  rules:
    - name: no-privileged-containers
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Privileged containers are not allowed."
        pattern:
          spec:
            containers:
              - =(securityContext):
                  =(privileged): "false"
```

**Live-blocked test result:**
```
Error from server: error when creating "bad-pod.yaml": admission webhook
"validate.kyverno.svc-fail" denied the request:
resource Pod/default/bad-privileged-pod was blocked due to the following policies
disallow-privileged-containers:
  no-privileged-containers: 'validation error: Privileged containers are not allowed.
    rule no-privileged-containers failed at path /spec/containers/0/securityContext/privileged/'
```

### Policy 2 — Require non-root

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-non-root
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-run-as-non-root
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Containers must set runAsNonRoot: true"
        pattern:
          spec:
            containers:
              - securityContext:
                  runAsNonRoot: true
```

**Live-blocked test result:**
```
Error from server: ... denied the request:
require-non-root:
  require-run-as-non-root: 'validation error: Containers must set runAsNonRoot: true.
    rule require-run-as-non-root failed at path /spec/containers/0/securityContext/'
```

### Policy 3 — Require resource limits

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-limits
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Containers must define resource limits (cpu and memory)"
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    memory: "?*"
                    cpu: "?*"
```

**Live-blocked test result:**
```
Error from server: ... denied the request:
require-resource-limits:
  require-limits: 'validation error: Containers must define resource limits (cpu and
    memory). rule require-limits failed at path /spec/containers/0/resources/limits/'
```

### Proof the policies don't break legitimate deployments

After all 3 policies were active, the actual `month2-app` Deployment (which already includes `runAsNonRoot`, `runAsUser`, non-privileged, and resource limits) was deleted and reapplied — it passed admission cleanly and both replicas reached `Running 1/1`. This confirms the policies enforce real security requirements without being so strict they block valid, well-configured workloads.

---

## Interview Q&A

**Q: What's the difference between a Pod, a Deployment, and a ReplicaSet?**
A: A Pod is the smallest deployable unit — one or more containers sharing network and storage. A ReplicaSet ensures a specified number of identical Pods are always running, recreating them if they crash. A Deployment manages ReplicaSets on top of that, adding rolling updates and rollback capability. In practice, you almost never create a bare Pod directly — you create a Deployment, which creates the ReplicaSet, which creates and maintains the Pods.

**Q: Walk me through a real Kubernetes bug you debugged.**
A: My Deployment failed with `CreateContainerConfigError` because my Dockerfile creates a non-root user by name (`appuser`), but Kubernetes' `runAsNonRoot: true` check needs a numeric UID to verify safety before starting the container — it can't resolve a username without starting the container first, which would defeat the check's purpose. I found the actual UID with `docker run --rm image id appuser`, then added `runAsUser: 1000` explicitly to the SecurityContext, which resolved it immediately.

**Q: What's the difference between a Role and a ClusterRole?**
A: A Role's permissions are scoped to a single namespace. A ClusterRole's permissions apply cluster-wide, across all namespaces. I used a namespace-scoped Role for a ServiceAccount that only needed read access to Pods within the `default` namespace — no reason to grant broader scope than necessary.

**Q: How did you verify your RBAC policy actually worked, not just that it applied without error?**
A: `kubectl apply` succeeding only means the YAML was syntactically valid and accepted by the API server — it doesn't prove the permission boundary is real. I used `kubectl auth can-i <verb> <resource> --as=<serviceaccount>` to directly query the API server's authorization decision. This confirmed my ServiceAccount could list Pods but was denied on deleting Pods and listing Secrets — actual enforcement, not just a plausible-looking policy file.

**Q: What is Kyverno and why use it alongside CI/CD scanning?**
A: Kyverno is a Kubernetes admission controller — it validates every resource creation request against defined policies before the object is persisted to the cluster, and can outright reject non-compliant requests. My CI pipeline (Bandit, Trivy, Gitleaks) scans code and images before deployment, but nothing stops someone from manually running `kubectl apply` with a bad manifest that bypasses CI entirely. Kyverno closes that gap by enforcing policy at the cluster's admission boundary itself, regardless of how the request arrives — genuine defense-in-depth.

**Q: What's the difference between `Enforce` and `Audit` in a Kyverno policy?**
A: `Enforce` actively blocks non-compliant requests — the resource is never created. `Audit` logs violations but still allows the request through. `Audit` is used during policy rollout in production to see what would be blocked without breaking existing workloads, then teams typically flip to `Enforce` once they've confirmed the policy doesn't have unintended false positives.

**Q: How do you know your Kyverno policies aren't too strict?**
A: After enabling all three policies, I redeployed my actual application Deployment — which already included `runAsNonRoot`, a non-root UID, no privileged mode, and resource limits — and confirmed it passed admission cleanly with both replicas reaching `Running`. Proving that legitimate, well-configured workloads pass while genuinely insecure ones are blocked is as important as proving the blocking itself.

**Q: Why did you check the k3d install script before running it?**
A: `curl | bash` is a common install pattern but blindly piping unknown scripts to a shell is a real risk. I fetched the script content directly and reviewed it for red flags — obfuscated code, unexpected network calls, writes outside expected directories. It downloaded only from k3d's official GitHub Releases over HTTPS with TLS enforcement and verified a SHA256 checksum before installing — a legitimate, standard install pattern, not something to blindly trust just because it's common.

---

## What I'd Add With More Time

- Ingress resource with a real domain-style routing setup, instead of `port-forward` for local testing
- Kyverno policies in `Audit` mode first, transitioning to `Enforce`, to demonstrate the real-world rollout pattern
- Falco for runtime threat detection (flagged as a Month 6 stretch topic in the original roadmap)
- Integrate Trivy's Kubernetes-target scanning to check the cluster itself for misconfigurations, not just the image

---

## Author

Krish Joshi — B.Tech CSE (Cybersecurity), building toward a DevSecOps career.

# Phase 8 — Containers & Kubernetes

**Goal:** run the whole Deskly stack on **Kubernetes**, locally and for free, using a `kind` (Kubernetes-in-Docker) cluster. Translate the Compose file into Deployments/Services/Ingress, run scheduled work as a CronJob, and understand what an orchestrator actually buys you.

**Done when:** `kubectl get pods` shows backend/worker/beat/frontend + Postgres/Redis running in a local cluster, the app is reachable through an Ingress, an export still works, and the digest runs as a Kubernetes CronJob.

> This runs entirely on the laptop (kind is free). Deploying to real EKS is an optional extension after this — the manifests are the same; only the cluster and the backing services change.

## Concepts to teach here

- **Why an orchestrator.** Compose runs containers on one machine. Kubernetes runs them across many, and adds self-healing (restart crashed pods), scaling (more replicas on demand), rolling updates (no-downtime deploys), and service discovery. You feel the value once you have several services that must stay up.
- **The core objects (map each to something they already know):**
  - **Pod** — one or more containers scheduled together (the unit K8s runs).
  - **Deployment** — declares "keep N replicas of this pod running" and handles rollouts. (backend, worker, frontend)
  - **Service** — a stable in-cluster address + load balancing for a set of pods (how backend finds Postgres).
  - **Ingress** — the HTTP front door routing external traffic to Services (the Phase 0 reverse proxy, K8s-native).
  - **ConfigMap / Secret** — non-secret and secret config injected as env/files (your `.env`, the K8s way).
  - **CronJob** — scheduled one-off jobs (your Celery Beat digest, or run Beat as a Deployment — discuss both).
  - **PersistentVolumeClaim** — durable storage for stateful pods like Postgres (or keep Postgres external, which is what real clusters do).
- **Declarative, not imperative.** You describe desired state in YAML; K8s continuously reconciles reality to match. This mindset is the whole point.
- **Probes.** Liveness/readiness probes reuse your Phase 0 `/api/health/` — K8s uses them to know when to restart or route traffic.

## Build steps (vertical slice)

1. **Create a kind cluster.** Install kind + kubectl; `kind create cluster`. Install an ingress controller (ingress-nginx) into it.
2. **Config & secrets.** A ConfigMap for non-secret config, a Secret for `SECRET_KEY`/DB creds/API key. (For real clusters, mention sealed-secrets/external-secrets — don't commit raw Secrets.)
3. **Backing services.** For the lab, run Postgres and Redis as in-cluster Deployments (Postgres with a PVC) — or, closer to production, point at external managed ones. Explain the tradeoff (stateful workloads on K8s are advanced).
4. **App workloads.** Deployments for `backend`, `celery-worker`, `frontend`; a Deployment *or* CronJob for scheduled tasks. Services for each. Add readiness/liveness probes hitting `/api/health/`. Set resource requests/limits.
5. **Load images into kind.** `kind load docker-image deskly-backend:<sha>` (or push to a local registry) so the cluster can pull your locally-built images.
6. **Migrations as a Job.** Run DB migrations as a one-off Kubernetes `Job` before/independent of the rolling app, not baked into container start.
7. **Ingress.** Route `/api` → backend Service, everything else → frontend Service. Hit the app through the ingress host.
8. **(Optional) Helm.** Once raw YAML makes sense, template it with a Helm chart so config is DRY and environments differ by values file. Introduce this *after* they've felt the raw manifests.

Representative Deployment sketch (let them adapt):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: backend }
spec:
  replicas: 2
  selector: { matchLabels: { app: backend } }
  template:
    metadata: { labels: { app: backend } }
    spec:
      containers:
        - name: backend
          image: deskly-backend:<sha>
          envFrom: [{ configMapRef: { name: deskly-config } }, { secretRef: { name: deskly-secrets } }]
          readinessProbe: { httpGet: { path: /api/health/, port: 8000 }, initialDelaySeconds: 5 }
          livenessProbe:  { httpGet: { path: /api/health/, port: 8000 }, initialDelaySeconds: 10 }
          resources: { requests: { cpu: 100m, memory: 128Mi }, limits: { cpu: 500m, memory: 512Mi } }
```

## Verify

- `kubectl get pods` → all app + infra pods `Running`/`Ready`.
- The app answers through the **Ingress** host; `/api/health/` is green.
- Delete a backend pod (`kubectl delete pod ...`) → the Deployment recreates it automatically (self-healing).
- Run an export → it still lands in object storage; the digest **CronJob** shows completed runs in `kubectl get jobs`.
- A rolling update (`kubectl set image ...` / re-apply) swaps pods with no downtime; readiness probes gate traffic until new pods are ready.

## Best practices to call out

- **Set resource requests/limits and probes** on every workload — the scheduler and self-healing depend on them.
- **Migrations as a Job**, not on container start, to avoid races with multiple replicas.
- **Don't commit raw Secrets;** use sealed-secrets/external-secrets in real clusters.
- **Keep state out of the cluster where you can** (managed Postgres/Redis); stateful sets + PVCs are advanced ops.
- **One source of truth** for manifests (git); apply declaratively; template with Helm/Kustomize as it grows.
- **Same image everywhere** — the SHA you tested locally is the SHA you run.

## Canonical docs

- Kubernetes concepts: https://kubernetes.io/docs/concepts/
- kind: https://kind.sigs.k8s.io/ · kubectl: https://kubernetes.io/docs/reference/kubectl/
- Deployments: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/ · Services: https://kubernetes.io/docs/concepts/services-networking/service/
- Ingress + ingress-nginx: https://kubernetes.io/docs/concepts/services-networking/ingress/ and https://kubernetes.github.io/ingress-nginx/
- CronJob: https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/ · Jobs: https://kubernetes.io/docs/concepts/workloads/controllers/job/
- Probes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Helm: https://helm.sh/docs/

## Common issues (lab copilot fodder)

- **`ImagePullBackOff`** → the cluster can't find your image; you forgot `kind load docker-image` or a registry push. Most common kind pitfall.
- **`CrashLoopBackOff`** → the container starts then dies; `kubectl logs` + `kubectl describe pod` reveal why (bad env, failed migration, missing secret).
- **Pending pods** → unschedulable due to resource requests or a missing PVC; check `kubectl describe`.
- **Ingress 404/503** → controller not installed, wrong host, or the Service selector doesn't match pod labels.
- **CronJob never fires** → schedule syntax or timezone; check `kubectl get cronjob` and its last-schedule time.

---

## Capstone checklist (the whole lab)

Use this to confirm the learner has actually built a production-shaped SaaS. Each maps to their original requirements:

- [ ] **Local-first stack** comes up with one command; `/api/health/` is real (Phase 0).
- [ ] **Multi-tenant** data model with proven isolation test (Phase 1).
- [ ] **Sessions + JWT + Google OAuth** and **RBAC** enforced at data + API + UI layers, with a permission-matrix test (Phase 2 + `rbac-access-control.md`).
- [ ] **Admin** hardened; **impersonation** works and is **audited**; **feature flags** gate a real feature (Phase 3).
- [ ] **Celery** exports to object storage + **scheduled email** digests/SLA reminders (Phase 4).
- [ ] **AI suggested replies** (grounded, human-in-the-loop, flagged) + **MCP server** exposing scoped tools (Phase 5).
- [ ] **Public v1 API** + **signed, retried, logged webhooks** + **interactive OpenAPI docs** with a test console (Phase 6).
- [ ] **Deployed to AWS** on managed services, free-tier, no baked secrets (Phase 7).
- [ ] **CDN** fronts static assets with correct cache rules; private files signed; **origin locked down** so it can't be bypassed (Phase 7b).
- [ ] **Kubernetes**: Deployments/Services/Ingress + CronJob, self-healing demonstrated (Phase 8).

**Stretch goals** once the core works: Terraform/CDK IaC, a customer portal, `pgvector` semantic search for the assistant, CI/CD (GitHub Actions build→test→push→deploy), observability (structured logs, metrics, tracing), and blue/green or canary releases via flags.

# Phase 0 — Containerized Foundation

**Status:** ✅ Verified

**Goal:** stand up the whole local stack in one command, with an honest health
check, so every later phase has a running app to build on.

## What we built

- **Docker Compose stack** with four services: `db` (Postgres 16), `redis`
  (Redis 7), `backend` (Django + Django REST Framework), `frontend`
  (React + TypeScript via Vite).
- **A real health endpoint** at `GET /api/health/` that actually queries
  Postgres (`SELECT 1`) and pings Redis, returning
  `{"status": "ok", "db": true, "redis": true}` — or `degraded` if a
  dependency is down.
- **Env-driven config** — all secrets/hosts come from `.env` (never hardcoded),
  following the 12-factor principle. `.env.example` is the committed template;
  `.env` is git-ignored.

## Key concepts

- **Container** — a lightweight, isolated box holding an app plus everything it
  needs to run, so it behaves the same on any machine.
- **Docker Compose** — a `docker-compose.yml` that declares several containers
  and how they connect, brought up together with `docker compose up`.
- **Health check** — a probe a container exposes so orchestrators (Compose,
  later Kubernetes) know it's *actually* ready, not just "process started."

## Architecture decisions & trade-offs

- **Health check probes real dependencies, not just liveness.** A route that
  returns 200 unconditionally can't tell a load balancer the DB is down. Cost:
  a tiny bit of latency per check — worth it. This same endpoint becomes the
  K8s liveness/readiness probe in Phase 8.
- **`depends_on: service_healthy`** makes the backend wait until db/redis pass
  their health checks before starting — avoids "connection refused" crashes on
  cold boot. Trade-off: slightly slower startup for reliability.
- **Same containers everywhere.** Running Postgres/Redis in containers locally
  (not native installs) keeps laptop parity with cloud, so "works on my
  machine" surprises shrink.

## How to verify

```bash
docker compose up --build          # all four services come up
curl localhost:8000/api/health/    # {"status":"ok","db":true,"redis":true}
# Falsifiability test: stop db, confirm it fails honestly
docker compose stop db
curl localhost:8000/api/health/    # {"status":"degraded","db":false,...}
```

Frontend serves at `http://localhost:5173` and proxies `/api/health/` to the
backend.

## Gotchas

- The backend container mounts `./backend:/app`, so files you edit locally show
  up live inside the container — no rebuild needed for code changes.

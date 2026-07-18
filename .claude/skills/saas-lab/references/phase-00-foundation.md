# Phase 0 — Foundation: the local stack

**Goal:** a reproducible, one-command local environment where an empty Django API and an empty React/TS app talk to each other, backed by Postgres and Redis in containers. Ship nothing fancy — just prove the plumbing.

**You'll know the phase is done when:** `docker compose up` brings everything up, `GET /api/health/` returns `{"status":"ok"}` with a real DB check, and the React app renders a page that fetches and shows that health status.

## Concepts to teach here

- **Why containers from day one.** "Works on my machine" is the oldest bug in software. Docker packages each service with its dependencies so the learner's laptop, a teammate's, and the cloud all run the same thing. Compose wires several containers into one local system. This is also why we're local-first: the whole stack runs free on the laptop.
- **The twelve-factor idea (lightly).** Config comes from the environment, not hardcoded. That's why we use a `.env` file and read it in settings. Mention https://12factor.net as background, not homework.
- **Monolith + SPA split.** Django serves JSON; React renders UI. They're separate dev servers now, unified behind a proxy later. Keeping them decoupled teaches clean API boundaries.

## Build steps (vertical slice)

Guide the learner to create this layout — have them make the folders/files, don't paste a finished repo:

```
deskly/
  docker-compose.yml
  .env.example            # committed; real .env is gitignored
  backend/
    Dockerfile
    pyproject.toml (or requirements.txt)
    manage.py
    config/               # Django project (settings, urls, wsgi/asgi)
    apps/
      core/               # health check + shared bits live here
  frontend/
    Dockerfile
    package.json
    src/
  Makefile                # friendly wrappers: make up, make migrate, make test
```

1. **Backend project.** `django-admin startproject config backend` then a `core` app. Add DRF. Split settings so config reads from env (`DATABASE_URL`, `REDIS_URL`, `DEBUG`, `SECRET_KEY`). `django-environ` or `os.environ` both fine — explain the tradeoff briefly.
2. **Health endpoint.** In `core`, a DRF view at `/api/health/` that runs `SELECT 1` against Postgres and pings Redis, returning `{"status":"ok","db":true,"redis":true}`. This is the single most useful endpoint in the whole app — it's what Compose healthchecks, load balancers, and Kubernetes probes hit.
3. **Compose file.** Services: `db` (postgres:16), `redis` (redis:7), `backend` (build ./backend), `frontend` (build ./frontend). Use `depends_on` with healthchecks so backend waits for a *healthy* db, not just a started one. Mount source as volumes for hot reload. Put all secrets/config in `.env`.
4. **Frontend app.** `npm create vite@latest frontend -- --template react-ts`. Add a single component that fetches `/api/health/` and renders the status. Configure Vite's dev server proxy so `/api` forwards to the backend container (avoids CORS pain in dev; explain what CORS is when it comes up).
5. **Makefile niceties.** `make up`, `make down`, `make logs`, `make migrate`, `make sh` (shell into backend), `make test`. Small ergonomics that keep the learner in flow.

Representative healthcheck view (let them adapt it):

```python
# backend/apps/core/views.py
from django.db import connection
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    db_ok = True
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
    except Exception:
        db_ok = False
    redis_ok = cache.get_or_set("health", "ok", 5) == "ok"
    return Response({"status": "ok" if db_ok and redis_ok else "degraded",
                     "db": db_ok, "redis": redis_ok})
```

## Verify

- `docker compose up --build` starts all four services; `db` reports healthy before `backend` starts.
- `curl localhost:8000/api/health/` → `{"status":"ok",...}`.
- The Vite app (localhost:5173) shows the health status it fetched through the proxy.
- Stopping the `db` container and refetching flips `db` to `false` — proves the check is real, not hardcoded.

## Best practices to call out

- **Pin base image versions** (`postgres:16`, not `postgres:latest`) for reproducibility.
- **Never bake secrets into images.** They come from `.env` / the environment at runtime.
- **Healthchecks everywhere.** The pattern you set up now is reused by Kubernetes liveness/readiness probes in Phase 8.
- **`.dockerignore` and `.gitignore` early** — keep `node_modules`, `.env`, and `__pycache__` out of images and history.
- **Non-root container user** for the backend image is a good habit; introduce it now or note it for the hardening pass in Phase 7.

## Canonical docs

- Django: https://docs.djangoproject.com/en/stable/
- Django REST Framework: https://www.django-rest-framework.org/
- Docker Compose: https://docs.docker.com/compose/
- Vite: https://vite.dev/guide/
- Twelve-Factor App: https://12factor.net/

## Common issues (lab copilot fodder)

- **Backend starts before Postgres is ready** → use `depends_on: condition: service_healthy` plus a real DB healthcheck; explain the difference between "container started" and "service ready."
- **Frontend can't reach the API / CORS errors** → in dev, use Vite's proxy so requests are same-origin; save real CORS config (`django-cors-headers`) for when the SPA is served from a different origin.
- **`SECRET_KEY` missing** → shows up as a Django ImproperlyConfigured error; the fix teaches the env-config pattern.
- **Port already in use** → something else is on 5432/8000/5173; teach `docker compose down` and checking `lsof`.

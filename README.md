# Deskly — a SaaS engineering lab

A hands-on lab for building a realistic, multi-tenant SaaS help desk from scratch,
local-first and inside free tiers. You learn production engineering by building it,
guided phase by phase, following official docs.

This repo ships a **runnable Phase 0** (the plumbing) plus the full curriculum as a
Claude skill in `.claude/skills/saas-lab/`. Phases 1–8 you build yourself, guided.

📓 **Engineering notes:** [`docs/`](docs/README.md) — a per-phase log of what was
built, why, and the trade-offs, plus architecture decision records, a known-gaps
register, and a troubleshooting log of everything that actually broke.

📚 **The course:** [`content/course/`](content/course/README.md) — each phase written
up as a lesson for support engineers, framed around a realistic ticket with a
break-it/fix-it exercise. All drafts until reviewed.

## What's already here (Phase 0)

- Django + Django REST Framework backend with a real `/api/health/` check
- React + TypeScript (Vite) frontend that fetches and shows that health status
- Postgres + Redis, all wired with Docker Compose
- Env-driven config, a Makefile, and sensible ignore files

Everything above Phase 0 (multi-tenancy, auth, admin/impersonation/flags, Celery
exports & email, AI + MCP, webhooks/API/docs, AWS, Kubernetes, CDN, RBAC deep-dive)
is described in the skill and built as you go.

## Quick start (runs the plumbing)

Prereqs: Docker Desktop (or Docker Engine + Compose).

```bash
cp .env.example .env        # then edit if you like
make up                     # or: docker compose up --build
```

Then:

- Backend health: http://localhost:8000/api/health/  → `{"status":"ok","db":true,"redis":true}`
- Frontend: http://localhost:5173  → shows the health status it fetched through the proxy

To prove the check is real, stop Postgres (`docker compose stop db`) and refetch —
`db` flips to `false`. Handy Make targets: `make logs`, `make migrate`, `make sh`, `make test`, `make down`.

## How to use the guided curriculum

There are two ways, depending on where you're working.

### A) In Claude Code (recommended — the skill is already in this repo)

1. Install Claude Code if you haven't: https://docs.claude.com/en/docs/claude-code/overview
2. From this repo's root, start Claude Code (`claude`). Project skills load automatically
   from `.claude/skills/`.
3. Confirm it's loaded: ask **"what skills are available?"** or run **`/skills`**.
   If you edit the skill, `/reload-skills` picks up changes.
4. Kick it off: **"Let's start the SaaS lab — walk me through Phase 1."**
   Claude reads the skill and pairs with you: concept → docs → build a small slice →
   verify → best practices. Say **"continue Phase 4"** etc. to resume any time.

### B) In the Claude app / claude.ai

Install the packaged skill once (the `saas-lab.skill` file), then in any chat say
"let's continue the SaaS lab." Or just paste a phase file from
`.claude/skills/saas-lab/references/` and ask Claude to guide you through it.

## Repo layout

```
deskly/
  backend/            Django + DRF (Phase 0: health check)
  frontend/           React + TypeScript (Vite)
  docker-compose.yml  Postgres + Redis + backend + frontend
  Makefile            make up / down / logs / migrate / sh / test
  docs/               engineering notes, ADRs, known gaps, troubleshooting log
  content/course/     published course articles (drafts)
  .env.example        copy to .env
  .claude/skills/
    saas-lab/         the full guided curriculum (SKILL.md + references)
```

## The roadmap (built via the skill)

0. Foundation — **done, in this repo**
1. Domain model & multi-tenancy
2. Auth: sessions + JWT + Google OAuth + RBAC
3. Admin, impersonation & feature flags
4. Async: Celery exports & scheduled email
5. AI: in-app assistant + MCP server
6. Integrations: public API + webhooks + OpenAPI docs
7. Cloud: deploy to AWS (free tier)
   - 7b. Edge, CDN & origin protection
8. Containers & Kubernetes
   - plus the RBAC deep-dive (`references/rbac-access-control.md`)

Open `.claude/skills/saas-lab/SKILL.md` for the full map.

## Notes

- Keep secrets in `.env` (gitignored). The only non-free dependency is the AI model
  API in Phase 5 — kept to cents.
- This is a learning lab, not a product: real billing, a customer portal, and scale
  tuning are out of scope (great stretch goals once the core works).

# ADR-0001 — Local-first stack on Docker Compose

- **Status:** Accepted
- **Date:** 2026-07-18
- **Phase:** 0

## Context

Deskly needs four things running together to do anything useful: a Django
backend, a React frontend, a Postgres database, and Redis. ("Redis" is a fast
in-memory store used later for caching and as a job queue.)

Three ways to get that running:

1. Install everything directly on the Mac (Homebrew Postgres, Homebrew Redis,
   Python virtualenv, Node).
2. Run it all in containers, orchestrated locally by Docker Compose.
3. Develop against cloud services from day one.

The learner is new to this stack, so setup friction is a real cost — hours lost
to "it won't install" are hours not spent learning. The project also has to stay
free, and must eventually deploy to AWS and Kubernetes without a rewrite.

A **container** is a packaged, isolated copy of an application plus everything it
needs to run. **Docker Compose** is a single file describing several containers
and how they connect.

## Decision

We will run the entire stack locally in Docker Compose, defined in
`docker-compose.yml`, with each service built from its own Dockerfile. No
project dependency gets installed directly on the host machine.

Services depend on each other through **health checks** rather than start order:
the backend waits for `db` and `redis` to report *healthy*, not merely *started*.

## Consequences

**Good**

- One command (`make up`) gets a working system. No install guides, no version
  drift between machines.
- **Parity**: what runs locally is close to what runs in the cloud. The same
  container images move to AWS in Phase 7 and Kubernetes in Phase 8 — the
  topology is already right, so those phases teach orchestration rather than
  re-plumbing.
- Fully disposable. `docker compose down -v` resets to a clean slate, which
  makes breaking things on purpose safe — and this course depends on breaking
  things on purpose.
- Costs nothing.

**Bad**

- Docker is another concept to learn before writing any application code.
- Slower than native on macOS: containers run inside a lightweight VM, so file
  syncing and startup have overhead.
- Failures gain a layer. "Is it my code, or the container?" is a genuinely new
  category of confusion for a beginner.

**Risks to watch**

- **Port conflicts** with software already on the host — this bit us immediately
  (see GAP-005 and the 5432 entry in `troubleshooting-log.md`).
- Local convenience settling into production. Published database ports and
  plaintext `.env` files are fine here and wrong later; tracked in
  `known-gaps.md` so they don't survive by inertia.

## Alternatives considered

| Option | Why not |
|---|---|
| Install natively on the Mac | Fastest to run, but setup is fragile and machine-specific, and it teaches nothing that transfers to deployment. "Works on my machine" is the exact problem containers were invented to solve. |
| Cloud services from day one | Real parity, but costs money, needs accounts and credentials before writing a line of code, and makes iteration slow. Deferred to Phase 7, deliberately. |
| Devcontainers only, no Compose | Good editor integration, but devcontainers describe a *development environment*, not a *deployable topology*. We use both — Compose defines the system, devcontainers sit on top for editing inside it. |

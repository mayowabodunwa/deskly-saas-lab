# Deskly — Engineering Notes

Per-phase summaries of what was built, **why** it was built that way, and the
trade-offs behind each decision. These are a reference as you go and a record of
architectural choices (think lightweight ADRs — Architecture Decision Records).

> **Fork this?** This repo is a reusable boilerplate. It ships a verified
> Phase 0 and an empty notes framework — start at Phase 1 and fill in a note per
> phase as you build, copying [`_TEMPLATE.md`](_TEMPLATE.md).

## How this works

- **Concept → build → verify.** Every slice starts with the *why* and ends with
  a concrete "you'll know it worked when…" check.
- **Branch per phase.** `main` always holds verified, working code. Each phase
  is built on its own branch (`phase-1-domain`, `phase-2-auth`, …) and merged
  via a Pull Request after review.
- **Local-first, free-first.** Everything runs in Docker Compose (Postgres,
  Redis, and later MinIO/MailHog). No cloud spend until the AWS phase.
- **One note per phase.** When you start a phase, copy `_TEMPLATE.md` to
  `phase-N-<name>.md` and grow it as you build.

## Phase tracker

| Phase | Notes | Status |
|-------|-------|--------|
| 0 — Foundation | [phase-0-foundation.md](phase-0-foundation.md) | ✅ Verified |
| 1 — Domain model & multi-tenancy | _to write_ | ⬜ Not started |
| 2 — Auth (sessions + JWT + OAuth + RBAC) | _to write_ | ⬜ Not started |
| 3 — Admin, impersonation & feature flags | _to write_ | ⬜ Not started |
| 4 — Async: Celery exports & scheduled email | _to write_ | ⬜ Not started |
| 5 — AI: in-app assistant + MCP server | _to write_ | ⬜ Not started |
| 6 — Integrations: public API + webhooks + docs | _to write_ | ⬜ Not started |
| 7 — Cloud: deploy to AWS (+ 7b edge/CDN) | _to write_ | ⬜ Not started |
| 8 — Containers & Kubernetes | _to write_ | ⬜ Not started |

The full curriculum lives in `.claude/skills/saas-lab/`.

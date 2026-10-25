# Deskly — Engineering Notes

Per-phase summaries of what we built, **why** we built it that way, and the
trade-offs behind each decision. These are a reference for us and a record of
architectural choices (think lightweight ADRs — Architecture Decision Records).

## How we work

- **Concept → build → verify.** Every slice starts with the *why*, ends with a
  concrete "you'll know it worked when…" check.
- **Branch per phase.** `main` always holds verified, working code. Each phase
  is built on its own branch (`phase-1-domain`, `phase-2-auth`, …) and merged
  via a Pull Request after review.
- **Local-first, free-first.** Everything runs in Docker Compose (Postgres,
  Redis, and later MinIO/MailHog). No cloud spend until the AWS phase.
- **One note per phase.** When you start a phase, copy [`_TEMPLATE.md`](_TEMPLATE.md)
  to `phase-N-<name>.md` and grow it as you build.
- **Break it on purpose.** Every phase ends by deliberately breaking what we just
  built and diagnosing it from the symptoms alone — the way a support ticket
  actually arrives. That exercise becomes the heart of the phase's article.

## Repository

- GitHub: `mayowabodunwa/deskly-saas-lab` (private)

## Phase index

| Phase | Notes | Status |
|-------|-------|--------|
| 0 — Foundation | [phase-0-foundation.md](phase-0-foundation.md) | ✅ Verified |
| 1 — Domain model & multi-tenancy | [phase-1-domain-multitenancy.md](phase-1-domain-multitenancy.md) | ✅ Verified |
| 2 — Auth (sessions + JWT + OAuth + RBAC) | [phase-2-auth.md](phase-2-auth.md) | ✅ Verified (PR #2 merged) |
| 3 — Admin, impersonation & feature flags | [phase-3-admin-impersonation-flags.md](phase-3-admin-impersonation-flags.md) | 🚧 In progress |
| 4 — Async: Celery exports & scheduled email | _to write_ | ⬜ Not started |
| 5 — AI: in-app assistant + MCP server | _to write_ | ⬜ Not started |
| 6 — Integrations: public API + webhooks + docs | _to write_ | ⬜ Not started |
| 7 — Cloud: deploy to AWS (+ 7b edge/CDN) | _to write_ | ⬜ Not started |
| 8 — Containers & Kubernetes | _to write_ | ⬜ Not started |

The full curriculum lives in `.claude/skills/saas-lab/`.

## Working documents

Written *during* the build, these are the raw material the course articles are
compiled from.

| Document | What it holds |
|---|---|
| [adr/](adr/) | Architecture Decision Records — one significant decision per file, immutable |
| [known-gaps.md](known-gaps.md) | Risk register: every lab shortcut vs. what production does, and when it must be closed |
| [troubleshooting-log.md](troubleshooting-log.md) | Append-only log of real errors, gotchas and dead ends. Errors quoted verbatim |
| [concepts/](concepts/) | Plain-English system-design notes, one per concept |
| [django-apps-map.md](django-apps-map.md) | Plain-English map of `backend/apps/`: what each app is for, why some have models, how an address finds its view, every endpoint |
| [http-status-codes.md](http-status-codes.md) | The 4xx codes in plain English: what each means in Deskly, and what support does about it |
| [django-orm-to-sql.md](django-orm-to-sql.md) | Translation table: every Django ORM call and the SQL it becomes, with Deskly examples |

## Published course

`../content/course/` holds the public-facing articles — one per phase, each
framed around a realistic support ticket with a break-it/fix-it exercise.
Articles are compiled at the **end** of each phase and stay `draft: true` until
reviewed. See [the course outline](../content/course/README.md).

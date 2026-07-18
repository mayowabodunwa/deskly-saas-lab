# Deskly — Engineering Notes

Per-phase summaries of what we built, **why** we built it that way, and the
trade-offs behind each decision. These are a reference for us and a record of
architectural choices (think lightweight ADRs — Architecture Decision Records).

## How we work

- **Branch per phase.** `main` always holds verified, working code. Each phase
  is built on its own branch (`phase-1-domain`, `phase-2-auth`, …) and merged
  via a Pull Request after review.
- **Local-first, free-first.** Everything runs in Docker Compose (Postgres,
  Redis, and later MinIO/MailHog). No cloud spend until the AWS phase.
- **Concept → build → verify.** Every slice starts with the *why*, ends with a
  concrete "you'll know it worked when…" check.

## Repository

- GitHub: `cloudsenseiNG/deskly-saas-lab` (private)

## Phase index

| Phase | Notes | Status |
|-------|-------|--------|
| 0 — Foundation | [phase-0-foundation.md](phase-0-foundation.md) | ✅ Verified |
| 1 — Domain model & multi-tenancy | [phase-1-domain-multitenancy.md](phase-1-domain-multitenancy.md) | 🚧 In progress |

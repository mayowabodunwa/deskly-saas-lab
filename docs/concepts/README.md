# Deskly — System-Design Whitepaper (working notes)

We build the Deskly app phase by phase; each phase we extract the system-design
concept(s) behind it into a note here. These notes compile into the whitepaper.

| Build phase | Concept note(s) | Status |
|---|---|---|
| 0 — Foundation (Docker, Django, Postgres, Redis) | 01 Tiers & planes, 02 Reverse proxy | ✅ |
| 1 — Domain model & multi-tenancy | 03 DB correctness, 04 Multi-tenancy | 🟡 building |
| 2 — Auth (sessions, JWT, OAuth, RBAC) | 09 Auth | ⬜ |
| 3 — Admin, impersonation, feature flags | bonus: admin & flags | ⬜ |
| 4 — Async: Celery + Redis, exports, email | 05 Caching, 06 Queues, 07 Scheduled, 08 Object storage | ⬜ |
| 5 — AI assistant + MCP server | bonus: AI plane | ⬜ |
| 6 — Public API + webhooks + docs | 10 API design, 11 Webhooks & retries | ⬜ |
| 7 / 7b — AWS deploy, CDN | bonus: cloud parity, 12 CDN & edge | ⬜ |
| 8 — Containers & Kubernetes | 13 Containers & orchestration | ⬜ |

## Notes written so far
- [01 — Tiers & planes](01-tiers-and-planes.md)
- [02 — Reverse proxy](02-reverse-proxy.md)
- [03 — Database correctness](03-database-correctness.md)
- [04 — Multi-tenancy](04-multi-tenancy.md)

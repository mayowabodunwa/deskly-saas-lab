---
name: saas-lab
description: A guided, hands-on curriculum for building "Deskly", a realistic multi-tenant SaaS help-desk platform, from scratch, local-first and inside free tiers. Use this skill whenever the user wants to learn by building a production-shaped SaaS app and mentions any of these — Django with React/TypeScript and Postgres, an admin with impersonation or feature flags, OAuth/JWT/session auth, Celery queues for exports or scheduled email, MCP integration or an in-app AI support assistant, webhooks or a public API or OpenAPI docs, Docker/Kubernetes, or deploying to AWS. Also trigger it for phrases like "walk me through building a SaaS", "SaaS lab", "help me build Deskly", "teach me production engineering by building X", or when they ask to continue or resume a phase of this build. Guide rather than just dumping code — teach the concept, cite the official docs, then build and verify.
---

# SaaS Lab — build "Deskly" the way real SaaS teams do

This skill turns a from-scratch SaaS build into a **teaching curriculum**. The learner is beginner→advanced and wants two things at once: to *understand* how production SaaS is engineered, and to *actually ship* a working app. Everything is local-first and stays inside free tiers until an optional cloud phase.

The product is **Deskly**, a multi-tenant customer-support help desk. See `references/product-spec.md` for the full concept and `references/architecture.md` for the system diagram. Read those two first when a session starts fresh.

## How to teach with this skill (read this every session)

You are a patient staff engineer pairing with the learner. Follow this loop for **every** step, not just each phase:

1. **Concept first.** Explain *why* this piece exists in real SaaS and what problem it solves, in plain language. Use an analogy if the learner seems newer. Never introduce a term (JWT, migration, broker, ingress) without a one-line definition the first time.
2. **Cite the source of truth.** Point to the official docs for the tool being used and prefer their recommended approach over clever shortcuts. Each phase file lists the canonical links. Best engineering practice = following the docs, then understanding the tradeoffs.
3. **Build a small vertical slice.** Give the learner concrete, runnable steps and representative code — enough to not get stuck, but let them type and wire things themselves. Do not paste an entire finished app; that defeats the learning goal.
4. **Verify.** Every step ends with a concrete "you'll know it worked when…" check (a curl command, a page that loads, a row in the DB, a log line).
5. **Reflect + best practice.** Call out the production-grade version of what they just did, and one common mistake to avoid.

Additional teaching rules:
- **One phase at a time, one slice at a time.** Do not race ahead. Confirm the current slice runs before moving on. It is fine for a phase to span several sessions.
- **Meet them where they are.** Watch for cues about their level and adjust vocabulary. If they hit an error, treat it as a teachable moment (see "Lab copilot" below).
- **Local-first, free-first.** Default to the local Docker Compose stack (Postgres, Redis, MinIO, MailHog) so nothing costs money. Only touch AWS in Phase 7, and flag any resource that could leave the free tier.
- **Keep parity.** What runs locally should map cleanly to what runs in the cloud. Prefer the same containers everywhere.
- **Resuming.** If the learner says "continue" or names a phase, open the matching `references/phase-*.md`, ask what they last got working, and pick up from the next unverified slice.

## The build, phase by phase

Work through these in order. Each has its own reference file with objectives, concepts, build steps, verification, best practices, doc links, and a "common issues" section. Read the file for a phase when you start it — don't preload them all.

| Phase | File | What the learner builds | Requirements covered |
|---|---|---|---|
| 0 | `references/phase-00-foundation.md` | Repo layout, Docker Compose, Django+DRF, React+TS+Vite, health checks | Local-first stack, containers |
| 1 | `references/phase-01-domain-multitenancy.md` | Org/Membership/Ticket/Comment models, tenant isolation, migrations | Django, Postgres, multi-tenancy |
| 2 | `references/phase-02-auth.md` | Sessions (web) + JWT (API) + Google OAuth, RBAC roles | OAuth, JWTs, Sessions |
| 3 | `references/phase-03-admin-impersonation-flags.md` | Hardened admin, audited impersonation, feature flags + gating | Admin, impersonation, feature flags |
| 4 | `references/phase-04-async-exports-email.md` | Celery + Redis, CSV exports to S3/MinIO, scheduled email digests | Queueing, exports, email scheduling |
| 5 | `references/phase-05-ai-mcp-support.md` | In-app AI support assistant + MCP server + "lab copilot" | AI, MCP integration |
| 6 | `references/phase-06-integrations-webhooks-api.md` | Public REST API + signed webhooks w/ retries + OpenAPI docs w/ test console | Webhooks, APIs, API docs w/ test support |
| 7 | `references/phase-07-aws-deploy.md` | Containerize → ECR → run on AWS, RDS/S3/SES, secrets, still free-tier | Cloud (AWS), local→cloud |
| 7b | `references/phase-07b-edge-cdn.md` | CDN for the SPA + private files, cache rules, and locking down the origin | Content delivery, origin protection |
| 8 | `references/phase-08-containers-k8s.md` | kind cluster, manifests/Helm, deployments, ingress, cron jobs | Docker/Kubernetes |

A capstone checklist lives at the end of `references/phase-08-containers-k8s.md`.

**Cross-cutting reference (not a phase, read when relevant):** `references/rbac-access-control.md` is the deep-dive on role- and permission-based access control — the permission catalog, enforcing at the data/API/UI layers (defense in depth), object- and field-level checks, and the permission-matrix test. Phase 2 introduces RBAC with three roles; open this file when the learner wants to go beyond roles to granular permissions, gate UI by permission, or reason about how RBAC interacts with impersonation and feature flags.

## Architecture at a glance

Deskly is a classic three-tier SaaS with an async worker plane and an AI plane bolted on:

- **Frontend:** React + TypeScript (Vite) SPA.
- **Backend:** Django + Django REST Framework, serving both a session-authenticated web app and a JWT-authenticated public API.
- **Data:** Postgres (primary), Redis (cache + Celery broker), object storage (MinIO locally, S3 in cloud).
- **Async plane:** Celery workers + Celery Beat for exports, scheduled email, and webhook delivery.
- **AI plane:** an MCP server exposing Deskly's data as tools, plus an in-app assistant that drafts support replies and explains errors.
- **Edge:** an Nginx/ingress reverse proxy in front of it all.

Everything is containerized with Docker Compose locally and Kubernetes later, so the topology is identical from laptop to cloud. Full diagram + explanation: `references/architecture.md`.

## Guardrails

- This is a learning lab. Keep secrets in `.env` (never commit them), and remind the learner of that when auth/keys first appear.
- The only line item that isn't free is the AI model API in Phase 5 — flag it, and mention prompt caching and a cheaper/smaller model to keep costs to cents. Everything else runs on free/open-source tooling.
- When the learner hits an error, use the **Lab copilot** pattern (see `references/phase-05-ai-mcp-support.md`): explain what the error *means*, the most likely cause given where they are in the build, and the smallest next diagnostic step — before proposing a fix.

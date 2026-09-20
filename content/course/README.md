# Support Engineering by Building Systems

A hands-on course that teaches technical support engineers how software systems
actually work — by building one, breaking it on purpose, and diagnosing it the
way a real ticket arrives.

**Status:** in progress. Every article is `draft: true` until reviewed.

## Who this is for

Support engineers, ops folks, and anyone who has to debug a system they didn't
build, from the outside, with only a customer's description to go on.

No prior backend experience assumed. Every term is defined the first time it
appears.

## The idea

Most tutorials show you the happy path: build it, it works, done. That is not
the world support lives in. Support lives in the *broken* path — partial
information, an angry customer, and a system someone else designed.

So each lesson does four things:

1. Opens with a **realistic support ticket** you'd actually receive.
2. **Builds** the piece of the system that ticket is about.
3. **Breaks it on purpose** and diagnoses it from symptoms alone.
4. Ends with **what to check first** next time you see that ticket.

We build one product across the whole course: **Deskly**, a multi-tenant
customer-support help desk. ("Multi-tenant" = many customer companies share one
running system, each walled off from the others. Defined properly in Lesson 1.)

## The course map

Each phase of the build maps to a real category of support ticket.

| Lesson | Phase built | The ticket it teaches you to handle | Status |
|---|---|---|---|
| 0 | Foundation — Docker, Django, Postgres, Redis | *"The site is down."* Which tier is actually broken — frontend, backend, or database? | ⬜ not written |
| 1 | Domain model & multi-tenancy | *"My data is missing"* / *"I can see another company's data."* One is a bug, one is a breach | ⬜ not written |
| 2 | Auth — sessions, JWT, OAuth, roles | *"I can't log in."* The biggest support category. 401 vs 403: "who are you?" vs "I know you, and no" | ⬜ not written |
| 3 | Admin, impersonation, feature flags | Your own tooling. Impersonation is how you see what the customer sees; flags explain *"why does it work for them and not me?"* | ⬜ not written |
| 4 | Async — Celery, exports, scheduled email | *"My export never arrived."* Learning that queued is not the same as lost | ⬜ not written |
| 5 | AI assistant + MCP server | Assisted triage — and knowing its failure modes so you don't trust it blindly | ⬜ not written |
| 6 | Public API + webhooks + docs | *"Your webhook never fired."* The most common integration ticket there is | ⬜ not written |
| 7 / 7b | AWS deploy, CDN, origin protection | *"It works for you but not for me."* Stale caches and regional differences | ⬜ not written |
| 8 | Containers & Kubernetes | Reading logs and restarts when a container keeps dying | ⬜ not written |

## How an article is built

Articles are **compiled at the end of each phase**, not written during it. The
raw material is captured while building, in `docs/`:

| Source | Feeds which section |
|---|---|
| `docs/phase-N-*.md` — engineering notes | Build it, Verify it |
| `docs/concepts/NN-*.md` — plain-English concept notes | The problem, Concepts you need |
| `docs/adr/` — architecture decision records | Trade-offs & decisions |
| `docs/troubleshooting-log.md` — real errors, verbatim | What actually broke |
| `docs/known-gaps.md` — lab vs production | Production reality check |

Rough notes written in the moment are the honest ones. Polish comes later.

## Conventions

- **Every article starts as `draft: true`.** Nothing publishes without review.
- **One file per lesson**, numbered, in this folder: `NN-slug.md`.
- **Frontmatter is deliberately generator-neutral** — plain YAML that Astro,
  Hugo, Next and Jekyll can all read with minor field renaming. Once a static
  site generator is chosen, adapting the field names is a few minutes' work.
- **Errors are quoted verbatim**, never paraphrased, so they stay searchable for
  the reader who is hitting the same thing.
- **No assumed knowledge.** If a term appears for the first time, it gets a
  one-line plain-English definition right there.

Start a new article by copying [`_TEMPLATE.md`](_TEMPLATE.md).

# Phase 1 — Domain Model & Multi-Tenancy

**Status:** 🚧 In progress

**Goal:** model Deskly's core objects and enforce **tenant isolation** — an org
can only ever see its own data. This is what turns "a web app" into "a SaaS."

**Done when:** we can create two organizations, add tickets to each, and a
request scoped to Org A can never read Org B's tickets — proven by a test.

## Key concepts

- **Tenant** — one customer company using Deskly (e.g. "Acme Corp"). Analogy:
  an apartment building — shared plumbing (one app + DB), private units
  (isolated data).
- **Multi-tenancy** — many tenants share one running app and one database, but
  none can see another's data.
- **Migration** — a versioned, replayable description of a schema change. We
  never edit the DB by hand; migrations keep every environment in sync.

## Architecture decisions & trade-offs

### Isolation strategy: shared DB + shared schema + tenant column

| Strategy | Isolation | Cost | Chosen? |
|---|---|---|---|
| **Tenant column** (`organization_id` on every row) | Good (with discipline) | Cheapest, scales far | ✅ |
| Schema-per-tenant | Stronger | More ops overhead | |
| Database-per-tenant | Strongest | Most expensive | |

We use the **tenant column**: every tenant-scoped row carries an
`organization` foreign key; every query filters by it. It's what most SaaS
companies run (Slack, GitHub, Shopify started here). Its one weakness — a
*forgotten* filter leaks data — so the whole strategy is about **centralizing
the filter** so no one can forget it.

### Separate `organizations` app from domain apps

Tenant-defining models (`Organization`, `Membership`) live in their own app,
apart from domain models (`Ticket`, `Comment`). Tenancy is infrastructure every
other app depends on, so it sits at the bottom of the dependency graph — avoids
circular imports and keeps the boundary clear.

### Model choices

- **Route by `slug`, not numeric id** — human-readable URLs and doesn't leak
  customer count (sequential ids do). Cost: slugs must stay immutable once set.
- **`Membership` is an explicit join table** (not a plain M2M) because it
  carries the **role** on the relationship — a user can be Owner at one org and
  Viewer at another.
- **Roles as string `TextChoices`** — simplest for a fixed small set. Graduate
  to a Role table when roles become customer-customizable (the Phase 2 RBAC
  path).
- **Enforce invariants in the DB** — a `UniqueConstraint(organization, user)`
  prevents duplicate memberships even if application code has a bug/race.

## Build slices

- [ ] Slice 1 — `organizations` app: `Organization` + `Membership` models,
      registered in `INSTALLED_APPS`.
- [ ] Slice 2 — `tickets` app: `Ticket` + `Comment` with a `for_org` scoping
      manager; migrate; inspect tables.
- [ ] Slice 3 — tenant resolution (per-request org) + guard writes
      (never trust client-supplied `organization_id`).
- [ ] Slice 4 — `seed_demo` management command (two orgs with sample tickets).
- [ ] Slice 5 — isolation test proving Org A can't read Org B's data.

## How to verify (target)

- Seed creates Org A and Org B.
- A member of Org A lists only A's tickets; requesting Org B's slug is denied
  (404/403, not an empty list).
- Posting a ticket with `organization_id` set to B's id still lands in A.
- A test asserts the isolation so it can never silently regress.

## Gotchas

- Empty list where data should be → the org didn't resolve; base queryset
  correctly failed closed. Check the tenant-resolution layer.
- Cross-tenant leak in a new endpoint → someone used `Ticket.objects.all()`
  directly instead of `for_org`.

# ADR-0002 — Shared database with a tenant column for multi-tenant isolation

- **Status:** Accepted (implementation pending — Phase 1)
- **Date:** 2026-07-18
- **Phase:** 1

## Context

Deskly is **multi-tenant**: many customer companies use one running system.
"Acme Corp" and "Globex" both have tickets in Deskly, and neither may ever see
the other's. A leak here is not a bug report — it is a data breach, with
disclosure obligations attached.

**Broken access control sits at number one in the OWASP Top 10**, the industry's
ranked list of web application risks. This is the highest-stakes decision in the
entire build.

Three standard ways to keep tenants apart, cheapest and weakest first:

1. **Shared database, shared schema, tenant column** — every row carries an
   `organization_id`; every query filters on it.
2. **Schema per tenant** — one database, a separate set of tables per customer.
3. **Database per tenant** — complete physical separation.

## Decision

We will use a **shared database with a tenant column**. Every tenant-scoped
model carries an `organization` foreign key, and querying is centralised behind
a scoping manager (`for_org`) rather than left to each individual view.

The whole strategy rests on **centralising the filter**, because its one failure
mode is a developer forgetting it.

## Consequences

**Good**

- Cheapest to run and operate: one database, one connection pool, one migration
  to apply. Adding a customer is inserting a row, not provisioning
  infrastructure.
- Scales a long way. Slack, GitHub and Shopify all started here.
- Simple to reason about, and cross-tenant analytics stay easy.

**Bad**

- **Isolation depends on discipline, not physics.** Nothing at the database
  level stops a bad query returning another tenant's rows. Options 2 and 3 make
  a leak structurally impossible; this one makes it merely unlikely.
- The failure is **silent**. No crash, no error — just a row appearing where it
  shouldn't. Nothing alerts you. A customer finds it.
- "Noisy neighbour": one enormous customer's load affects everyone.
- A per-customer restore means extracting rows, not restoring a database.

**Risks to watch**

- Any use of `Ticket.objects.all()` instead of the scoped manager. This is the
  single thing to grep for in every review.
- Raw SQL and bulk operations bypassing the manager entirely.
- Missing index on `organization_id` — every query filters on it, so without an
  index performance collapses once a customer has serious volume.
- **Mitigation:** an automated isolation test asserting Org A cannot read Org B's
  data, so a regression fails the build rather than reaching a customer. Tracked
  as GAP-004.

## Alternatives considered

| Option | Why not |
|---|---|
| **Schema per tenant** | Stronger isolation, and a leak requires an explicit cross-schema query rather than a forgotten `WHERE`. But every migration must run against every schema, connection pooling gets complicated, and it strains past a few hundred tenants. Real operational overhead to buy protection a test can also provide. |
| **Database per tenant** | Strongest possible wall, and the honest answer for regulated data (health, financial) or a small number of large enterprise customers. Cost and operational load scale linearly with customers — wrong for a help desk aiming at many small tenants. |
| **Postgres Row-Level Security (RLS)** | Genuinely attractive: the database itself enforces the filter, so a forgotten `WHERE` fails closed. Rejected *for now* on learning grounds — it moves the security boundary into database policy, which is harder to reason about and debug when you are new to both Django and Postgres. Worth revisiting as a later ADR; it directly addresses this decision's main weakness. |

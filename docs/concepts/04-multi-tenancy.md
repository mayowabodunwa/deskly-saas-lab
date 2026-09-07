# 04 — Multi-tenancy (many customers, one system)

## The idea in one line
Many customers ("tenants") share one running system, each walled off so nobody
ever sees another tenant's data.

## Plain-English version
Like an apartment building: one building + shared plumbing (shared system), but
every tenant has a locked unit and your key only opens yours. A key that opens a
neighbour's flat = a data leak, the worst bug a multi-tenant SaaS can have.

## Three ways to keep tenants apart (cheap/weak → pricey/strong)
1. Shared everything, tag each row with tenant_id, always filter by it. Cheapest,
   most common. Danger: forget the filter once → leak everyone's data.
2. Separate schema per tenant. More separation, more upkeep.
3. Separate database per tenant. Strongest wall, most expensive to run.
Trade-off: more isolation = safer but pricier and harder to operate.

## Proof I ran
- Shared `tickets` table with tenant_id for 'acme' and 'globex'.
- SELECT ... WHERE tenant_id='acme' → only Acme's rows. Correct.
- SELECT * FROM tickets (no filter) → Globex's row appeared in Acme's list. Leak!
  No error, no crash — that's what makes it dangerous.

## The guardrail (don't rely on human memory)
- One choke-point in code that ALWAYS adds the tenant filter (Deskly's approach:
  a `for_org(org)` queryset + resolving the current org once per request).
- Never trust a client-supplied org id; derive it server-side from auth/URL.
- Postgres Row-Level Security (RLS): the DB itself only returns the tenant's rows.

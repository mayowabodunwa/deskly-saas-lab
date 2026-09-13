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

### Slice 2 model choices

- **`Comment` carries its own `organization`**, even though it could reach one
  through `ticket`. The rule is then uniform — *every* tenant-scoped table has
  the column — so a reviewer can check it mechanically, with no per-model
  exceptions, and comments can be filtered and indexed without a join. The cost
  is that the two could theoretically disagree (a comment stamped Org B
  pointing at Org A's ticket); nothing in the schema prevents that, so it is
  covered by test instead (see GAP note below).
- **`on_delete` is a business decision, not a technical one.** The same file
  answers it three different ways, each by asking what the business wants:
  `organization` → `CASCADE` (a customer leaves, their data goes — that is what
  "delete my data" means legally); `created_by` / `assignee` → `SET_NULL` (an
  employee leaves, the org keeps its support history; `CASCADE` here would be a
  data-loss incident triggered by an HR action); Slice 1's `Membership.user` →
  `CASCADE` (a membership without a user is meaningless).
- **`for_org` lives on a `QuerySet`, not a `Manager`,** so it chains:
  `Ticket.objects.for_org(org).filter(status="open")` works, and so does
  `.count()` after it. On a `Manager` it would work once and then dead-end —
  and a safety rail people cannot use in the middle of a query is a safety rail
  people route around.
- **No `created_by` yet.** There are no logins until Phase 2, so there is
  nothing to put in the field. Added when it can be filled in.

### Slice 3 — how a URL becomes a response

The mental model for the whole request path. **A view is simply the function a
URL is configured to call, and whatever it returns is what the caller receives.**
Nothing more mystical than that.

```
  curl /api/orgs/acme/tickets/
            │
            ▼
  config/urls.py                    the routing table — "which function handles this?"
    path("api/orgs/", include("apps.organizations.urls"))
            │  strips "api/orgs/", passes "acme/tickets/" onward
            ▼
  apps/organizations/urls.py
    path("<slug:slug>/", views.organization_detail)   ← tried first, needs the URL to END here
    path("<slug:slug>/", include("apps.tickets.urls"))  ← "acme/" captured as slug=acme
            │  strips "acme/", passes "tickets/" onward
            ▼
  apps/tickets/urls.py
    path("tickets/", views.ticket_list)
            │
            ▼
  apps/tickets/views.py
    def ticket_list(request, slug):        ← slug="acme", handed down from the outer pattern
        organization = get_object_or_404(Organization, slug=slug)   1. RESOLVE the tenant
        tickets = Ticket.objects.for_org(organization)              2. SCOPE the query
        return Response(TicketSerializer(tickets, many=True).data)  3. TRANSLATE to JSON
            │
            ▼
  HTTP/1.1 200 OK + JSON body
```

**Four things that model explains:**

- **`urls.py` is a lookup table, matched top to bottom, first match wins.** Two
  patterns can share a prefix: `<slug:slug>/` matches `/api/orgs/acme/` only
  when the URL *ends* there, so `/api/orgs/acme/tickets/` falls through to the
  `include` on the next line. Order is significant.
- **`<slug:slug>` is two different words.** The first is the *type* of value
  allowed (letters, digits, hyphens, underscores — never a `/`); the second is
  the *name* it arrives under in the view. They coincide here by choice.
  Captured values propagate through nested `include()`s, which is why
  `ticket_list` receives `slug` without asking for it.
- **A view returns a response; the return value *is* the API.** `Response({...})`
  builds JSON by hand — fine for a few fields. A **serializer** describes the
  translation once and handles both directions (row → JSON out, JSON → validated
  data in). `many=True` means "a list of these".
- **The routing table is built once at startup, not per request.** So a mistake
  in `urls.py` or `settings.py` prevents the process from booting at all.

**Order inside the view is the safety property.** Resolve first, scope second.
`for_org()` can never run without an organization to scope to, because the line
above it either produced one or ended the request with a 404.

### Slice 3 — status codes are part of the design

| Code | Meaning here | Why it was chosen |
|---|---|---|
| `200 OK` | found and returned | |
| `201 Created` | a POST made something new | distinct from 200 so the caller knows a resource now exists |
| `301 Moved Permanently` | trailing slash added | Django's `APPEND_SLASH`. Redirects are GET-only — a slash-less `POST` loses its body, a classic silent "the form submits but nothing saves" |
| `400 Bad Request` | serializer validation failed | the caller's input is wrong; nothing on the server is broken |
| `404 Not Found` | no such slug — **and, later, "not yours"** | see below |
| `500` | the server itself failed | should never be the answer to a bad URL |

**404 over 403 for another tenant's data.** `403 Forbidden` confirms the thing
exists. If a foreign org returns 403 while a nonsense slug returns 404, the
difference between the two answers enumerates the customer list — try `tesla`,
`stripe`, `monzo`, and the status code tells you who is a customer. Returning
404 for both reveals nothing. The rule: **never confirm the existence of
something the caller has no right to know about.**

`get_object_or_404` exists for exactly this. `Organization.objects.get()` raises
`DoesNotExist` → an unhandled 500, which claims the server broke when in fact
someone simply typed a bad URL. Wrong status codes send whoever is on call to
look in the wrong place.

*(Production nicety not yet applied: DRF's default 404 body,
`"No Organization matches the given query."`, names the model. Real deployments
flatten it to `"Not found."`)*

### Slice 3 — resolution is not authorization

Resolving the tenant from the URL answers *which* org the request concerns. It
does **not** answer whether the caller is entitled to it. With no authentication
until Phase 2, any caller can substitute any slug:

```
curl -i http://localhost:8000/api/orgs/globex/   →   200 OK, Globex's record
```

The app behaved correctly and still handed over another tenant's data, because
the URL was treated as both the question and the permission. Tracked as
**GAP-006 (🔴)**; closes in Phase 2, where the resolved org is checked against
the caller's `Membership`. Note that `for_org()` is no defence here — the filter
is applied perfectly, to the wrong org. The query was right; the question wasn't.

## Build slices

- [x] Slice 1 — `organizations` app: `Organization` + `Membership` models,
      registered in `INSTALLED_APPS`. **Verified 2026-09-07** — table shape
      confirmed in psql; duplicate `slug` and duplicate `(organization, user)`
      both rejected by Postgres with `IntegrityError`.
- [x] Slice 2 — `tickets` app: `Ticket` + `Comment` with a `for_org` scoping
      manager; migrate; inspect tables. **Verified 2026-09-10** — tables
      created and inspected in psql; the cross-tenant leak reproduced
      deliberately in the Django shell, then closed with `for_org`.
- [x] Slice 3 — tenant resolution (per-request org) + guard writes
      (never trust client-supplied `organization_id`). **Verified 2026-09-14** —
      `/api/orgs/<slug>/tickets/` returns only that org's tickets; a POST to
      Acme's URL carrying `"organization": 3` still lands in Acme. The
      vulnerable variant was built deliberately, shown to leak into Globex, then
      reverted and the planted rows deleted by id. Authorization is **not** done
      — GAP-006 stays open until Phase 2.
- [ ] Slice 4 — `seed_demo` management command (two orgs with sample tickets).
- [ ] Slice 5 — isolation test proving Org A can't read Org B's data.

## How to verify (target)

- Seed creates Org A and Org B.
- A member of Org A lists only A's tickets; requesting Org B's slug is denied
  (404/403, not an empty list).
- Posting a ticket with `organization_id` set to B's id still lands in A.
- A test asserts the isolation so it can never silently regress.

## Commands used

```bash
# create the app (bind mount means files appear on the host immediately)
docker compose exec backend mkdir -p apps/organizations
docker compose exec backend python manage.py startapp organizations apps/organizations

# schema changes: write the file, then apply it
docker compose exec backend python manage.py makemigrations organizations
docker compose exec backend python manage.py migrate

# inspect the real table, not Django's idea of it
docker compose exec db psql -U deskly -d deskly -c "\d organizations_membership"
```

Slice 2 followed the same shape:

```bash
docker compose exec backend mkdir -p apps/tickets
docker compose exec backend python manage.py startapp tickets apps/tickets
# add "apps.tickets" to INSTALLED_APPS, then:
docker compose exec backend python manage.py makemigrations tickets
docker compose exec backend python manage.py migrate
docker compose exec db psql -U deskly -d deskly -c "\d tickets_ticket"
```

Reproducing the leak, in `manage.py shell`:

```python
from apps.organizations.models import Organization
from apps.tickets.models import Ticket
acme = Organization.objects.get(slug="acme")
globex = Organization.objects.get(slug="globex")
Ticket.objects.create(organization=acme, subject="Printer won't work")
Ticket.objects.create(organization=globex, subject="Globex merger plans")

# what the buggy page does — returns BOTH companies' tickets
list(Ticket.objects.values_list("organization__slug", "subject"))

# what it should do
list(Ticket.objects.for_org(acme).values_list("organization__slug", "subject"))
```

```bash
# Slice 3 — tenant resolution over HTTP
docker compose up -d db backend

# resolve an org from the URL
curl -i http://localhost:8000/api/orgs/acme/

# status codes worth seeing side by side
curl -i http://localhost:8000/api/orgs/globex/         # 200 — and see GAP-006
curl -i http://localhost:8000/api/orgs/nosuchcompany/  # 404
curl -i http://localhost:8000/api/orgs/acme            # 301 -> /api/orgs/acme/

# tenant-scoped ticket lists
curl http://localhost:8000/api/orgs/acme/tickets/      # 2 tickets
curl http://localhost:8000/api/orgs/globex/tickets/    # 1 ticket

# when the server goes silent, read its last words
docker compose logs --tail=40 backend
```

## Gotchas

- **`curl: (52) Empty reply from server`** → the server is *dead*, not unhappy.
  A 404 or 500 means the process is alive and answering; silence means it never
  finished booting. `urls.py` and `settings.py` are imported once at startup to
  build the routing table, so an error there stops the process before it can
  serve anything — including an error page. Only the container logs hold the
  reason: `docker compose logs --tail=40 backend`. First move on silence is
  always the logs, never another curl.
- **Read a traceback from the bottom.** The last line is the error
  (`NameError: name 'include' is not defined`); the lowest line naming a file
  under `/app/` is where it happened. Everything between is framework
  scaffolding. Real instance: adding `include(...)` to
  `organizations/urls.py` without adding it to
  `from django.urls import path` — one missing word took the whole server down.
- **A redirect drops a POST body.** `APPEND_SLASH` turns `/api/orgs/acme` into a
  301 to `/api/orgs/acme/`. Harmless for GET, silent data loss for POST. Always
  write the trailing slash.
- Empty list where data should be → the org didn't resolve; base queryset
  correctly failed closed. Check the tenant-resolution layer.
- **Cross-tenant leak in a new endpoint** → someone used `Ticket.objects.all()`
  directly instead of `for_org`. Reproduced deliberately in Slice 2. Three
  things make this the access-control failure that actually reaches production:
  the dangerous call is the *shorter, more natural* one that every Django
  tutorial teaches first; it raises no error, because the code does exactly
  what it says — it just answers a different question than intended; and with
  one tenant in a dev database the safe and unsafe queries return identical
  results, so it stays invisible until a second customer exists. Adding
  `for_org` does **not** remove `.objects.all()` — the dangerous path is still
  there. That is why the mitigation is a test (Slice 5), not a convention.
- **N+1 queries on reverse relations.** `[m.organization.name for m in
  user.memberships.all()]` costs 1 query for the memberships plus 1 *per row*
  to fetch each organization. Invisible with test data, fatal at scale — the
  cause of "slow for one customer only" tickets. Fix: `select_related` for
  forward (one) relations, `prefetch_related` for reverse (many) relations.
  Measure with `reset_queries()` + `len(connection.queries)` (needs `DEBUG=1`).
- **Id sequences have gaps.** A failed insert still consumes its id — Postgres
  allocates the number before checking constraints, and does not give it back.
  Acme is id 1 and Globex id 3 because a rejected duplicate ate id 2. Never
  read "highest id" as "row count", and never expose ids as a customer count —
  a second argument for routing by `slug` (see ADR-0002).
- **Django auto-indexes every foreign key.** You will see indexes in `\d` that
  you never declared. Useful, but not free: each index slows writes slightly
  and costs disk.

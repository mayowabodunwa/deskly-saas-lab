# Phase 1 — Domain model & multi-tenancy

**Goal:** model Deskly's core objects and enforce **tenant isolation** — an org can only ever see its own data. This is the concept that separates "a web app" from "a SaaS."

**Done when:** you can create two organizations, add tickets to each, and a request scoped to Org A can never read Org B's tickets — proven by a test.

## Concepts to teach here

- **What multi-tenancy means.** Many customer companies ("tenants") share one running app and one database, but their data is invisible to each other. Analogy: an apartment building — shared plumbing, private units.
- **Isolation strategies (pick one, explain the menu):**
  - *Shared DB, shared schema, tenant column* (what we use): every row has an `organization_id`; every query filters by it. Simplest, cheapest, scales far. The risk is a forgotten filter leaking data — so we centralize the filtering.
  - *Shared DB, schema-per-tenant* (e.g. `django-tenants`): stronger isolation, more ops overhead.
  - *DB-per-tenant:* strongest isolation, most expensive. Overkill for a lab.
  Teach why we chose the first and when a real company graduates to the others.
- **Migrations.** A migration is a versioned, replayable description of a schema change. Never edit the DB by hand; always go through migrations so every environment converges to the same schema.

## Build steps (vertical slice)

1. **Create the `organizations` and `tickets` apps.** Keep tenant-defining models (`Organization`, `Membership`) separate from domain models (`Ticket`, `Comment`).
2. **Model the objects** from `product-spec.md`. Every tenant-scoped model gets `organization = models.ForeignKey(Organization, ...)`. Add DB indexes on `organization` and common filters (`status`, `created_at`).
3. **Centralize tenant scoping** so no view has to remember the filter. Two complementary layers:
   - A custom manager/queryset: `Ticket.objects.for_org(org)` returns only that org's rows.
   - Resolve the "current org" once per request (from the URL, e.g. `/api/orgs/<slug>/tickets/`, or from the user's active membership) in middleware or a DRF permission/mixin, and reuse it.
4. **Guard writes too.** On create, always set `organization` from the resolved tenant — never trust an `organization_id` sent by the client. This is the classic IDOR/tenant-leak bug; make the learner feel why.
5. **Seed data.** A management command (`seed_demo`) that creates two orgs with sample tickets, so every later phase has data to work with.

Representative scoping (let them adapt):

```python
# organizations/models.py
class Organization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    plan = models.CharField(max_length=20, default="free")

# tickets/models.py
class TicketQuerySet(models.QuerySet):
    def for_org(self, org):
        return self.filter(organization=org)

class Ticket(models.Model):
    organization = models.ForeignKey("organizations.Organization",
                                     on_delete=models.CASCADE, related_name="tickets")
    subject = models.CharField(max_length=300)
    status = models.CharField(max_length=20, default="open", db_index=True)
    # ...
    objects = TicketQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["organization", "status"])]
```

```python
# a DRF viewset always scopes by the resolved org
class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    def get_queryset(self):
        return Ticket.objects.for_org(self.request.organization)
    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)  # never from client input
```

## Verify

- Create Org A and Org B via the seed command.
- As a member of Org A, `GET /api/orgs/orgA/tickets/` lists only A's tickets; requesting Org B's slug is denied (404/403, not an empty list — teach why "not found" can be the safer signal).
- Attempting to `POST` a ticket with `organization_id` set to B's id still lands in A (server ignores client-supplied org).
- A test asserts the isolation so it can never silently regress.

## Best practices to call out

- **Deny by default.** The base queryset returns nothing until scoped to an org. A missing filter should fail closed (no rows), never leak everything.
- **Never trust client-supplied tenant identifiers.** Derive the org server-side from auth/session/URL.
- **Index the tenant column** and composite indexes for hot query paths — multi-tenant tables get large.
- **One migration per logical change**, reviewed like code. Check migrations into git.
- **Write the isolation test now.** Tenant leaks are the highest-severity SaaS bug; a test is cheap insurance.

## Canonical docs

- Django models & migrations: https://docs.djangoproject.com/en/stable/topics/db/models/ and https://docs.djangoproject.com/en/stable/topics/migrations/
- Custom managers/querysets: https://docs.djangoproject.com/en/stable/topics/db/managers/
- DRF viewsets: https://www.django-rest-framework.org/api-guide/viewsets/
- (Reference for the harder strategy) django-tenants: https://django-tenants.readthedocs.io/

## Common issues (lab copilot fodder)

- **Empty list where data should be** → the org didn't resolve; the base queryset correctly failed closed. Check the tenant-resolution layer.
- **Cross-tenant leak in a new endpoint** → someone used `Ticket.objects.all()` directly. Reinforce: always go through `for_org`.
- **`related_name` clashes / migration conflicts** → two developers' migrations diverge; teach `makemigrations --merge` and keeping migrations small.

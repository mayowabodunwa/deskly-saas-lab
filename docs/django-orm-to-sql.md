# Django ORM → SQL — a Deskly cheat sheet

**What this is:** a translation table. Every line of Django you write becomes a
SQL string that gets sent to Postgres. This page shows which becomes which,
using Deskly's own models (`Organization`, `Ticket`, `Comment`).

**Why it exists:** written during Phase 1 Slice 2, right after inspecting the
real tables in `psql`. Seeing `organization_id` hold the number `1` instead of
the word "Acme" is what makes the rest of this page make sense.

## The one idea

Django's **ORM** (Object-Relational Mapper) maps Python objects onto database
rows. You never write SQL — but SQL is always what runs. Knowing the mapping is
the difference between "the query is slow" and "I know which query is slow and
why".

---

## Reading rows

| Django | SQL it becomes |
|---|---|
| `Ticket.objects.all()` | `SELECT * FROM tickets_ticket` |
| `Ticket.objects.for_org(acme)` | `... WHERE organization_id = 1` |
| `Ticket.objects.filter(status="open")` | `... WHERE status = 'open'` |
| `Ticket.objects.exclude(status="closed")` | `... WHERE NOT (status = 'closed')` |
| `Ticket.objects.filter(organization=acme, status="open")` | `... WHERE organization_id = 1 AND status = 'open'` |
| `Ticket.objects.get(id=1)` | `... WHERE id = 1` — raises `DoesNotExist` on zero, `MultipleObjectsReturned` on 2+ |
| `Ticket.objects.first()` | `... ORDER BY created_at DESC LIMIT 1` |
| `Ticket.objects.count()` | `SELECT COUNT(*) FROM tickets_ticket` |
| `Ticket.objects.exists()` | `SELECT 1 FROM tickets_ticket LIMIT 1` |
| `Ticket.objects.all()[:5]` | `... LIMIT 5` |
| `Ticket.objects.order_by("subject")` | `... ORDER BY subject ASC` |
| `Ticket.objects.order_by("-created_at")` | `... ORDER BY created_at DESC` |
| `Ticket.objects.values_list("subject", flat=True)` | `SELECT subject FROM ...` |

Note: `Ticket.Meta.ordering = ["-created_at"]` means an `ORDER BY` is appended
to *every* ticket query whether you asked for one or not.

## Matching on part of a value

Django uses **double underscores** where SQL uses operators and keywords. Read
`__` as "dot": `subject__icontains` = "subject, contains-ignoring-case".

| Django | SQL |
|---|---|
| `filter(subject__icontains="printer")` | `WHERE subject ILIKE '%printer%'` |
| `filter(subject__startswith="P")` | `WHERE subject LIKE 'P%'` |
| `filter(status__in=["open", "pending"])` | `WHERE status IN ('open','pending')` |
| `filter(created_at__gte=yesterday)` | `WHERE created_at >= ...` |
| `filter(body__isnull=True)` | `WHERE body IS NULL` |
| `filter(Q(status="open") \| Q(status="pending"))` | `WHERE status='open' OR status='pending'` |

Plain `filter(a=1, b=2)` always means `AND`. You need `Q` objects to get `OR`.

## Following relationships

Deskly's links: `Ticket.organization` → `Organization`, `Comment.ticket` →
`Ticket`, `Comment.organization` → `Organization`.

| Django | SQL |
|---|---|
| `ticket.organization` | a **second** `SELECT` against organizations |
| `acme.tickets.all()` | `SELECT * FROM tickets_ticket WHERE organization_id = 1` |
| `Ticket.objects.select_related("organization")` | one `SELECT` with a `JOIN` |
| `acme.tickets.prefetch_related("comments")` | two queries; the second is `WHERE ticket_id IN (1,2,…)` |
| `Ticket.objects.filter(organization__slug="acme")` | `JOIN organizations_organization … WHERE slug = 'acme'` |

**The N+1 rule of thumb:**
`select_related` for **forward** relations (a ticket → its one org — a `JOIN`).
`prefetch_related` for **reverse** relations (an org → its many tickets — a
second query). Without them, looping over 100 tickets and touching
`.organization` fires 101 queries.

## Writing rows

| Django | SQL |
|---|---|
| `Ticket.objects.create(...)` | `INSERT INTO tickets_ticket ...` |
| `t.save()` on a new object | `INSERT` |
| `t.save()` on an existing object | `UPDATE ... WHERE id = 1` — rewrites **every** column |
| `Ticket.objects.filter(...).update(status="closed")` | one `UPDATE ... WHERE ...` across all matching rows |
| `t.delete()` | `DELETE FROM tickets_ticket WHERE id = 1` |
| `Ticket.objects.filter(...).delete()` | `DELETE ... WHERE ...` (plus cascades) |
| `Ticket.objects.get_or_create(...)` | a `SELECT`, then an `INSERT` only if nothing matched |
| `Ticket.objects.bulk_create([...])` | one multi-row `INSERT` |

**Trap:** queryset `.update()` is one fast query, but it goes *around* the model
rather than through it — `auto_now` on `updated_at` does not fire, and custom
`save()` logic is skipped.

**Trap:** `.delete()` on a queryset still honours `on_delete=CASCADE`, so
deleting an Organization takes its tickets and comments with it.

## Querysets are lazy

```python
tickets = Ticket.objects.for_org(acme)   # nothing has hit the database yet
print(tickets)                           # NOW the query runs
```

Building a query only writes the sentence; the database is touched when the
answer is actually needed (printing, iterating, `len()`, slicing to a value).
That laziness is why filters chain:

```python
Ticket.objects.for_org(acme).filter(status="open").order_by("-created_at")[:10]
```

All of that collapses into **one** query with `WHERE`, `ORDER BY` and `LIMIT`.

---

## How to see the SQL yourself

Never guess. Add `.query` to any queryset:

```bash
docker compose exec backend python manage.py shell
```

```python
from apps.tickets.models import Ticket
from apps.organizations.models import Organization

acme = Organization.objects.get(slug="acme")
print(Ticket.objects.for_org(acme).filter(status="open").query)
```

To count queries (catches N+1), with `DEBUG=1`:

```python
from django.db import connection, reset_queries
reset_queries()
[t.organization.name for t in Ticket.objects.all()]
print(len(connection.queries))    # 1 + one per ticket = N+1
```

## Or look at the tables directly

```bash
docker compose up -d db
docker compose exec db psql -U deskly -d deskly
```

```sql
\dt                                  -- list tables
\d tickets_ticket                    -- describe one table, incl. indexes
SELECT id, organization_id, subject, status FROM tickets_ticket;
\q                                   -- quit
```

Table names are `appname_modelname`, lowercase — so the `Ticket` model in the
`tickets` app becomes `tickets_ticket`.

## Why the column is called `organization_id`

In `models.py` you write `organization`. The real column is `organization_id`.
Django names it honestly: the column does not hold an Organization, it holds
that organization's **id number**.

Verified in Phase 1 Slice 2 — the tickets table contains no company names at
all, only `1`, `1`, `3`:

```
 id | organization_id |              subject               | status
----+-----------------+------------------------------------+--------
  1 |               1 | Printer won't work                 | open
  2 |               1 | Password reset                     | open
  3 |               3 | Globex merger plans - confidential | open
```

**That column of numbers is the only thing separating two customers.** Acme's
and Globex's rows sit adjacent in the same table.

## The security punchline

```sql
SELECT * FROM tickets_ticket;                          -- Ticket.objects.all()
SELECT * FROM tickets_ticket WHERE organization_id=1;  -- Ticket.objects.for_org(acme)
```

`for_org()` is not a wall, a firewall, or a permission system. **It is one
`WHERE` clause.** The cross-tenant leak reproduced in Slice 2 was simply that
clause being absent — a query that runs fine, raises nothing, and looks
completely ordinary in review. That is why the mitigation is an automated test
(Slice 5), not a convention.

## Official docs

- Making queries — https://docs.djangoproject.com/en/stable/topics/db/queries/
- QuerySet API reference — https://docs.djangoproject.com/en/stable/ref/models/querysets/
- Field lookups (`__icontains`, `__in`, …) — https://docs.djangoproject.com/en/stable/ref/models/querysets/#field-lookups
- Database optimization — https://docs.djangoproject.com/en/stable/topics/db/optimization/

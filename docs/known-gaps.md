# Known Gaps — lab shortcuts vs. production

Deskly is a **learning lab**. To keep the build moving we take shortcuts that a
real production system would not. This file makes every one of them visible.

In industry this is a **risk register**: the deliberate, documented list of
"we know, we chose this, here's when it stops being acceptable." The
professional failure is not taking a shortcut — it's taking one silently and
forgetting.

Each gap records: what we did, what production does, why it matters, and the
**trigger** — the moment it must be closed.

| Severity | Meaning |
|---|---|
| 🔴 Critical | Would be a breach or outage in production. Must close before any real user. |
| 🟠 Important | Real risk, but survivable briefly. Close before launch. |
| 🟡 Minor | Hygiene and maintainability. Close when convenient. |
| ✅ Closed | Fixed. Entry kept, never deleted — the reasoning is the record. |

---

## 🔴 GAP-001 — `SECRET_KEY` has an insecure default

**Where:** `backend/config/settings.py:11`

```python
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
```

**What production does:** loads the key from a secrets manager (AWS Secrets
Manager, Vault) and **fails to start** if it is missing. No fallback value ever.

**Why it matters:** Django uses `SECRET_KEY` to cryptographically sign session
cookies and password-reset tokens. Anyone who knows the key can **forge a
session cookie and log in as any user, including an admin**. A default value
committed to a public repo is a published master key.

**Trigger to close:** before the app is reachable by anyone but you — Phase 7
(AWS deploy) at the very latest.

**Course value:** perfect illustration of *"the vulnerability isn't exotic — it's
a default nobody changed."*

---

## 🟠 GAP-002 — `DEBUG` and `ALLOWED_HOSTS` default to permissive

**Where:** `backend/config/settings.py:12-13`

```python
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")
```

**What production does:** `DEBUG = False` always, and an explicit list of real
hostnames.

**Why it matters:** with `DEBUG = True`, a crash renders a full error page
showing source code, local variables, and settings — Django redacts some
secrets, but it leaks far more than any stranger should see. `ALLOWED_HOSTS = "*"`
disables Django's check that a request was actually addressed to your site,
which enables host-header attacks (poisoned password-reset links pointing at an
attacker's domain).

**Trigger to close:** Phase 7, or the first time anything is exposed beyond
localhost.

---

## 🟠 GAP-003 — Secrets live in a local `.env` file

**Where:** `.env` (gitignored), read by `docker-compose.yml`

**What production does:** a managed secrets store with access control, audit
logging, and rotation.

**Why it matters:** `.env` is plaintext on disk, readable by anything running as
you, easy to email or paste by accident, and with no record of who read it. It
is genuinely the right choice for local development — the risk is that it
quietly follows the project into deployment.

**Trigger to close:** Phase 7.

---

## 🟡 GAP-004 — No automated tests or CI yet

**Where:** repo-wide. `make test` exists; nothing runs it automatically.

**What production does:** every push runs tests, linting and a security scan
before merge; failures block the pull request.

**Why it matters:** without an automatic gate, a regression is only caught by
whoever notices. **Phase 1 raises the stakes sharply** — the tenant-isolation
test is the control that stops a cross-customer data leak, and a test nobody
runs protects nobody.

**Trigger to close:** end of Phase 1, alongside the isolation test. This is the
first gap we should actually close.

---

## 🟡 GAP-005 — Postgres published on a host port

**Where:** `docker-compose.yml`, `ports: ["5433:5432"]`

**What production does:** the database sits on a private network with no public
route. Access is via a bastion host or a VPN, never a published port.

**Why it matters:** publishing the port makes the database reachable from your
whole machine and, depending on firewall settings, potentially your local
network. Convenient for connecting a GUI client during development; an open
door in any shared environment.

**Trigger to close:** Phase 7. (Fine locally — worth knowing it is a local-only
convenience.)

---

## 🔴 GAP-006 — Tenant resolution has no authorization behind it

**Where:** `backend/apps/organizations/views.py`, `backend/apps/organizations/urls.py`

```python
@permission_classes([AllowAny])
def organization_detail(request, slug):
    organization = get_object_or_404(Organization, slug=slug)
```

**What we did:** the current organization is resolved from the URL
(`/api/orgs/<slug>/`). That answers *which* tenant the request concerns — and
nothing else. Any caller can substitute any slug and receive that
organization's data.

Demonstrated in Phase 1 Slice 3 from an unauthenticated shell:

    curl -i http://localhost:8000/api/orgs/globex/
    HTTP/1.1 200 OK
    {"id":3,"name":"Globex","slug":"globex","plan":"free"}

**What production does:** resolution and authorization are two separate steps,
both mandatory. After resolving the org from the URL, the server checks that the
**authenticated** caller holds a `Membership` in it, and returns 404 if not.
The URL is treated as a *request* for a tenant, never as proof of entitlement.

**Why it matters:** this is the highest-severity bug class in SaaS — horizontal
privilege escalation / IDOR. It needs no tooling and no skill to exploit: a
customer edits the company name in their address bar and reads a competitor's
data. `for_org()` does not help here, because the filter is applied faithfully
to the *wrong* org. The query is correct; the question was not.

**Why it is open:** authentication does not exist until Phase 2, so there is no
"who is asking" to check a membership against. Closing it requires logins first.

**Trigger to close:** Phase 2, in the same slice that introduces sessions/JWT.
The `Membership` model (Slice 1) already holds exactly the fact the check needs.
Nothing may be exposed beyond localhost until this is closed.

**Course value:** the cleanest possible demonstration that **resolution is not
authorization** — the app correctly identified the tenant and still handed over
the data. Pairs with the "I can see another company's data" support ticket that
frames the Phase 1 article.

---

## 🟠 GAP-007 — `Comment.organization` can drift from `comment.ticket.organization`

**Where:** `backend/apps/tickets/models.py`

`Comment` stores `organization` directly *and* reaches the same fact through
`ticket.organization`. Nothing in the schema forces the two to agree, so a
comment can claim to belong to Acme while hanging off a Globex ticket.

**What production does:** enforces the invariant — validation in `save()`/
`clean()`, a database `CheckConstraint` or trigger, or by not duplicating the
column at all and accepting the join.

**Why it matters:** the duplicated column was added so comment queries can
filter by tenant without joining through tickets. That speed is only safe while
the copies agree. If they diverge, the two tenant-scoped queries return
*different* answers for the same comment — and one of them leaks it into the
wrong org's view.

**Trigger to close:** Phase 1 Slice 5, alongside the isolation test — the same
test file should assert a mismatched comment is rejected.

---

## 🟡 GAP-008 — Editor cannot see the container's installed packages

**Where:** developer tooling; `.devcontainer/backend/devcontainer.json`

Dependencies are installed inside the `backend` image, not on the host. A VS Code
session running on the host reports false errors such as
`Import "rest_framework.permissions" could not be resolved` on code that runs
correctly, and there are no Django type stubs, so Pylance also flags real runtime
attributes (e.g. `ticket_id`).

**What production teams do:** develop inside the container (Dev Containers) so
the editor and the runtime share one interpreter, and add `django-stubs` for
accurate type information.

**Why it matters:** false alarms train you to ignore the editor, which is exactly
when it catches a genuine typo. Harmless to the running app; corrosive to the
feedback loop.

**Trigger to close:** whenever the noise becomes annoying. No production impact.

---

## ✅ GAP-009 (closed 2026-09-20) — `seed_demo` was not wrapped in a transaction

**Closed by:** adding `from django.db import transaction` and decorating
`handle()` with `@transaction.atomic`, so the command either completes or leaves
the database untouched.

**Evidence:** the code change only — `make seed` runs clean. The rollback was
**not** demonstrated by forcing a mid-run failure, so the guarantee is taken on
the decorator's word rather than observed. Worth proving the first time this
command is changed.

The original entry is kept below, unedited, because the reasoning is the part
worth reading.

**Where:** `backend/apps/core/management/commands/seed_demo.py` — `handle()`

Django does **not** run a management command inside a database transaction by
default. `handle()` writes organizations first and tickets second, so a failure
partway through leaves everything already written in place and nothing rolled
back. The database is left in a state that is neither "before" nor "after".

This is survivable here only because every write uses `get_or_create`, so simply
running the command again reconciles whatever is missing. That is a property of
this particular command, not a general safety net.

**What production teams do:** wrap the whole unit of work in
`@transaction.atomic`, so it either completes or leaves the database untouched:

```python
from django.db import transaction

class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        ...
```

Anything that seeds or migrates real data does this as a matter of course, and
usually pairs it with `--dry-run` and an explicit `--flush` rather than letting
the command guess.

**Why it matters:** "all or nothing" is the guarantee that makes a failed run
safe to retry. Without it, a crash halfway through is a partially-populated
database that looks fine until something reads the half that never arrived — and
the symptom appears far away from the cause. For support work this is the shape
behind "the import said it failed but some of the records are there."

**Trigger to close:** the moment any seeding or data-fix command runs against
data someone cares about — a shared staging database, or anything beyond one
developer's laptop. Also close it immediately if a write is ever added that is
**not** idempotent, since the re-run repair strategy stops working at that point.

---

<!-- New gaps: assign the next GAP-NNN, pick a severity, and always fill in the
     trigger. A gap with no trigger becomes permanent by accident. -->

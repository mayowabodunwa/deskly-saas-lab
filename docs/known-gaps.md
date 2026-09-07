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

<!-- New gaps: assign the next GAP-NNN, pick a severity, and always fill in the
     trigger. A gap with no trigger becomes permanent by accident. -->

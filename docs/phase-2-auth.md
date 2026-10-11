# Phase 2 — Auth: logins, roles and tokens

**Status:** 🚧 In progress (branch `phase-2-auth`, started 2026-10-07)

**Goal:** Deskly knows **who** is making each request, and only lets them see
and do what their company and role allow.

**Done when:**

- A person can log in, and the app knows who they are.
- Someone who isn't a member of a company can't see that company's data. This
  closes **GAP-006** 🔴.
- A **viewer** is refused when they try to create a ticket, and an **agent** is
  allowed. A test locks this in.
- The web app's writes are protected against cross-site request forgery.
- A script can call the API with a token instead of a login cookie.
- (Optional, needs a Google account) "Sign in with Google" works.

**Support ticket this phase teaches:** *"I can't log in"*, and the difference
between `401` ("who are you?") and `403` ("I know who you are, and no").

## Key concepts

- **Authentication (AuthN)**: working out *who* is making a request.
- **Authorization (AuthZ)**: deciding what that person is *allowed* to do.
- **Password hash**: a scrambled fingerprint of a password that can't be turned
  back into it. Deskly stores the hash, never the password. At login, Django
  hashes what was typed and compares the two fingerprints.
- **Salt**: a random string mixed in before hashing, different for every user.
  Two people with the same password get different hashes, so cracking one
  doesn't reveal the other.
- **Session**: the coat-check model. At login, the server writes a note
  ("ticket `olr9…` belongs to adam") to the `django_session` table and gives the
  browser the ticket number as a cookie called `sessionid`. The browser shows
  the ticket on every request; the server looks up the note.
- **The server decides, not the cookie.** A cookie with no matching note is
  just a random string. Deleting the note logs the person out at once, even
  though they still hold the cookie.

## Architecture decisions & trade-offs

### Slice 1 — one demo person per access rule

`seed_demo` creates four users, each there to test one rule later in the phase:

| User | Company | Role | Tests |
|---|---|---|---|
| olivia | Acme | owner | owner-only actions |
| adam | Acme | agent | agents can write |
| vera | Acme | viewer | viewers can't write (Slice 3) |
| gary | Globex | agent | can't see another company (Slice 2) |

All share the password `deskly-demo`. A password written into code is only
acceptable because this command makes throwaway local data.

- **`get_user_model()`, not `from django.contrib.auth.models import User`.** It
  returns whatever user model the project uses, so a later custom user model
  doesn't break this code.
- **`update_or_create` for memberships.** `get_or_create` would leave a changed
  role alone; `update_or_create` puts it back. The seed file is the source of
  truth for demo data, so manual role edits don't survive a reseed. That's
  deliberate.
- **`check_password()` before `set_password()`.** Calling `set_password()` every
  run made a new salted hash every run, and Django logs a user out everywhere
  when their stored password changes. Now the seed only touches a password that
  is wrong. See the troubleshooting log, 2026-10-11.

### Slice 1 — a separate `accounts` app

Login, `/api/me/`, and later JWT and Google sign-in live in `apps/accounts/`.
`core` holds infrastructure (health check, seed command); auth is its own area
and will grow through Slices 5 and 6. Cost: one more folder.

### Slice 1 — sessions for the web app

Django's built-in session login: `authenticate()` checks the password,
`login()` writes the note and sets the cookie. Chosen over tokens for the
browser because:

- the browser stores and sends the cookie itself, and the cookie is `HttpOnly`,
  so scripts on the page can't read it;
- the server can end a session instantly by deleting its row.

Costs: the server has to store sessions (one row per login), and because the
browser sends the cookie automatically, writes need CSRF protection (Slice 4).

### Slice 1 — what the login endpoint says, and doesn't say

- **One vague error for both mistakes.** `"Invalid username or password."`
  never says which half was wrong. "No such user" would let an attacker find
  out which usernames exist.
- **400 for a failed login.** 400 means "this login attempt failed". 401 is kept
  for "this page needs you to be logged in".
- **No logout yet.** A logout is a write made with a session cookie, so it
  needs CSRF. It arrives in Slice 4.

### Slice 1 — why an anonymous request gets 403, not 401

With no `REST_FRAMEWORK` settings, DRF uses session login first, then Basic
auth. For an anonymous request, DRF chooses the status from the **first**
method only. A correct 401 must include a `WWW-Authenticate` header telling the
client how to log in, and session login has none (you can't ask a client for a
cookie). So DRF sends 403, with the body
`"Authentication credentials were not provided."`

Left as-is on purpose. In Slice 5, JWT login *does* send
`WWW-Authenticate: Bearer`, and the order we list the methods in will decide
401 or 403. The choice belongs there.
Docs: <https://www.django-rest-framework.org/api-guide/authentication/#unauthorized-and-forbidden-responses>

## Build slices

- [x] Slice 1 — **Log in with a session.** Demo users with memberships; a
      login endpoint; `/api/me/` answers "who am I?". Done 2026-10-11.
- [ ] Slice 2 — **Members only.** The company in the URL must be one the user
      belongs to. Closes GAP-006.
- [ ] Slice 3 — **Roles.** Viewers can read but not write; agents and owners
      can write. Permission tests.
- [ ] Slice 4 — **CSRF for the web app.** The browser proves a write came from
      Deskly's own pages.
- [ ] Slice 5 — **Tokens for scripts (JWT).** Short-lived access tokens plus
      refresh, and login throttling.
- [ ] Slice 6 — **Sign in with Google (OAuth).** Optional; needs a Google Cloud
      project.

Each slice: build it → break it on purpose → diagnose from symptoms → fix.

### Slice 1 — the breaks

1. **A user created without `set_password()`.** `User.objects.create(username="bob",
   password="deskly-demo")` stored the password as plain text. bob could never
   log in (`authenticate()` returned `None` even with the right password), and
   his password was readable by anyone who could read the table. Fixed with
   `set_password()`.
2. **A fake cookie.** `sessionid=fakefake…` got no error: Deskly found no note
   and treated the request as a stranger.
3. **Deleting the note.** Removing adam's row from `django_session` logged him
   out at once, while his real cookie stayed on his machine.
4. **Reseeding.** `make seed` logged out every demo user, though no password
   changed. Fixed with `check_password()` (see above).

## How to verify

Slice 1:

```bash
curl -i http://localhost:8000/api/me/
# 403, {"detail":"Authentication credentials were not provided."}

curl -i -c /tmp/deskly-cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"username": "adam", "password": "deskly-demo"}' \
  http://localhost:8000/api/auth/login/
# 200, Set-Cookie: sessionid=...; HttpOnly; SameSite=Lax

curl -i -b /tmp/deskly-cookies.txt http://localhost:8000/api/me/
# 200, {"username":"adam","memberships":[{"org":"acme","role":"agent"}]}

make seed
curl -s -b /tmp/deskly-cookies.txt http://localhost:8000/api/me/
# still adam: reseeding no longer logs people out
```

Every healthy row in `auth_user.password` starts with `pbkdf2_sha256$`.

## Commands used

```bash
# Slice 1: the accounts app
mkdir backend/apps/accounts
docker compose exec backend python manage.py startapp accounts apps/accounts
# then: name = "apps.accounts" in apps.py, and "apps.accounts" in INSTALLED_APPS

# psql inside the container, on the deskly database (not your Mac's Postgres)
docker compose exec db psql -U deskly deskly
```

```sql
-- who belongs where
SELECT u.username, o.slug, m.role
FROM organizations_membership m
JOIN auth_user u ON u.id = m.user_id
JOIN organizations_organization o ON o.id = m.organization_id
ORDER BY o.slug, u.username;

-- the coat-check room
SELECT session_key, expire_date FROM django_session;
DELETE FROM django_session WHERE session_key = '<key>';  -- log one person out
```

```python
# Django shell (make exec). A new shell remembers nothing: import again.
from django.contrib.auth import get_user_model, authenticate
User = get_user_model()
authenticate(username="vera", password="deskly-demo")   # <User: vera> or None
```

## Gotchas

- **A 403 that means "not logged in".** Read the body, not just the number.
  `"Authentication credentials were not provided."` is an authentication
  problem, not a permissions one.
- **A password that doesn't start with an algorithm name** (`pbkdf2_sha256$`)
  was written by code that skipped `set_password()`. That user can't log in,
  even with the right password.
- **Anything that rewrites the password column logs that person out**, even if
  the password is the same: a new salt makes a new hash. Scripts, imports and
  reseeds can all cause "I keep getting logged out".
- **An app that works but isn't registered.** The views ran while `apps.py`
  said `name = 'accounts'` and `INSTALLED_APPS` didn't list it, because
  `config/urls.py` imports the views by path. It would have broken as soon as
  the app got a model or a migration. The two lines must agree; fixing only
  `INSTALLED_APPS` gives `ModuleNotFoundError: No module named 'accounts'`.
- **"I can't see any users"** while they were in the database: check which
  database you're looking at. `docker compose exec db psql -U deskly deskly`
  opens the right one; the prompt should read `deskly=#`.
- **Pasting into the Python shell:** a line that starts with spaces gives
  `IndentationError: unexpected indent`, and a new shell gives
  `NameError: name 'User' is not defined` until you import again.

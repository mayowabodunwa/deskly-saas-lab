# Phase 2 — Auth: logins, roles and tokens

**Status:** ✅ All six slices built and verified 2026-10-24 (branch
`phase-2-auth`, started 2026-10-07). Lesson 2 drafted; PR to `main` open.

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
- **JWT (JSON Web Token)**: the wristband model. Instead of a note on the
  server, the server hands out a signed token that says "this is adam, valid
  until 21:20". The client sends it as `Authorization: Bearer <token>`. The
  server checks the signature; it looks nothing up. The flip side: it can't
  take a wristband back before it expires (GAP-016).
- **Access and refresh tokens**: the access token is short-lived (15 minutes)
  and goes on every request. The refresh token lives longer (1 day) and is
  used only to get a new access token, without sending the password again.
- **Throttling (rate limiting)**: a limit on how often someone can call an
  endpoint. Over the limit, the answer is `429 Too Many Requests` with a
  `Retry-After` header. On login it stops password guessing at scale.
- **OAuth**: one site trusting another to say who someone is. Deskly sends the
  browser to Google, the person logs in *at Google*, and Google sends them back
  with a one-time code. Deskly's server swaps the code for their name and
  email. Deskly never sees the Google password.
- **Redirect URI**: the exact address Google may send people back to. Google
  refuses any address not on the list in its console, so a one-time code can't
  be delivered to an attacker's site.

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

**Decided in Slice 5:** JWT is listed first, so anonymous requests now get
`401` with `WWW-Authenticate: Bearer`. See "Slice 5 — the order of the login
methods".
Docs: <https://www.django-rest-framework.org/api-guide/authentication/#unauthorized-and-forbidden-responses>

### Slice 2 — members only: two questions, one lookup

Before Slice 2, an org-scoped request asked one question: "does this company
exist?" Slice 2 adds the second: "does this person belong to it?"

```python
# apps/organizations/access.py
def get_membership_or_404(request, slug):
    return get_object_or_404(
        Membership.objects.select_related("organization"),
        organization__slug=slug,
        user=request.user,
    )
```

- **One query does both.** It looks for a membership row matching this
  company *and* this person. No row → 404.
- **One helper, used by every org-scoped view.** One place to get right. The
  risk is the opposite case: a new view that forgets to call it. Tests per
  endpoint are what catch that (see the breaks below).
- **It returns the membership, not just the company.** The membership carries
  the role, which Slice 3 needs.
- **`IsAuthenticated` runs first.** Strangers are refused (403) before any
  lookup, and the helper never has to deal with an anonymous user.

### Slice 2 — why 404, not 403

403 would mean "this company exists, but you can't see it", which tells a
stranger that the company is a Deskly customer. With 404, a company you don't
belong to and a company that doesn't exist get **the same status and the same
body**. A test compares the two whole responses to keep it that way.

Trade-off: support can't tell from the status alone whether a user typed the
wrong company or lacks a membership. The answer is in the database
(`organizations_membership`), not in the response, which is where it belongs.

### Slice 3 — roles: a plain function, not a DRF permission class

```python
# apps/organizations/access.py
WRITE_ROLES = {Membership.Role.OWNER, Membership.Role.AGENT}

def require_write_role(membership):
    if membership.role not in WRITE_ROLES:
        raise PermissionDenied("Viewers can read tickets but not change them.")
```

`ticket_list` calls it inside `if request.method == "POST":`, **before** the
serializer saves anything.

- **Why not a DRF permission class?** Permission classes run before the view
  body, before the membership has been looked up, so the class would have to
  look it up a second time. A function called inside the view reuses the
  membership Slice 2's helper already returned: one query. Revisit when there
  are many views (Phase 6).
- **`WRITE_ROLES` is written once.** A new role means one line to change.
- **The 403 body says why.** "Viewers can read tickets but not change them"
  turns the support ticket "it just says forbidden" into a one-line answer.
- **The order of the checks:** logged in? (403) → member? (404) → role
  allowed? (403). A stranger never reaches the role check, so learns nothing
  about who has which job inside a company.

### Slice 3 — why Membership decides access, not the ticket's foreign key

Two links, two questions. `Ticket.organization` says which company a ticket
belongs to; it knows nothing about people. `Membership` says which company a
person belongs to and with which role; it's the only link between a user and a
company. Access means connecting a person to data, so it needs both:

```
person ──Membership (role)──► Organization ◄──foreign key── Ticket
```

The role lives on the membership, not on the user, because one person can
belong to several companies with a different job at each (the Phase 1 user
`mayowa` is an owner at Acme and a viewer at Globex).

### Slice 4 — CSRF: what the attack is and what stops it

**The attack.** adam is logged into Deskly. He visits `evil.com`, which has
hidden code that sends a write to Deskly. The browser attaches adam's
`sessionid` cookie automatically, and Deskly sees a valid login. The cookie
proves which **browser** sent the request, not which **website** told it to.

**Two checks, both made by Django on every logged-in write:**

| Check | Question | Why `evil.com` fails it |
|---|---|---|
| Token | Did the request carry the `csrftoken` value in the `X-CSRFToken` header? | One site can't read another site's cookies, so `evil.com` can't copy the token |
| Origin | Does the browser's `Origin` header match Django's own address (or `CSRF_TRUSTED_ORIGINS`)? | The browser labels the request `Origin: https://evil.com` |

Reads (GET) need neither: they must never change anything, and the browser
won't let `evil.com` see the answer.

**Defence in depth:** the session cookie is also `SameSite=Lax` (Slice 1), so
modern browsers mostly don't send it on requests started by other sites. The
token is the layer that still holds if that one doesn't.

**When DRF enforces it:** session auth checks CSRF only for a **logged-in**
user. Anonymous requests, including the login itself, skip it. See GAP-014.

### Slice 4 — the endpoints

- **`GET /api/auth/csrf/`** calls `get_token(request)`, which makes Django set
  the `csrftoken` cookie on the reply. Before this, the cookie only arrived at
  login, and a page needs it before its first write.
- **`POST /api/auth/logout/`** calls `logout(request)`, which deletes the
  `django_session` row. It's a POST because logging out changes something: as
  a GET, any site could log you out with an image tag pointing at the URL.
  Both live in `accounts`, next to login.

### Slice 4 — the browser side

`frontend/src/api.ts` has two functions, and the app talks to the API only
through them: `getJson` (no token) and `postJson` (always copies the
`csrftoken` cookie into `X-CSRFToken`). One place to send the token means no
button can forget it. The page can read `csrftoken` but not `sessionid`,
which is `HttpOnly`: it can prove where it is without being able to steal the
login. `Auth.tsx` fetches `/api/auth/csrf/` when it opens, then `/api/me/`.

The frontend files were written by me at the learner's request, then rewritten
for readability (plain loops, `if/else`, full names) after the first version
read as too dense.

### Slice 4 — the dev proxy keeps the Host header

`frontend/vite.config.ts` now has `changeOrigin: false`. With `true`, Vite
rewrote the Host to `backend:8000`, so Django saw `Origin: localhost:5173` on a
request addressed to `backend:8000` and refused every logged-in write from the
browser. Keeping the Host is what a production reverse proxy does (Nginx's
`proxy_set_header Host $host`), so local behaves like production.

The alternative was `CSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]`. It
works, but it papers over the mismatch rather than removing it, and adds a
setting to keep in step. Production will still need the setting if the SPA
and the API ever live on different domains.

### Slice 5 — tokens for scripts, sessions for the browser

A script can't easily juggle cookies and CSRF tokens, so it gets JWT instead.
`djangorestframework-simplejwt` provides both endpoints; we wrote no views:

- **`POST /api/auth/token/`** with a username and password returns an
  `access` token (15 minutes) and a `refresh` token (1 day).
- **`POST /api/auth/token/refresh/`** with the refresh token returns a new
  access token.

The React app keeps using the session cookie. The page never touches a JWT,
so there's no token in `localStorage` for injected JavaScript to steal. JWT
requests also need no CSRF token: the browser never attaches an
`Authorization` header by itself, so `evil.com` can't borrow it.

Lifetimes are in `SIMPLE_JWT` in `settings.py`. A short access token is the
main defence against a stolen one, because there's no way to cancel it early
(GAP-016).

### Slice 5 — the order of the login methods

```python
"DEFAULT_AUTHENTICATION_CLASSES": [
    "rest_framework_simplejwt.authentication.JWTAuthentication",   # checked 1st
    "rest_framework.authentication.SessionAuthentication",         # checked 2nd
],
```

DRF tries each method in turn: a `Bearer` header, then a session cookie, then
the caller is anonymous. **First doesn't mean "main"**: the browser sends no
header, so it skips JWT and logs in by cookie, exactly as before.

The order only matters for an anonymous request, where DRF asks the **first**
method what to say. JWT can say "send a Bearer token", so the answer is `401`
with `WWW-Authenticate: Bearer`. With sessions first it was `403` (Slice 1).
Two tests that pinned the old `403` now expect `401`.

Listing the methods also drops DRF's default Basic auth (a password on every
request), which nothing used.

### Slice 5 — throttling the password endpoints

Both endpoints that accept a password share one limit:

```python
# apps/accounts/throttles.py
class LoginRateThrottle(AnonRateThrottle):
    scope = "login"          # rate comes from DEFAULT_THROTTLE_RATES: 5/minute
```

`login_view` gets `@throttle_classes([LoginRateThrottle])`; the token view
gets `TokenObtainPairView.as_view(throttle_classes=[LoginRateThrottle])`.
Same scope, so one counter per IP address covers both: 3 guesses on one and
3 on the other is still 6.

Only the password endpoints are throttled. Refresh, `/api/me/` and the ticket
endpoints aren't: they need a valid login already, so guessing gets nothing.

**Where the counter lives.** DRF keeps it in Django's cache. With no `CACHES`
setting, that's `LocMemCache`, which is the memory of one Python process: a
restart wipes it, and each gunicorn worker keeps its own count, so 4 workers
means about 20 tries a minute, not 5. `CACHES` now points at the Redis we
already run (Django 5.1's built-in `RedisCache`, using `REDIS_URL`). One
counter for every process, and it survives a restart. The trade-off is that
login now needs Redis to be up.

**Tests use their own cache.** `LoginThrottleTests` has
`@override_settings(CACHES=<LocMemCache>)` and `cache.clear()` in `setUp`.
Otherwise the counter would carry from test to test, and tests and dev curls
would share one Redis counter.

### Slice 5 — the login view ignores the login cookie

```python
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
```

`AnonRateThrottle` counts **anonymous** callers only. Without
`@authentication_classes([])`, a caller logged in as themselves (mallory)
looked logged in, so the throttle skipped her, while the body asked about
someone else (`"username": "olivia"`). She could guess olivia's password with
no limit. The throttle looked at **who is sending**; the risk is **who is
being guessed**.

With no authentication classes, the view never reads the cookie, so every
caller is anonymous and counted by IP. SimpleJWT's token view already works
this way. Refusing logins from logged-in callers was the other option; it
would break switching accounts on a shared computer.

### Slice 6 — Google sign-in with django-allauth

```
browser ── POST /accounts/google/login/ (+ CSRF token) ──▶ Deskly
browser ◀── 302 to accounts.google.com?client_id=…&redirect_uri=…5173/…/callback/
browser ── logs in at Google, clicks Allow
browser ◀── 302 to localhost:5173/accounts/google/login/callback/?code=…
Deskly  ── swaps the code for name + email (server to server, uses the secret)
Deskly  ── finds the user with that verified email, logs them in (session cookie)
browser ◀── 302 to LOGIN_REDIRECT_URL = "/"
```

**A library, not our own code.** OAuth is where home-made code gets subtle
security bugs (state checks, code swaps, token checks). `django-allauth` 65.20
does the whole round trip; we wrote only settings, an adapter, a form and
tests. The client ID and secret are read from `GOOGLE_OAUTH_CLIENT_ID` and
`GOOGLE_OAUTH_CLIENT_SECRET` in `.env`, never committed.

**Pages, not JSON.** allauth lives under `/accounts/`, not `/api/`: the
browser visits these addresses and follows redirects. The Vite proxy forwards
`/accounts` with `changeOrigin: false`, so allauth builds the callback address
from `localhost:5173`, which is the one registered with Google, and the session
cookie lands where the React app runs.

**Only POST starts a login.** A GET shows a "Continue" page
(`SOCIALACCOUNT_LOGIN_ON_GET` is left `False`). Otherwise any site could start a
Google login in your browser with a plain link. The React button is a real
`<form method="post">` with a hidden `csrfmiddlewaretoken`, because the whole
page has to go to Google and back, which `fetch` can't do. `Auth.tsx` stores the
token in state once `/api/auth/csrf/` has set it: on a first visit the form is
drawn before the cookie exists.

### Slice 6 — only existing users, matched by verified email

```python
# apps/accounts/adapters.py
class NoSignupAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False
```

A Google stranger would have no membership and see nothing, so sign-up is
closed: unknown emails get allauth's "Sign Up Closed" page. The same adapter
closes allauth's own `/accounts/signup/` form. New people will join by invite,
later.

`SOCIALACCOUNT_EMAIL_AUTHENTICATION = True` lets a Google email log into the
Deskly user with that email. That's safe only because Google verifies emails
before vouching for them. `..._AUTO_CONNECT = True` then links the Google
account to the user, so later logins follow the link.

**allauth trusts its own email table, not `User.email`.** If the match is on
an email allauth hasn't recorded as **verified**, it wipes the user's
password on the first Google login. That's on purpose. Otherwise someone who
signed up with your email before you, and knows its password, would share the
account with you. Lab users are linked in the shell with a verified
`EmailAddress` row; real users will get one by clicking an emailed link or
accepting an invite.

## Build slices

- [x] Slice 1 — **Log in with a session.** Demo users with memberships; a
      login endpoint; `/api/me/` answers "who am I?". Done 2026-10-11.
- [x] Slice 2 — **Members only.** The company in the URL must be one the user
      belongs to. Closed GAP-006. Done 2026-10-18.
- [x] Slice 3 — **Roles.** Viewers can read but not write; agents and owners
      can write. Permission tests. Done 2026-10-19.
- [x] Slice 4 — **CSRF for the web app.** The browser proves a write came from
      Deskly's own pages. Plus logout and a login box in the React app.
      Done 2026-10-23.
- [x] Slice 5 — **Tokens for scripts (JWT).** Short-lived access tokens plus
      refresh, and login throttling. Anonymous requests now get 401.
      Done 2026-10-24.
- [x] Slice 6 — **Sign in with Google (OAuth).** django-allauth; existing
      users only, matched by verified email. Done 2026-10-24.

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

### Slice 2 — the breaks

1. **The hole, seen first.** Before the fix, gary (Globex) got Acme's tickets,
   and so did a stranger with no login: `200 OK` and the full list.
2. **Locking the door broke the old tests.** The two Phase 1 ticket tests
   visited the ticket list without logging in, and now got `403 != 200` and
   `403 != 201`. The tests still checked the right things; they gained
   `force_login(adam)` in `setUp` and passed again.
3. **Removing the check from one view (reasoned, not run).** With
   `ticket_list` back on `Organization.objects.get(slug=slug)`, all eight tests
   would still pass: the ticket tests log in as a member, and the members-only
   tests only visit the company page. The learner chose to skip running it.
   The missing test was added
   (`test_non_member_cannot_list_another_orgs_tickets`), making nine.

### Slice 3 — the breaks

1. **The problem, seen first.** vera (viewer) created a ticket with `201`.
2. **The check after the save.** With `require_write_role(membership)` moved
   below `serializer.save(...)`, vera got `403`, and the ticket was saved
   anyway. Seen by hand. A response that says "no" proves nothing about what
   already happened. `test_viewer_cannot_create_a_ticket` checks both the
   `403` and that no ticket exists, so it guards this.

### Slice 4 — the breaks

1. **Logout without the token** (curl, playing `evil.com`): `403`,
   `"CSRF Failed: CSRF token missing."`; with the token, `204`, and `/api/me/`
   then says "credentials were not provided".
2. **Code in the wrong app.** The new views and URLs went into
   `organizations`, giving `404` on `/api/auth/csrf/`. Under `organizations`
   the address would be `/api/orgs/auth/csrf/`, and even that is caught first by
   `"<slug:slug>/"`, which treats `auth` as a company name. Moved to
   `accounts`.
3. **The Origin check in the browser.** Login worked in the React app; logout
   showed `CSRF Failed: Origin checking failed - http://localhost:5173 does not
   match any trusted origins.` The token was fine; the dev proxy was rewriting
   the Host. Fixed with `changeOrigin: false`.

### Slice 5 — the breaks

1. **Six wrong passwords.** `400` five times, then `429` with `Retry-After`.
   The right password also got `429` until the minute was up: the limit
   doesn't know who's typing.
2. **Restart while locked out.** `docker compose restart backend`, and the
   lock was gone. The learner diagnosed it before being told: nothing was
   saving the count. It was in `LocMemCache`, the process's own memory.
   Fixed with `CACHES` on Redis; after that, still `429` after a restart.
3. **Throttle removed from `login_view`.** The first test failed with
   `400 != 429`. Put back.
4. **Logged in, then guessing.** Found while checking before close-out, in
   the Django shell: logged in as adam, 8 wrong logins for olivia gave `400`
   eight times, never `429`. The second test was written first and failed
   (`400 != 429`), then `@authentication_classes([])` made it pass.

### Slice 6 — the breaks

1. **Starting from port 8000.** `localhost:8000/accounts/google/login/` →
   Continue → Google: `Error 400: redirect_uri_mismatch`. The request asked
   for `…8000…/callback/`; only `…5173…/callback/` is registered. The
   learner's first guess was "the backend doesn't know how to log in with
   Google". It did: the browser reached Google, and Google refused the address.
   Fixed by going through 5173, not by adding 8000 to Google's list.
2. **A Gmail no user has.** Google login → "Sign Up Closed". Correct: the
   adapter refused a stranger.
3. **Missing `LOGIN_REDIRECT_URL`.** After Google, a Django 404 for
   `accounts/profile/`, Django's default "after login" address. The login had
   worked: opening `localhost:5173` showed olivia logged in.
4. **Email set on the user only.** `olivia.email = <gmail>`, then Google
   login: it worked, and afterwards olivia's password login failed,
   `has_usable_password()` → `False`, and the hash started with `!`. allauth
   wiped it because the email wasn't verified in its table. Fixed: `make seed`
   (restores the password), a verified `EmailAddress` row, and the
   `SocialAccount` link deleted so the email check ran again. Password then
   survived the Google login.
5. **Sign-ups opened.** `return True` in the adapter, and
   `test_nobody_can_sign_up` failed: the intruder got in. Put back.

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

Slice 2:

```bash
curl -s -c /tmp/gary-cookies.txt -H "Content-Type: application/json" \
  -d '{"username": "gary", "password": "deskly-demo"}' \
  http://localhost:8000/api/auth/login/

curl -i -b /tmp/gary-cookies.txt http://localhost:8000/api/orgs/acme/tickets/    # 404
curl -i http://localhost:8000/api/orgs/acme/tickets/                             # 403
curl -i -b /tmp/gary-cookies.txt http://localhost:8000/api/orgs/globex/tickets/  # 200
make test                                                                        # 9 tests, OK
```

Slice 3 (a logged-in write needs the CSRF token as well as the cookie; Slice 4
explains why):

```bash
curl -s -c /tmp/vera-cookies.txt -H "Content-Type: application/json" \
  -d '{"username": "vera", "password": "deskly-demo"}' \
  http://localhost:8000/api/auth/login/
CSRF=$(grep csrftoken /tmp/vera-cookies.txt | awk '{print $7}')
curl -i -b /tmp/vera-cookies.txt \
  -H "Content-Type: application/json" -H "X-CSRFToken: $CSRF" \
  -d '{"subject": "Vera was here"}' \
  http://localhost:8000/api/orgs/acme/tickets/
# 403 {"detail":"Viewers can read tickets but not change them."}
# The same as adam: 201. make test: 11 tests, OK.
```

Slice 4:

```bash
curl -i -c /tmp/fresh-cookies.txt http://localhost:8000/api/auth/csrf/   # 204 + csrftoken cookie
curl -s -c /tmp/adam-cookies.txt -H "Content-Type: application/json" \
  -d '{"username": "adam", "password": "deskly-demo"}' \
  http://localhost:8000/api/auth/login/
curl -i -b /tmp/adam-cookies.txt -X POST http://localhost:8000/api/auth/logout/  # 403 CSRF
CSRF=$(grep csrftoken /tmp/adam-cookies.txt | awk '{print $7}')
curl -i -b /tmp/adam-cookies.txt -H "X-CSRFToken: $CSRF" -X POST \
  http://localhost:8000/api/auth/logout/                                       # 204
```

In the browser: http://localhost:5173 → log in as adam → Log out → back to the
form, no red message. `make test`: 13 tests, OK.

Slice 5 (since this slice, the anonymous `403`s in the Slice 1 and 2 blocks
above are `401`):

```bash
curl -i http://localhost:8000/api/me/
# 401, WWW-Authenticate: Bearer realm="api"

curl -s -H "Content-Type: application/json" \
  -d '{"username": "adam", "password": "deskly-demo"}' \
  http://localhost:8000/api/auth/token/
# {"refresh":"eyJ...","access":"eyJ..."}
curl -i -H "Authorization: Bearer <access>" http://localhost:8000/api/me/      # 200, adam

for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/auth/login/ \
    -H "Content-Type: application/json" -d '{"username":"olivia","password":"wrong"}'
done
# 400 400 400 400 400 429

docker compose restart backend      # then the loop again: still 429
docker compose exec redis redis-cli keys '*throttle*'
# ":1:throttle_login_<your IP>"  (scope + IP; gone after a minute)
```

`make test`: 15 tests, OK.

Slice 6 (needs `GOOGLE_OAUTH_*` in `.env`, and your Gmail as a test user in
the Google console):

```python
# make exec — link your Gmail to olivia, verified, so her password survives
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
olivia = get_user_model().objects.get(username="olivia")
olivia.email = "YOUR-GMAIL@gmail.com"
olivia.save()
EmailAddress.objects.update_or_create(
    user=olivia, email=olivia.email,
    defaults={"verified": True, "primary": True},
)
```

Then at http://localhost:5173: **Sign in with Google** → back on the page as
olivia (acme: owner). Log out → olivia / `deskly-demo` still works.
`curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/accounts/signup/`
shows the closed page, and `make test`: 18 tests, OK.

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
- **`curl: (56) Recv failure: Connection reset by peer`** → the server hung
  up without answering, which usually means it crashed while loading. Read
  `docker compose logs --tail=30 backend` from the bottom. Real case:
  `isAuthenticated` instead of `IsAuthenticated` in one view file took the
  whole server down.
- **The cookie file vanished.** `/tmp` is emptied when the Mac restarts, so
  `/tmp/deskly-cookies.txt` from an earlier session is gone, and `/api/me/`
  says "credentials were not provided". Log in again.
- **An edit that didn't take effect** → check the editor tab for the white
  "unsaved" dot before debugging anything else.
- **A test only protects the door it knocks on.** A members-only test on the
  company page says nothing about the ticket list. Each org-scoped endpoint
  needs its own non-member test.
- **`{"detail":"CSRF Failed: CSRF token missing."}` on a curl write** while
  logged in → session writes need the `X-CSRFToken` header as well as the
  cookie. Reads don't. Django's test client skips this check by default, which
  is why the tests don't need it. Slice 4.
- **A 403 that still changed data.** Put permission checks before anything is
  saved, and make tests check the database, not just the status code.
- **Works with curl, fails in the browser** → the browser adds things curl
  doesn't. Here, the `Origin` header, which Django's CSRF check compares with
  the request's Host.
- **`CSRF Failed: Origin checking failed - … does not match any trusted
  origins.`** → the token is fine; the Origin and Host disagree. Look for a
  proxy rewriting the Host before reaching for `CSRF_TRUSTED_ORIGINS`.
- **A 404 on a brand-new URL** → check which app's `urls.py` it went into. Each
  app's URLs sit under its own prefix, and a catch-all like `"<slug:slug>/"`
  swallows anything listed after it.
- **Testing CSRF:** Django's test client skips it unless built with
  `Client(enforce_csrf_checks=True)`. Headers are passed as
  `HTTP_X_CSRFTOKEN=...`.
- **`429` isn't a wrong password.** It means too many tries; the person just
  waits for `Retry-After` seconds. If a whole office is locked out at once,
  suspect a shared IP address (GAP-015).
- **A limit that resets on restart** is stored in process memory. Find where
  the counter lives before trusting the number.
- **Check what a limit counts.** `AnonRateThrottle` skips logged-in callers.
  On a login endpoint that was a hole; `@authentication_classes([])` closes it.
- **A rate limit test that passes alone but fails in a full run** usually
  means the counter is shared. Give the test class its own cache and clear it
  in `setUp`.
- **`401` vs `403` depends on the order** of `DEFAULT_AUTHENTICATION_CLASSES`,
  not only on whether you're logged in.
- **`redirect_uri_mismatch`** is almost never a Google outage. Compare the
  `redirect_uri` in "error details" with the console list: port, `http` vs
  `https`, `www.`, trailing slash.
- **"I logged in and got a 404"** → the login probably worked and the "where
  next" address is wrong. Check whether they're logged in first.
- **"Google login worked, now my password doesn't"** → the account's email
  wasn't verified, and allauth wiped the password on purpose.
- **A shell object is a copy.** After `make seed` changes a user, call
  `refresh_from_db()` before trusting `has_usable_password()`.
- **`update_or_create` returned `False`** → the row already existed (allauth
  writes `EmailAddress` rows during Google logins).
- **Tests never use the real OAuth secret.** `override_settings` with a fake
  client ID; CI has no `.env` secrets, and shouldn't.

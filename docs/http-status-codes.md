# HTTP status codes, the 4xx family, in Deskly

A plain-English guide to the "your request was refused" codes: what each one
means, where Deskly sends it, and what a support engineer does about it.

## First split: 4xx or 5xx?

- **4xx: the problem is the request.** The person or program asking did
  something Deskly won't accept. Deskly itself is fine. Help the user.
- **5xx: Deskly broke.** A bug or a crash. Wake up the engineers.

## The codes Deskly uses

| Code | Name | In plain English | Real Deskly examples |
|---|---|---|---|
| **400** | Bad Request | "What you sent doesn't make sense." | Wrong password at `/api/auth/login/`. A ticket with no subject: `{"subject":["This field is required."]}` |
| **401** | Unauthorized | "**I don't know who you are.** Log in." | `/api/me/` with no login (since Phase 2, Slice 5) |
| **403** | Forbidden | "**I know who you are, but no.**" | vera (viewer) creating a ticket. A logged-in write without the CSRF token |
| **404** | Not Found | "There's nothing here," or "**as far as you're concerned**, there's nothing here." | gary (Globex) asking for `/api/orgs/acme/`. An address in the wrong `urls.py` |
| **405** | Method Not Allowed | "This address exists, but not for that action." | `GET /api/auth/login/` (login only accepts POST) |
| **429** | Too Many Requests | "Slow down." | Too many login attempts (Phase 2, Slice 5) |

**Note on 405:** DRF checks who you are *before* it checks the method. A GET
to `/api/auth/logout/` with no login returns `401`, not `405`, because logout
requires a login and that check runs first.

## 401 vs 403 vs 404: the order Deskly asks in

Every company-scoped request goes through the same three questions:

```
1. Do I know who you are?            No → 401
2. Do you belong to this company?    No → 404  (pretend it doesn't exist)
3. Is your role allowed to do this?  No → 403
   All yes                              → 200 / 201
```

- **404 at step 2, not 403.** A 403 would say "Acme exists, but you can't see
  it", which tells a stranger Acme is a Deskly customer. A 404 tells them
  nothing: a company you don't belong to and a company that doesn't exist get
  the same answer.
- **403 at step 3.** The person already belongs to the company, so there's
  nothing to hide. Deskly says no, and says why.

### Why anonymous requests used to get 403

Until Phase 2, Slice 5, a request with no login got `403` with the message
"Authentication credentials were not provided." DRF picks the "not logged in"
code from the **first** authentication method in its list. Session login can't
send a proper 401 (that needs a `WWW-Authenticate` header, and you can't ask a
client for a cookie), so DRF fell back to 403. Slice 5 put JWT first, and JWT
can say `WWW-Authenticate: Bearer`, so the answer became the correct `401`.

## The body tells you more than the number

The same code can have different causes. Always read the message:

| Code | Message | Real cause | What support does |
|---|---|---|---|
| 403 | `Viewers can read tickets but not change them.` | The person's role | Ask the company's owner to change the role |
| 403 | `CSRF Failed: CSRF token missing.` | The app or script didn't send the token | An app bug, not the user's fault |
| 403 | `CSRF Failed: Origin checking failed - … does not match any trusted origins.` | A proxy or settings mismatch | An engineer fixes the configuration |
| 404 | `No Membership matches the given query.` | Not a member, **or** no such company | Check the company name for typos, then check `organizations_membership` |
| 401 | `Authentication credentials were not provided.` | Not logged in at all | Log in again. Did the session expire? |

## From support ticket to status code

| Ticket | Likely code | First question |
|---|---|---|
| "I can't log in" | 400 at login | Right username and password? Was the account created with `set_password()`? (A password without `pbkdf2_sha256$` in front means it wasn't) |
| "I keep getting logged out" | 401 | Did the session expire (14 days)? Did a script rewrite their password? |
| "It says forbidden" | 403 | Read the message: role, or CSRF? |
| "My company's page is gone" | 404 | Typo in the company name? Was their membership removed? |
| "It says too many requests" | 429 | Wait a minute. Is something retrying in a loop? |

## The 2xx codes, for comparison

| Code | Meaning | Deskly example |
|---|---|---|
| 200 | OK, here's your answer | Reading tickets |
| 201 | Created | A new ticket |
| 204 | Done, nothing to show | Logout, `/api/auth/csrf/` |

Reference: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Status>

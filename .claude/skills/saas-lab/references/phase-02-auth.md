# Phase 2 — Auth: sessions, JWT, OAuth, and RBAC

**Goal:** three authentication paths for three audiences — session cookies for the web app, JWTs for programmatic API access, and "Sign in with Google" (OAuth) for humans — plus role-based access control so owners/agents/viewers can do different things.

**Done when:** an agent can log into the SPA (session), a script can call the API with a bearer token (JWT), a user can sign in with Google, and a viewer is blocked from writing while an agent is allowed.

## Concepts to teach here (this phase has the most new vocabulary)

- **Authentication vs authorization.** AuthN = "who are you?" AuthZ = "what are you allowed to do?" RBAC is authZ.
- **Sessions.** After login, the server stores a session and hands the browser a cookie. Every request carries the cookie; the server looks up who you are. Great for first-party web apps because the browser manages it and you can revoke server-side. Downside: needs shared session storage and CSRF protection.
- **JWT (JSON Web Token).** A signed token the client holds and sends in an `Authorization: Bearer …` header. The server verifies the signature without a DB lookup — stateless, ideal for APIs and other services. Downside: hard to revoke before expiry, so keep access tokens short-lived and use refresh tokens. Emphasize: a JWT is *signed, not encrypted* — never put secrets in the payload.
- **CSRF.** Cross-site request forgery: because browsers auto-send cookies, a malicious site could trigger authenticated requests. Session-cookie endpoints need CSRF tokens; bearer-token APIs don't (no ambient cookie). Explain *why* the two paths differ here.
- **OAuth 2.0 / OIDC.** A protocol to log in via a third party (Google) without handling passwords. The user approves; Google returns an identity; we create/lookup the local user. Teach the redirect flow at a high level; use a library, don't hand-roll it.

## Build steps (vertical slice)

1. **Sessions for the web app.** Use Django's session auth for SPA calls. Configure DRF `SessionAuthentication`, secure cookie flags (`Secure`, `HttpOnly`, `SameSite`), and wire CSRF for unsafe methods. The SPA fetches a CSRF token and echoes it on writes.
2. **JWT for the API.** Add `djangorestframework-simplejwt`: `/api/token/` issues access+refresh tokens; `/api/token/refresh/` rotates them. Set a short access lifetime (e.g. 15 min) and a longer refresh. Add a login-throttle.
3. **Google OAuth.** Use a maintained library (`django-allauth` or `authlib`). Register an OAuth app in Google Cloud, put client id/secret in `.env`, implement the callback that maps a Google identity to a Deskly `User` + `Membership`. Explain the redirect-URI allowlist as a security control.
4. **RBAC.** Roles live on `Membership` (owner/agent/viewer). Implement DRF permission classes: `IsOrgMember` (any read), `IsAgentOrOwner` (writes on tickets), `IsOwner` (org settings, invites). Compose them per viewset. This is the starter version; when the learner wants granular permissions, a permission-aware UI, object/field-level rules, and a permission-matrix test, switch to the deep-dive in `references/rbac-access-control.md` (it also covers how RBAC interacts with impersonation, feature flags, and API token scopes).
5. **Wire tenant + role together.** The tenant resolver from Phase 1 now also loads the user's `Membership` for the active org, so permissions can check role in O(1).

Representative permission (let them adapt):

```python
class IsAgentOrOwner(BasePermission):
    def has_permission(self, request, view):
        m = getattr(request, "membership", None)
        if request.method in SAFE_METHODS:
            return m is not None                      # any member can read
        return m is not None and m.role in {"owner", "agent"}   # writes gated
```

## Verify

- Log into the SPA → a session cookie is set; an authenticated `/api/orgs/<slug>/tickets/` succeeds; the same call with the cookie cleared fails 403.
- `POST /api/token/` with credentials returns access+refresh; calling a protected endpoint with `Authorization: Bearer <access>` works; an expired/tampered token is rejected.
- Google sign-in completes and lands you as a real Deskly user.
- A **viewer** gets 403 trying to create a ticket; an **agent** succeeds. A test locks this in.

## Best practices to call out

- **Short-lived access tokens + refresh rotation.** Limits blast radius if a token leaks.
- **Cookies:** `HttpOnly` (JS can't read it), `Secure` (HTTPS only), `SameSite=Lax/Strict` (CSRF defense in depth).
- **Never store JWTs in `localStorage`** if you can avoid it (XSS-readable); prefer the session-cookie path for the first-party SPA and reserve JWTs for server-to-server/API clients. Discuss the tradeoff honestly.
- **Throttle auth endpoints** to blunt credential stuffing (DRF throttling).
- **Use libraries for OAuth.** Rolling your own is how subtle, severe bugs happen.
- **Least privilege by default** — new endpoints require an explicit permission, never open by omission.

## Canonical docs

- DRF authentication: https://www.django-rest-framework.org/api-guide/authentication/
- DRF permissions: https://www.django-rest-framework.org/api-guide/permissions/
- SimpleJWT: https://django-rest-framework-simplejwt.readthedocs.io/
- django-allauth: https://docs.allauth.org/
- Django sessions & CSRF: https://docs.djangoproject.com/en/stable/topics/http/sessions/ and https://docs.djangoproject.com/en/stable/ref/csrf/
- OAuth 2.0 overview: https://oauth.net/2/

## Common issues (lab copilot fodder)

- **CSRF 403 on SPA writes** → the SPA isn't sending the CSRF token; teach the fetch-token-then-echo-it pattern (and why bearer APIs don't need it).
- **`redirect_uri_mismatch` from Google** → the callback URL isn't in Google's allowlist; teach exact-match redirect URIs as a feature, not a nuisance.
- **JWT "works forever"** → access lifetime too long; shorten it and add refresh.
- **Viewer can still write** → permission not applied to that viewset; reinforce deny-by-default.

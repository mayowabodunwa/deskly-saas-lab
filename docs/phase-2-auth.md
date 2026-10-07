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

## Architecture decisions & trade-offs

## Build slices

- [ ] Slice 1 — **Log in with a session.** Demo users with memberships; a
      login endpoint; `/api/me/` answers "who am I?".
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

## How to verify

## Commands used

## Gotchas

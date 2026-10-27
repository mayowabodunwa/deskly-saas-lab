# Phase 3 — Admin, impersonation & feature flags

**Status:** 🚧 In progress (branch `phase-3-admin`, started 2026-10-25)

**Goal:** Deskly's own staff get safe tools to support customers: a locked-down
admin, a record of every sensitive action, a way to see the app exactly as a
customer does, and switches that turn features on without a deploy.

**Done when:**

- Staff can search companies, members and tickets in the admin; a non-staff
  user can't get in.
- An audit log records sensitive actions, and nobody can edit or delete a row,
  not even an admin.
- A staff member can view Deskly as adam, sees a banner the whole time, can
  stop, and both the start and the stop are in the audit log. Admins can't be
  impersonated; non-staff can't impersonate anyone.
- A feature can be turned on for one company, for a plan, or for a percentage
  of companies, and a company stays on the same side every time.
- "Export tickets as CSV" works for companies with the flag on and is hidden
  (and refused) for the rest.

**Support ticket this phase teaches:** *"Why does it work for them and not for
me?"*, plus support's own tooling: seeing what the customer sees without
asking for their password.

## Key concepts

- **Admin panel**: Django's built-in back office at a URL like `/admin/`, for
  staff to look up and fix data. Powerful, so it's the most valuable target in
  the app.
- **Staff vs superuser**: two flags on every Django user. `is_staff` lets
  someone log into the admin at all; `is_superuser` gives every permission
  without asking. Most support staff should be staff with limited
  permissions, not superusers.
- **Audit log**: a record of sensitive actions (who, what, to whom, when) that
  can be added to but never changed. Like CCTV: useful only because nobody can
  wipe it.
- **Impersonation**: a staff member acting as a customer's user, to see exactly
  what they see. Deliberate, limited, reversible, and always recorded.
- **Feature flag**: a switch, stored in the database, that turns a feature on
  or off without deploying new code. Used for plan gating, gradual rollout and
  as a kill switch.

## Architecture decisions & trade-offs

Decided at the start (2026-10-25):

| Decision | Chosen | Why | Alternative |
|---|---|---|---|
| Impersonation | `django-hijack` | Swapping who's logged in is sensitive; the library does the session swap safely. We add: no staff targets, audit rows, SPA banner | A hand-written session swap |
| Feature flags | Our own small `Flag` model | Deskly thinks in companies, not users; we want a stable per-company percentage (a hash of the org id) so a company never flip-flops. About 30 lines | `django-waffle` (user-based, random per-visitor percentages) |
| Feature to gate | "Export tickets as CSV" | Small and visible; Phase 4 moves it to a background job | The AI feature from the original plan (doesn't exist until Phase 5) |

## Build slices

- [ ] Slice 1 — **Admin.** Register companies, members, tickets and comments
      with search; staff only; move it off `/admin/`.
- [ ] Slice 2 — **Audit log.** `AuditLog` model, `record_audit()` helper,
      read-only in the admin.
- [ ] Slice 3 — **Impersonation.** django-hijack, staff only, no staff targets,
      audited, banner in the React app.
- [ ] Slice 4 — **Feature flags.** Per company, per plan, or a stable
      percentage of companies.
- [ ] Slice 5 — **Gate a real feature.** CSV export behind a flag.
- [ ] Slice 6 — Tests, close-out, Lesson 3.

Each slice: build it → break it on purpose → diagnose from symptoms → fix.

## Slice 1 — Admin

### How admin accounts and passwords work

- **There is no default admin.** A fresh Deskly database has no staff users
  at all, and no username or password is written anywhere in the code, seed
  data or `.env`. Each person creates their own:

  ```bash
  docker compose exec backend python manage.py createsuperuser
  # Username: admin   Email: (Enter to skip)   Password: you choose it
  ```

  The password is hidden as you type. Django can warn about weak or common
  passwords, but only if `AUTH_PASSWORD_VALIDATORS` is set in
  `settings.py`. **Deskly's isn't set**, so even `1` is accepted, both here
  and for customer passwords. Fine for a local lab, never for production.
- **Only a hash is stored.** Django never keeps the password itself. It
  stores a one-way hash (PBKDF2 by default) in the `password` column of
  `auth_user`, so nobody, not even someone who can read the database, can
  look the password up. That's why there's no "show password" command.
- **Forgot it? Set a new one; don't recover it.**

  ```bash
  docker compose exec backend python manage.py changepassword admin
  ```

- **Why no hardcoded admin:** a default login like `admin/admin` in the code
  or seed data would end up in git and be the same on every copy of the app,
  so anyone reading the repo could log into the most powerful page in it.
  `seed_demo` creates only customer users (adam, …), never staff.
- **The superuser lives only in your local database.** `docker compose down -v`
  (which wipes the database volume) deletes it, so run `createsuperuser`
  again afterwards.

## How to verify

```bash
# Slice 1: is there a staff account yet? (an empty list means no)
docker compose exec backend python manage.py shell -c \
  "from django.contrib.auth import get_user_model as g; print(list(g().objects.filter(is_staff=True).values_list('username', 'is_superuser')))"
```

## Gotchas

- (none yet)

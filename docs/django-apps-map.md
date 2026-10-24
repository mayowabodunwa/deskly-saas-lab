# How Deskly's backend is split into apps

A plain-English map of `backend/apps/`: what each app is for, why some have
models and some don't, and how to decide where new code goes.

**Short version:** each app is **one topic**. An app has models only if it
needs to **save its own kind of thing** in the database.

## The building analogy

Think of the backend as an office building.

- **`backend/`** is the building.
- **`config/`** is the reception desk. It sends each visitor to the right room
  (`urls.py`) and holds the building rules (`settings.py`).
- **`apps/`** are the rooms. Each room handles one topic.

## The standard files in an app

Every app *can* have the same set of files. It only fills in the ones it needs.
`startapp` creates them all, mostly empty, so an empty file is not a mistake.
It means "this app doesn't need that yet."

| File | What it's for | In plain words |
|---|---|---|
| `models.py` | What we save | What this room keeps in its filing cabinet |
| `migrations/` | Changes to the database | Instructions for building the filing cabinet |
| `views.py` | What happens when someone visits | What this room *does* |
| `urls.py` | The web addresses | The room's door numbers |
| `serializers.py` | Turning data into JSON and back | The translator |
| `tests.py` | Checks that it works | The inspector |
| `admin.py` | Django's admin pages | The manager's back office |
| `apps.py` | The app's name tag | The sign on the door |
| `management/commands/` | Commands you run with `manage.py` | Tools in the cupboard |

## Deskly's apps today

| App | Topic | Saves things? | Why |
|---|---|---|---|
| `organizations` | Companies and who belongs to them | ✅ `Organization`, `Membership` | Deskly must remember these |
| `tickets` | Support tickets | ✅ `Ticket`, `Comment` | Deskly must remember these |
| `accounts` | Logging in, "who am I?" | ❌ Not yet | It **uses** users but adds no new kind of thing. Users are saved by Django's built-in `auth` app, which comes with Django and isn't in our folder |
| `core` | Building-wide tools: health check, `seed_demo` | ❌ No | It only **does** things; it stores nothing of its own |

So there are two kinds of app:

- **Apps that keep things** (nouns) have models and migrations:
  `organizations`, `tickets`.
- **Apps that do things** (actions) have only views, URLs or commands:
  `accounts`, `core`.

## Who depends on whom

```
core      ──uses──────►  every app        (seed_demo fills them all)
accounts  ──reads─────►  organizations  ──points to──►  auth (Django's User)
tickets   ──points to─►  organizations
```

`organizations` is the foundation: almost everything points to it.

Arrows should only go one way. If two apps need each other, the topic is
probably split in the wrong place.

## How an address finds its view

Think of a phone switchboard. `config/urls.py` is the main reception: it reads
the **start** of the address and puts the call through to an app. Each app's
`urls.py` is that app's own receptionist: it reads the **rest** and puts the
call through to a view.

| Word | Meaning |
|---|---|
| `path("x/", view)` | If the address is `x/`, send it to this view |
| `include("apps.x.urls")` | Cut off the part matched so far and hand the **rest** to that app's `urls.py` |
| `<slug:slug>` | A blank to fill in. Whatever is there (`acme`) reaches the view as `slug` |
| `SomeView.as_view()` | Turns a ready-made class-based view (like SimpleJWT's) into something `path()` accepts |

### The five files

**`config/urls.py`**, the main reception:

| Address starts with | Handed to |
|---|---|
| `admin/` | Django's admin |
| `api/` | `core` |
| `api/orgs/` | `organizations` |
| `api/` | `accounts` |

Two lines say `api/`, and that's fine: Django tries lines **top to bottom**,
and if `core` has no match for the rest of the address, it moves on to the next
line. `/api/health/` is found in `core`; `/api/me/` falls through to
`accounts`.

**`core/urls.py`** (Phase 0): `health/`.

**`accounts/urls.py`** (Phase 2, who you are): `auth/login/`, `me/`,
`auth/csrf/`, `auth/logout/`, `auth/token/`, `auth/token/refresh/`.

**`organizations/urls.py`** (Phase 1, one company): `<slug:slug>/` for the
company's details, and `<slug:slug>/` + `include("apps.tickets.urls")` to hand
everything deeper to `tickets`. This is **nesting**: ticket addresses live
inside a company's address.

**`tickets/urls.py`** (Phase 1, tickets inside a company): `tickets/`.

### Following one address all the way

`GET /api/orgs/acme/tickets/`:

```
config/urls.py         "api/orgs/" matches → rest "acme/tickets/"           → organizations
organizations/urls.py  "<slug>/"   matches → slug="acme", rest "tickets/"  → tickets
tickets/urls.py        "tickets/"  matches → ticket_list(request, slug="acme")
ticket_list            logged in? → member? → (writing: role allowed?) → answer
```

### Every endpoint today

| Address | App | Who can use it | Added |
|---|---|---|---|
| `/api/health/` | core | Anyone | Phase 0 |
| `/api/auth/login/` | accounts | Anyone | Phase 2, Slice 1 |
| `/api/me/` | accounts | Logged in | Phase 2, Slice 1 |
| `/api/auth/csrf/` | accounts | Anyone | Phase 2, Slice 4 |
| `/api/auth/logout/` | accounts | Logged in (sessions also need the CSRF token) | Phase 2, Slice 4 |
| `/api/auth/token/` | accounts | Anyone with a correct password | Phase 2, Slice 5 |
| `/api/auth/token/refresh/` | accounts | Anyone with a valid refresh token | Phase 2, Slice 5 |
| `/api/orgs/<company>/` | organizations | Members of that company | Phase 1; members-only since Phase 2, Slice 2 |
| `/api/orgs/<company>/tickets/` | tickets | Members read; agents and owners write | Phase 1; roles since Phase 2, Slice 3 |

`/api/orgs/` on its own is only a prefix, so it returns 404. If it ever lists
companies, it must list only the caller's own, or it becomes GAP-006 again.

### Two traps already hit

- **Wrong file, wrong prefix.** Code put in `organizations/urls.py` lives under
  `/api/orgs/`. That's why `/api/auth/csrf/` was a 404 in Slice 4.
- **Order matters.** Django stops at the first match, and `<slug:slug>/`
  matches any word, so a line listed after it can be swallowed.

## Deciding where new code goes

When you plan a feature, ask three questions:

1. **What are the nouns?** List the things the product must remember. Each one
   becomes a **model**.
2. **Which nouns belong together?** Put them in the same app, named after the
   topic. A comment can't exist without its ticket, so `Comment` lives in
   `tickets`.
3. **Can you describe the app in one sentence without "and"?**
   "Tickets handles support tickets" ✅.
   "Tickets handles support tickets *and* logins" ❌, which is two apps.

Then, for each app: **does it save something new?** Yes → it gets models. No →
it stays plain.

**Trade-off:** more apps means smaller, easier-to-find pieces, but more folders
and more links between them. Too few apps means one giant app where everything
is tangled. One topic per app is the usual middle ground.

## Apps grow, and that's normal

You don't have to get it right up front.

- **`accounts`** gets its first model in Phase 2, Slice 6: the link between a
  person and their Google login. It turns from "plain" into "keeps things".
- **Phase 4** will likely add an **`exports`** app (it saves export jobs).
- **Phase 6** will likely add a **`webhooks`** app (it saves deliveries).

## Adding a new app: the checklist

```bash
mkdir backend/apps/<name>
docker compose exec backend python manage.py startapp <name> apps/<name>
```

Then, **both** of these (they must agree, or Django crashes with
`ModuleNotFoundError`):

1. In `backend/apps/<name>/apps.py`: `name = "apps.<name>"`
2. In `backend/config/settings.py`: add `"apps.<name>",` to `INSTALLED_APPS`

If the app has web addresses, add an `include(...)` line in
`backend/config/urls.py`. If it has models: `makemigrations <name>`, then
`migrate`.

Docs: <https://docs.djangoproject.com/en/5.1/ref/applications/>

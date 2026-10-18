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

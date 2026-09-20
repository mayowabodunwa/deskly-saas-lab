# Troubleshooting Log

Append-only record of everything that broke, surprised us, or turned out to be a
dead end during the Deskly build. **Newest first.**

This file is the raw material for the "What actually broke for me" and
"Break it, then fix it" sections of each course article — and it is the part
that makes a public write-up credible. Idealised tutorials are everywhere; a
record of real failure is not.

## How to use it

Three entry types:

| Tag | Means |
|---|---|
| `ERROR` | It broke loudly. Something failed and said so. |
| `GOTCHA` | It "worked", but not the way we expected. Silent wrong behaviour. |
| `DEAD-END` | An approach we tried and abandoned — and why. |

Every entry answers five things in order: **Symptom → What it means → Root cause
→ Fix → Lesson.**

**Error text is quoted verbatim, never paraphrased.** Someone hitting the same
wall will paste their error into a search box — it has to match character for
character.

---

## 2026-09-20 — `ERROR` — Tooling / CI — a token that can push code cannot push workflows

**Symptom**
Pushing a branch that added `.github/workflows/ci.yml`:

```
 ! [remote rejected] phase-1-domain -> phase-1-domain (refusing to allow an OAuth App to create or update workflow `.github/workflows/ci.yml` without `workflow` scope)
error: failed to push some refs to 'https://github.com/mayowabodunwa/deskly-saas-lab.git'
```

**What it means**
GitHub treats `.github/workflows/` as a higher privilege than ordinary code. A
workflow file is not data — it is **code GitHub will execute on its own machines,
with access to the repository's secrets**. So `repo` scope (push code) and
`workflow` scope (push things that run) are deliberately separate. A stolen token
with only `repo` cannot quietly add a workflow that exfiltrates every secret.

Nothing was broken: the commits existed locally and only the push was refused.

**Root cause**
The stored `gh` token predated the CI work and carried
`'gist', 'read:org', 'repo'` — no `workflow`.

**Fix**
Adding the scope hit a second, unrelated problem:

```
error refreshing credentials for mayusB, received credentials for mayowabodunwa, did you use the correct account in the browser?
```

The GitHub **username had been renamed** `mayusB` -> `mayowabodunwa`. The token
was still valid (`gh api user --jq .login` returned `mayowabodunwa`), but `gh`
had the old name written in its own config, so `gh auth refresh` — which amends
an existing account entry and therefore insists the names match — refused.

`gh auth login` builds the entry from scratch instead, so it accepts whatever
the browser says you are:

```bash
gh auth logout -h github.com -u mayusB
gh auth login -h github.com -s workflow -w    # HTTPS, yes to git credentials
```

Scopes afterwards: `'gist', 'read:org', 'repo', 'workflow'`. Push succeeded.

Note `-h github.com` is required whenever the command cannot run interactively;
without it, `gh` exits with `--hostname required when not running interactively`.
The device-code flow needs a real terminal, since it waits on a keypress before
opening the browser.

The same rename also explains the repo path moving from
`cloudsenseiNG/deskly-saas-lab` to `mayowabodunwa/deskly-saas-lab`. GitHub keeps
a redirect, so the old remote URL kept working and hid the change — the remote
was updated with `git remote set-url origin <new url>`.

**Lesson**
Two separate lessons, and both show up in support queues:

1. **Permission errors are often a *scope* problem, not an access problem.** The
   same token, same repo, same user — one kind of file was refused. Read which
   *capability* was named, not just "permission denied".
2. **An identity rename leaves stale copies everywhere.** GitHub's redirects are
   a kindness that delays the discovery: git remotes, CLI config and CI configs
   keep working until one command compares the old name against the new one and
   stops. "It worked yesterday and nothing changed" usually means something was
   renamed and something else is still holding the old name.

---

## 2026-09-20 — `GOTCHA` — Phase 1 / Slice 5 — the unit test stayed green while the API leaked

**Symptom**
`Ticket.objects.for_org(organization)` in `apps/tickets/views.py` was replaced
with `Ticket.objects.all()` — the cross-tenant leak, reintroduced deliberately.
The suite reported:

```
.F
======================================================================
FAIL: test_ticket_list_endpoint_is_scoped_to_the_url_org
AssertionError: Lists differ: ['Globex merger plans', "Printer won't work"] != ["Printer won't work"]
```

One dot, one F. The model-level isolation test **passed** while the live
endpoint was handing Acme a list with Globex's confidential subject at the top.

**What it means**
The two tests answer different questions, and only one of them is the question a
customer is standing in front of:

- `test_for_org_returns_only_that_orgs_tickets` asks *does the tool work?* —
  `for_org` filters correctly. Still true. Nobody was calling it.
- `test_ticket_list_endpoint_is_scoped_to_the_url_org` asks *does the page use
  the tool?*

Testing the lock is not testing the door.

**Root cause**
Nothing was broken in the code under test by the first test — the breakage was
in a file the tests never mention. A unit test pinned down a helper; the route
from URL to response was free to stop calling that helper at any time, silently.

**Fix**
No fix needed to the app — the line was reverted. The finding is that the HTTP
test earns its place: it is the only one of the two that fails when the endpoint
regresses. Both were kept, because they fail in usefully different ways.

Along the way, two mistakes while trying to make the test fail, both instructive:

1. Changing `for_org(self.acme)` to `for_org(self.globex)` produced a red test
   that proved the *opposite* of the intent — the returned list was
   `['Globex merger plans']`, i.e. exactly one row, correctly scoped. A test can
   go red because the code is wrong or because the expectation is wrong, and the
   output looks identical.
2. Changing the call to `Ticket.objects.all(self.acme)` produced an **error**,
   not a failure:

```
TypeError: BaseManager.all() takes 1 positional argument but 2 were given
```

   `all()` has nowhere to put a tenant — that is what it means. The argument
   count reads as off-by-one because the invisible first argument is `self`.
   `E` means the test crashed before checking anything, so nothing was tested;
   `F` means it ran and the check did not hold. On a red suite, read the `E`s
   first.

**Lesson**
Write the test, then **break the thing it guards** — not the test itself — and
confirm it goes red. A green suite that has never been red is indistinguishable
from a suite of typos. And for anything multi-tenant, the test that matters
travels the full path a real request takes; a helper-level test will keep
reassuring you while the endpoint leaks.

*Support angle:* "I can see another company's data" never arrives as an
exception in a log. There is no crash, no 500, no alert — the code does exactly
what it says. It arrives as a customer email, weeks late.

---

## 2026-09-20 — `GOTCHA` — Phase 1 / Slice 3 — `seed_demo` turned three tickets into nine

**Symptom**
Two halves, one loud and one silent.

Loud — re-running `seed_demo` when the organizations already existed:

```
django.db.utils.IntegrityError: duplicate key value violates unique constraint "organizations_organization_slug_key"
DETAIL:  Key (slug)=(globex) already exists.
```

Silent — once the organization lines were fixed, every run reported success:

```
Seeded demo data.
```

but the ticket table kept growing:

```
orgs: 2 | tickets: 9
```

Three distinct tickets existed in the seed file. The database held nine rows.

**What it means**
The command was not **idempotent** — running it twice did not leave the database
in the same state as running it once.

The organizations failed loudly because `Organization.slug` is `unique=True`; the
database itself refused the second row. `Ticket` has no unique field at all, so
nothing objected, and each run appended three more rows.

The loud failure was the lucky one. The silent duplication is what costs an
afternoon.

**Root cause**
Three mechanics stacked on top of each other:

1. `handle()` runs top to bottom — organizations first, tickets second. The
   `IntegrityError` fired on an org line, so the ticket lines below it never
   executed. Crashing runs left *no* trace in the ticket table, which made the
   arithmetic confusing later.
2. Django does **not** wrap a management command in a transaction by default. A
   command that dies halfway keeps everything it already wrote. Nothing rolls back.
3. `Ticket` has no unique constraint, so every run that reached the bottom
   inserted three more rows, forever.

`created_at` reconstructed the history — millisecond clustering distinguishes a
program run from hand-typed data:

```
2026-09-10T02:16:11  acme   | Printer won't work      <- older lab work,
2026-09-10T02:16:11  acme   | Password reset             2s gap before globex
2026-09-10T02:16:13  globex | Globex merger plans

2026-09-20T08:07:13  acme   | Printer won't work      <- one run: all three
2026-09-20T08:07:13  acme   | Password reset             within 5ms
2026-09-20T08:07:13  globex | Globex merger plans

2026-09-20T08:08:50  acme   | Printer won't work      <- second run, 97s later
2026-09-20T08:08:50  acme   | Password reset
2026-09-20T08:08:50  globex | Globex merger plans
```

**Fix**
`get_or_create`, which splits every call into *how to recognise the row* and
*what to fill in if it has to build one*:

```python
# before — creates unconditionally
Ticket.objects.create(
    organization=acme,
    subject="Printer won't work",
    body="The office printer jams on every third page.",
)

# after — plain args identify, defaults only apply on creation
Ticket.objects.get_or_create(
    organization=acme,
    subject="Printer won't work",
    defaults={"body": "The office printer jams on every third page."},
)
```

Choosing the split is a real decision, not boilerplate:

- **Plain arguments** = identity. `organization` + `subject` names one ticket.
  `organization` alone names two, and `get_or_create` runs `.get()` first, so it
  raises `MultipleObjectsReturned: get() returned more than one Ticket -- it
  returned 2!` rather than guessing.
- **`defaults`** = cargo. `body` never helps identify a ticket. Leaving it as a
  plain argument still *worked*, but put the body text into the search, so
  editing one sentence in the seed file would have produced a fourth ticket.
- `organization` belongs in the lookup because two tenants can legitimately both
  have a ticket called "Password reset". Tenant scoping applies here too: "is
  this the same row?" almost always means "the same row *within this org*".

Verified by deleting the 9 rows, running the command twice, and confirming the
count stayed at 3 with every row carrying the *first* run's timestamp.

**Lesson**
A seed command gets run dozens of times; write it idempotent on day one. More
generally: a unique constraint is what converts silent duplication into a loud
error, and the loud error is the outcome you want. `Organization` had one and
told us immediately; `Ticket` had none and quietly tripled.

Two follow-ons worth knowing:

- `defaults` is used **only** on creation. It never updates an existing row —
  edit the seed text and existing rows keep the old value. `update_or_create` is
  the version that overwrites.
- `get_or_create` is only race-safe when a database unique constraint backs the
  lookup. Fine for a seed command run by hand; a genuine bug in a view serving
  concurrent requests, where the fix is a `UniqueConstraint` in `Meta`.

*Support angle:* "I clicked it twice and now there are two of everything" is an
entire genre of ticket. The cause is nearly always this — an operation that
creates instead of reconciling, with no constraint to stop it.

---

## 2026-09-20 — `ERROR` — Tooling — `make` on macOS is too old for the Makefile

**Symptom**
Every `make` target failed immediately, including ones that had nothing to do
with the work in progress:

```
Makefile:5: *** missing separator.  Stop.
```

**What it means**
Make could not parse the Makefile at all — it never got as far as running
anything. `missing separator` means Make reached a line it expected to be a
recipe (a command to run) and did not find the character that marks one.

Make's rule is that every recipe line must begin with a literal **tab**. Not
spaces — a tab. The two are indistinguishable on screen, which is why this error
is a rite of passage.

**Root cause**
GNU Make 3.82 added `.RECIPEPREFIX`, which lets a Makefile choose a visible
character instead of a tab. Ours chose `>`:

```make
.RECIPEPREFIX = >

up:
> docker compose up --build
```

macOS ships **GNU Make 3.81**, released in 2006 — older than the feature:

```bash
make --version
# GNU Make 3.81
# Copyright (C) 2006  Free Software Foundation, Inc.
```

3.81 read `.RECIPEPREFIX = >` as a meaningless variable assignment, ignored it,
then hit line 5, found no tab, and gave up. The Makefile was never portable; it
only ever worked on a machine with a newer Make installed.

**Fix**
Dropped the `.RECIPEPREFIX` line and replaced each `> ` with a real tab. Tabs
work on every version of Make ever shipped:

```make
up:
	docker compose up --build
```

Verified without executing anything using `-n` (dry run — print the commands,
run none):

```bash
for t in up down logs migrate sh test seed; do make -n "$t"; done
```

The rejected alternative was `brew install make` and typing `gmake` everywhere,
which keeps the nicer `>` syntax but adds an install step and a second command
to remember — a bad trade for a repo meant to be cloned and run.

Workaround while it was broken: run the target's command directly, since each
one is a single line —

```bash
docker compose exec backend python manage.py seed_demo
```

**Lesson**
`missing separator` always means the same thing: Make wanted a tab and got
something else. Check the Make version before trusting a Makefile that uses
modern syntax — macOS's is frozen at 2006 for licensing reasons, and it is the
oldest tool most Mac developers use daily without noticing.

The tabs are now invisible and an editor that converts them to spaces on save
brings the error straight back. An `.editorconfig` with `[Makefile]` /
`indent_style = tab` pins it down if it ever recurs.

*Support angle:* a tool that fails identically on every command — rather than on
one specific action — usually means it failed to *load*, not that the action is
wrong. Worth separating "your input was bad" from "I never started" when writing
error messages.

---

## 2026-09-14 — `GOTCHA` — Phase 1 / Slice 3 — A POST chose its own tenant

**Symptom**
A ticket created against Acme's URL was written into Globex's data. The request
succeeded; nothing indicated anything was wrong:

```
curl -i -X POST http://localhost:8000/api/orgs/acme/tickets/ \
  -H "Content-Type: application/json" \
  -d '{"subject":"Planted by Acme","body":"this should not be in Globex","organization":3}'

HTTP/1.1 201 Created
```

`GET /api/orgs/globex/tickets/` then listed a ticket authored by a caller who
had only ever addressed Acme. Status 201, no error, no log line, no failing test.

**What it means**
A cross-tenant **write**. The read-side leak found in Slice 2 exposed data; this
one lets a caller *plant* data inside another customer's account — which can be
worse, because the victim's own users then trust and act on it. Same OWASP
category as Slice 2 (broken access control), opposite direction of travel.

The attack needs no tooling and no skill: change one number in a JSON body.

**Root cause**
The organization was taken from client input instead of from the resolved
tenant. Reproduced deliberately by weakening two independent guards at once:

```python
# serializers.py — organization exposed as a writable field
fields = ["id", "organization", "subject", "body", "status", "created_at", "updated_at"]

# views.py — nothing overrides what the client sent
serializer.save()
```

Either guard alone was sufficient. Verified by weakening each in isolation:

- `serializer.save()` with `organization` **absent** from `fields` → no org is
  ever set → `IntegrityError` on the `NOT NULL` column → **500**. Loud, obvious,
  no leak.
- `organization` **present** in `fields` but `save(organization=organization)`
  retained → the server's value overwrites the client's → no leak.

Both had to be removed before anything escaped. That is the defence-in-depth
working as designed.

**Fix**
Restore both layers:

```python
# serializers.py — organization is not on the menu at all
fields = ["id", "subject", "body", "status", "created_at", "updated_at"]

# views.py — the tenant is stamped on server-side, from the resolved org
serializer.save(organization=organization)
```

Re-ran the identical POST: `201 Created`, ticket lands in **Acme**, Globex
unchanged. The `"organization": 3` in the body is silently ignored — note
*ignored*, not rejected, which is DRF's default for undeclared fields and worth
remembering when a client swears they sent a field that never took effect.

Planted rows removed by id (`Ticket.objects.filter(id__in=[...]).delete()`),
after printing every row first — a filter is a description and can match more
than intended; ids are exact.

**Lesson**
The vulnerable line and the safe line differ by twenty-six characters:

```python
serializer.save()                            # vulnerable
serializer.save(organization=organization)   # safe
```

Both return 201. Both read naturally. The dangerous one is what every
single-tenant DRF tutorial shows, because there it is simply correct — the bug
is created by the *context*, not by the code looking wrong. This is why it
survives code review: a reviewer reads `serializer.save()` as "save the thing",
not as "and the customer whose data this becomes is now decided by whoever sent
the request".

Two consequences for how we build from here:
1. **Never derive a tenant from the request body.** The org comes from the URL
   or the session, resolved server-side, always.
2. **Keep both layers even though either would do.** One layer is a convention
   somebody can innocently delete — e.g. adding `"organization"` to `fields` to
   show it in a response. Two independent layers mean a single reasonable-looking
   edit cannot silently reopen the tenant boundary.

Related: GAP-006 — resolving the tenant from the URL still does not check that
the caller is *entitled* to it. That half cannot close until Phase 2 adds logins.

---

## 2026-09-14 — `ERROR` — Phase 1 / Slice 3 — Server died silently on a missing import

**Symptom**

```
curl: (52) Empty reply from server
```

No status code, no error page, no JSON. The connection opened and closed with
nothing sent. Previous requests to the same server had worked moments earlier.

**What it means**
The process is not running. A `404` or `500` proves a server is alive and
answering; **silence means it never finished booting**. These are different
failures needing different first moves — one is debugged from the response, the
other only from the logs.

**Root cause**
`docker compose logs --tail=40 backend` ended with:

```
  File "/app/apps/organizations/urls.py", line 7, in <module>
    path("<slug:slug>/", include("apps.tickets.urls")),
                         ^^^^^^^
NameError: name 'include' is not defined
```

`include(...)` was added to the URL patterns, but the import line still read
`from django.urls import path`. Django imports `urls.py` **once at startup** to
build the routing table, so an error there stops the process before it can serve
anything — including an error page describing the problem.

**Fix**

```python
from django.urls import include, path
```

The dev server auto-reloaded and the endpoint answered normally.

**Lesson**
Two habits, both cheap:

1. **On silence, read the logs — do not curl again.** The server printed its
   last words to stdout and then stopped existing. Nothing over HTTP will ever
   tell you why.
2. **Read a traceback from the bottom.** The final line is the actual error; the
   lowest line naming a file under `/app/` is where it happened. Everything
   between is framework scaffolding. Forty intimidating lines collapsed to
   "one word missing from an import".

Config files (`urls.py`, `settings.py`) fail differently from view code: a
broken view gives a readable 500, a broken config gives you nothing at all.

---

## 2026-09-10 — `GOTCHA` — Phase 1 / Slice 2 — One `.all()` served another company's tickets

**Symptom**
Two companies exist, Acme and Globex. Acme's ticket list page shows three
tickets — one of which belongs to Globex:

```python
>>> list(Ticket.objects.values_list("organization__slug", "subject"))
[('acme', "Printer won't work"), ('acme', 'Password reset'),
 ('globex', 'Globex merger plans')]
```

No error. No warning. No entry in any log. The page rendered perfectly.

**What it means**
This is not a crash, it is a **data breach** — one customer reading another
customer's data. Broken access control is number one on the OWASP Top 10, the
industry's ranked list of the most common serious web application flaws.
Reproduced here on purpose, before it could happen by accident.

**Root cause**
`Ticket.objects.all()` means *every ticket in the entire database*, across all
customers. The page needed *every ticket belonging to this one customer*. The
code was working exactly as written; it was answering a different question than
the one intended.

**Fix**
Ask the scoped question instead:

```python
Ticket.objects.for_org(acme)     # -> only Acme's rows
```

`for_org` is a one-line method on a custom `QuerySet`, attached as the default
manager on every tenant-scoped model:

```python
class TenantQuerySet(models.QuerySet):
    def for_org(self, organization):
        return self.filter(organization=organization)
```

There is no cleverness in it. Its value is that the filter now lives in **one
place** instead of in the memory of every developer writing every page — and
that reviewing for the bug becomes mechanical: grep the project for
`.objects.all()` and question every hit.

**Lesson**
Three properties make this the access-control bug that actually reaches
production, and they compound:

1. **The dangerous call is the more natural one.** `.all()` is what every
   Django tutorial teaches on page one. Nobody typing it feels they are taking
   a risk.
2. **Nothing complains.** No exception, no red text. Correct-looking code
   producing wrong output is far harder to catch than code that fails loudly.
3. **It is invisible while you build it.** With one company in your dev
   database, `.all()` and `.for_org()` return *identical* results. The bug only
   appears once a second customer exists — which is to say, in production.

Note what the fix does **not** do: `.objects.all()` still exists and still
works. A safe path was added; the dangerous one was not removed. That is the
honest limit of the tenant-column strategy (ADR-0002), and the reason the real
mitigation is an automated isolation test rather than a team convention.

*Support angle:* the whole class of "I can see data that isn't mine" tickets.
The customer's report is the **first** detection — nothing upstream noticed.

---

## 2026-09-10 — `GOTCHA` — Phase 1 / Slice 2 — Editor flags `ticket_id`, which Django creates at runtime

**Symptom**
Pylance underlines `self.ticket_id` inside `Comment.__str__`, in a file that
runs without error:

```
Cannot access attribute "ticket_id" for class "Comment*"
  Attribute "ticket_id" is unknownPylancereportAttributeAccessIssue
(function) ticket_id: Unknown
```

**What it means**
Nothing is broken. The editor is wrong, not the code.

**Root cause**
A `ForeignKey` named `ticket` gives you two attributes, not one:

| Attribute | Is | Costs |
|---|---|---|
| `comment.ticket` | the whole `Ticket` object | a database query, if not already loaded |
| `comment.ticket_id` | just the id number | nothing — it is a column on the comment's own row |

Django adds `ticket_id` **when the program runs**. Pylance reads the file
*without* running it, so it never sees the attribute get created, cannot find a
definition, and reports it as unknown. Any static analyser without Django
support does the same.

**Fix**
Keep the efficient attribute and silence the checker on that line:

```python
def __str__(self):
    return f"Comment on ticket {self.ticket_id}"  # type: ignore[attr-defined]
```

Switching to `self.ticket.id` would also clear the warning, but it trades a
free attribute lookup for a database round-trip — the N+1 pattern, once you are
printing a list of comments rather than one.

The proper fix is `django-stubs`, which teaches the type checker about Django's
runtime behaviour. Not worth stopping a slice for; tracked as a gap.

**Lesson**
A squiggle is a *claim*, not a verdict — and a checker that does not understand
your framework will make false claims. The habit worth building: decide whether
the tool or the code is wrong **before** changing anything, because "fixing"
correct code to satisfy a confused tool is how the slower version gets written.
Use `# type: ignore` for a checker that is genuinely wrong, never to hide a
real mistake.

---

## 2026-07-18 — `GOTCHA` — Phase 0 — Container user had no home directory

**Symptom**
<!-- TODO: paste the verbatim error or the exact behaviour you saw.
     Recorded after the fact: the fix was adding `-m` to `useradd`, so the
     trigger was almost certainly a tool trying to write to `/home/app`
     (pip cache, shell history, or a dev-container extension) and finding no
     such directory. Replace this block with what you actually saw. -->

**What it means**
Linux gives every user a "home directory" — a private folder for that user's
settings, caches and temp files. `useradd -r` creates a *system* user for
running a service, and by default does **not** create one. Most of the time
that's fine, because a service just runs code. It stops being fine the moment
something tries to save a file "in your home folder" and there is no home
folder to save it in.

**Root cause**
`backend/Dockerfile` created the non-root `app` user without a home directory:

```dockerfile
RUN groupadd -r app && useradd -r -g app app
```

**Fix**
Add `-m` ("make the home directory"):

```dockerfile
RUN groupadd -r app && useradd -r -g app -m app
```

**Lesson**
Running containers as a **non-root user** is correct and important — if an
attacker breaks into the process, they land as a limited user rather than as
root with full control. But "non-root" has consequences beyond permissions: no
home directory, no write access outside declared volumes. Cheap to fix once you
know; confusing when a tool fails with a vague path error.

*Support angle:* "it works locally but fails in the container" is very often a
**permissions or missing-path** problem, not a code problem.

---

## 2026-08-08 — `ERROR` — Phase 0 / Concept T1 — Port 5432 already in use

**Symptom**
`docker compose up` failed to start the `db` service.

<!-- TODO: replace with your verbatim scrollback if you still have it.
     The text below is the standard Docker message for this condition and is
     RECONSTRUCTED, not quoted. -->

```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:5432 -> 0.0.0.0:0: listen tcp 0.0.0.0:5432: bind: address already in use
```

**What it means**
A "port" is a numbered door on your machine; only one program can hold a given
door at a time. Port **5432** is Postgres's standard door. Docker tried to open
it for Deskly's database and found something already standing there — almost
always a Postgres installed directly on the Mac, or another project's container
still running.

**Root cause**
`docker-compose.yml` published the container's port 5432 onto host port 5432,
which was already taken:

```yaml
ports: ["5432:5432"]
```

**Fix**
Move the **host** side to a free port. The left number is the door on your Mac;
the right number is the door inside the container. Only the left one has to
change:

```yaml
ports: ["5433:5432"]
```

Nothing inside Docker changes — the backend container still reaches the database
on 5432 over Docker's internal network. Only tools running on your Mac (a GUI
client like TablePlus, or `psql` in your terminal) now connect on **5433**.

Diagnose it before changing anything:

```bash
lsof -i :5432          # what is holding the port
docker ps              # is it another container of mine
```

**Lesson**
Port conflicts are one of the most common first-day Docker errors, and the
message is more intimidating than the problem. `address already in use` always
means the same thing: something else got there first. The two useful questions
are *what is holding it* and *do I need that thing running*.

*Support angle:* this is the shape of a whole class of tickets — a resource
that can only have one owner, quietly claimed by something the user forgot was
running.

---

<!-- New entries go ABOVE this line, newest first. Copy the shape above:
     ## DATE — TAG — Phase/Slice — one-line title
     Symptom (verbatim) / What it means / Root cause / Fix / Lesson -->

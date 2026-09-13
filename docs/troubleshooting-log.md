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

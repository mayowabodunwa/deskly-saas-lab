# 03 — How the database keeps data correct

## The idea in one line
A good database doesn't just store data — it refuses to hold WRONG data, and does
bundles of changes all-or-nothing.

## Two tools
- **Constraints** = rules the database won't let anyone break (unique, not-null,
  foreign key, check). The rule lives next to the data, so every writer must obey.
- **Transactions** = all-or-nothing bundles. Either every step succeeds or none do.
  No "half done". (The guarantees around this are called ACID — more later.)

## Where should validation live? App or database?
BOTH — "defense in depth".
- **Database** = the guarantee. Unbreakable by any writer. ONLY the DB can enforce
  uniqueness correctly when two requests arrive at the same instant (app-only checks
  race and let duplicates through).
- **Application** = the first line + good UX: friendly error messages, rich human
  rules (password strength, formats), business rules that span systems.
- Rule of thumb: app validates for experience, DB enforces for correctness. Keep both.

## Proof I ran
- UNIQUE + CHECK constraints rejected a duplicate email and a negative balance —
  no checking code written, the rules did it.
- A transaction where a later step failed left Alice's balance at 100, not 70 —
  the earlier change was undone. All-or-nothing.

## Seen again in real code (Phase 1)
- `slug = models.SlugField(unique=True)` on the Organization model becomes a real
  Postgres UNIQUE constraint after migration — the app-layer rule and the DB
  guarantee written in one line.

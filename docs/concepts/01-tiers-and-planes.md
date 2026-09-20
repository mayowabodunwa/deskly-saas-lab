# 01 — Tiers & Planes

## The idea in one line
A system is split into parts, each with one job, and requests flow one direction through them.

## Plain-English version
Like a restaurant: a **front door** (one way in), a **kitchen** (does the work),
a **fridge** (holds the data). Customers → front door → kitchen → fridge.
The fridge never walks out to the customer. Requests only reach one way.

- **Tier** = a layer in the request path (UI → logic → data). About *order*.
- **Plane** = a group of parts by *purpose* (app / data / async / AI). About *role*.

## Why split it up (the payoff)
1. Scale one part without touching the others (more cooks, same fridge).
2. Contain damage — one part dies, the rest keep serving ("degraded", not "dead").
3. Easier to reason about — one part at a time.

## The cost (the trade-off)
Every boundary is a tiny delay (a network hop) and one more thing to run.
Splitting is a trade, not a free win.

## Proof I ran
- `docker compose ps` → 4 containers = 4 parts (frontend, backend, db, redis).
- `curl /api/health/` → {"status":"ok","db":true,"redis":true}
  = one request to the app plane that reached into the data plane.
- Stopped redis → {"status":"degraded","db":true,"redis":false}
  = one part down, the app stayed up. Blast radius contained.

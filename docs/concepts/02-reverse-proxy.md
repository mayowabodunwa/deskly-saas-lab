# 02 — The Reverse Proxy (the front door)

## The idea in one line
Put ONE front door in front of all your services; every visitor goes through it.

## Plain-English version
Like a building's reception desk: one entrance, and reception points you to the
right room. A "reverse proxy" stands in front of your servers and routes each
request by its address — /api/... → backend, everything else → the web pages.

## Why one front door
1. Routing — sends each request to the right service by its address.
2. One lock — HTTPS/the padlock is set up once, at the door.
3. A bouncer spot — natural place for rate-limiting and blocking bad traffic.
4. Hides the inside — visitors only ever see one door, not your servers.

## The cost (trade-off)
One more hop in the path, and if the door dies, everything behind it is
unreachable — so in production the door itself is made redundant.

## Dev vs production
- **Dev (now):** Vite's dev server plays "front door" using a Node library called
  `http-proxy` (see `frontend/vite.config.ts`, which forwards /api → backend).
  It only runs while developing.
- **Production:** the Vite dev server is gone; a real reverse proxy — **Nginx** or a
  Kubernetes **Ingress** — takes over the same job. Same idea, different doorman.

## Proof I ran
- curl :8000/api/health/  → knocked directly on the backend.
- curl :5173/api/health/  → knocked on the front door; it routed me to the
  backend behind the scenes. Same answer, but I never named port 8000.

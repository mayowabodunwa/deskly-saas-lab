import type { Scenario } from "./types";

// Every output below is real: captured from Deskly while the named part was
// stopped (see Lesson 0, "Break it, then fix it"). The `docker compose ps`
// tables are the real format with the stopped service's row absent, which is
// how Compose lists a stopped container (only `ps -a` shows it).

const healthy = {
  backend: "backend    Up 42 hours",
  db: "db         Up 43 hours (healthy)",
  frontend: "frontend   Up 43 hours",
  redis: "redis      Up 43 hours (healthy)",
};
const ps = (...rows: string[]) => ["SERVICE    STATUS", ...rows].join("\n");

const clearCache = {
  text: "The customer replies 20 minutes later: \"Done that. Still broken.\" You learned nothing about the system.",
};

const scenario: Scenario = {
  title: "Ticket simulator: SITE DOWN",
  ticket: `Subject: SITE DOWN
From: Team lead, Acme Corp

Nothing is working. We can't get into Deskly at all.
This is costing us money. Please fix ASAP.`,
  actions: [
    { id: "open", label: "Open Deskly yourself, in your browser", minutes: 2 },
    { id: "cache", label: "Ask the customer to clear their cache and try again", minutes: 20 },
    { id: "front", label: "Call the health check through the front door", command: "curl -i localhost:5173/api/health/", minutes: 1 },
    { id: "back", label: "Call the health check on the backend directly", command: "curl localhost:8000/api/health/", minutes: 1 },
    { id: "ps", label: "See which containers are running", command: 'docker compose ps --format "table {{.Service}}\\t{{.Status}}"', minutes: 1 },
  ],
  causes: [
    { id: "frontend", label: "The frontend (the front door)" },
    { id: "backend", label: "The backend (the kitchen)" },
    { id: "db", label: "The database (the fridge)" },
    { id: "redis", label: "Redis (the notepad)" },
    { id: "customer", label: "The customer's own network" },
  ],
  wrongFixMinutes: 10,
  variants: [
    {
      id: "db-down",
      cause: "db",
      results: {
        open: { text: "The Deskly page loads. Its status box says: API status: degraded. Postgres: ❌ down. Redis: ✅ up." },
        cache: clearCache,
        front: { text: "The front door answers, and passes the backend's reply through.", output: '{"status":"degraded","db":false,"redis":true}' },
        back: { text: "The backend answers. It's running, and it names the broken part.", output: '{"status":"degraded","db":false,"redis":true}' },
        ps: { text: "Three containers are running. One is missing.", output: ps(healthy.backend, healthy.frontend, healthy.redis) },
      },
      fix: { command: "docker compose start db", text: "Wait a few seconds for the database to pass its own health check, and the health check is back to \"ok\"." },
      fastest: "One check: the health check. It answered (so the backend is up) and said db: false. About 2 minutes.",
    },
    {
      id: "redis-down",
      cause: "redis",
      results: {
        open: { text: "The Deskly page loads. Its status box says: API status: degraded. Postgres: ✅ up. Redis: ❌ down." },
        cache: clearCache,
        front: { text: "The front door answers, and passes the backend's reply through.", output: '{"status":"degraded","db":true,"redis":false}' },
        back: { text: "The backend answers. It's running, and it names the broken part.", output: '{"status":"degraded","db":true,"redis":false}' },
        ps: { text: "Three containers are running. One is missing.", output: ps(healthy.backend, healthy.db, healthy.frontend) },
      },
      fix: { command: "docker compose start redis", text: "Redis comes back within seconds, and the health check returns to \"ok\"." },
      fastest: "One check: the health check. It answered and said redis: false. About 2 minutes.",
    },
    {
      id: "backend-down",
      cause: "backend",
      results: {
        open: { text: "The Deskly page itself loads, but instead of the status box there's a red line starting \"Error: SyntaxError\". The page couldn't read any answer from the API." },
        cache: clearCache,
        front: {
          text: "Something answered, but with an error. Who sent it?",
          output: `HTTP/1.1 500 Internal Server Error
Vary: Origin
Content-Type: text/plain
Date: Wed, 07 Oct 2026 08:53:59 GMT
Connection: keep-alive
Keep-Alive: timeout=5
Transfer-Encoding: chunked`,
        },
        back: { text: "Nothing is listening on the backend's door at all.", output: "curl: (7) Failed to connect to localhost port 8000 after 0 ms: Couldn't connect to server" },
        ps: { text: "Three containers are running. One is missing.", output: ps(healthy.db, healthy.frontend, healthy.redis) },
      },
      fix: { command: "docker compose start backend", text: "The backend boots in a few seconds and the health check answers \"ok\" again." },
      fastest: "Two checks: the health check on 8000 can't connect at all, so the backend isn't running; docker compose ps confirms it's missing. About 2 minutes. The 500 from the front door is a trap: it came from the proxy, not the backend.",
    },
  ],
};

export default scenario;

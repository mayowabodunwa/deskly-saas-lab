import { useEffect, useState } from "react";

type Health = { status: string; db: boolean; redis: boolean };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health/")
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui", padding: "3rem", maxWidth: 640, margin: "0 auto" }}>
      <h1>Deskly</h1>
      <p style={{ color: "#666" }}>SaaS lab — Phase 0 foundation. This page fetches the backend health check.</p>
      {error && <pre style={{ color: "crimson" }}>Error: {error}</pre>}
      {health ? (
        <div style={{ padding: "1rem 1.25rem", border: "1px solid #ddd", borderRadius: 12 }}>
          <strong>API status: {health.status}</strong>
          <ul>
            <li>Postgres: {health.db ? "✅ up" : "❌ down"}</li>
            <li>Redis: {health.redis ? "✅ up" : "❌ down"}</li>
          </ul>
        </div>
      ) : (
        !error && <p>Checking…</p>
      )}
    </main>
  );
}

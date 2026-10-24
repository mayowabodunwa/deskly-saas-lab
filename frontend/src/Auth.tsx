import { useEffect, useState } from "react";
import { getCookie, getJson, postJson } from "./api";

// The shape of the answer from /api/me/
type Membership = { org: string; role: string };
type User = { username: string; memberships: Membership[] };

export default function Auth() {
  // Things this box remembers. Changing one redraws the box.
  const [user, setUser] = useState<User | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [csrfToken, setCsrfToken] = useState("");

  // Ask Deskly "who am I?" and remember the answer.
  async function checkWhoIAm() {
    const response = await getJson("/api/me/");
    if (response.ok) {
      setUser(await response.json());
    } else {
      setUser(null);
    }
  }

  // When the page opens: get a CSRF token, then check if we're logged in.
  useEffect(() => {
    async function start() {
      await getJson("/api/auth/csrf/");
      // The Google form below needs the token as a value, so keep a copy.
      setCsrfToken(getCookie("csrftoken"));
      await checkWhoIAm();
    }
    start();
  }, []);

  async function logIn() {
    const response = await postJson("/api/auth/login/", { username, password });
    if (response.ok) {
      setError("");
      await checkWhoIAm();
    } else {
      const body = await response.json();
      setError(body.detail);
    }
  }

  async function logOut() {
    const response = await postJson("/api/auth/logout/");
    if (response.ok) {
      setError("");
      setUser(null);
    } else {
      const body = await response.json();
      setError(body.detail);
    }
  }

  // Logged in: show who we are and a Log out button.
  if (user) {
    return (
      <section>
        <p>Logged in as <strong>{user.username}</strong></p>
        <ul>
          {user.memberships.map((m) => (
            <li key={m.org}>{m.org}: {m.role}</li>
          ))}
        </ul>
        <button onClick={logOut}>Log out</button>
        <p style={{ color: "crimson" }}>{error}</p>
      </section>
    );
  }

  // Not logged in: show the login form.
  return (
    <section>
      <input placeholder="username" value={username} onChange={(e) => setUsername(e.target.value)} />
      <input placeholder="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button onClick={logIn}>Log in</button>
      <p style={{ color: "crimson" }}>{error}</p>

      {/* A real form, not fetch: the whole page has to go to Google and back.
          allauth only starts a Google login on a POST with the CSRF token,
          so another website can't start one in your browser. */}
      <form method="post" action="/accounts/google/login/">
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <button type="submit">Sign in with Google</button>
      </form>
    </section>
  );
}

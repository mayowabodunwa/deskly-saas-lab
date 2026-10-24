// Read one cookie by name, e.g. getCookie("csrftoken").
// document.cookie looks like: "csrftoken=abc123; theme=dark"
export function getCookie(name: string) {
  for (const cookie of document.cookie.split("; ")) {
    const [key, value] = cookie.split("=");
    if (key === name) {
      return value;
    }
  }
  return "";
}

// Read data from Deskly. Reads never need the CSRF token.
export function getJson(path: string) {
  return fetch(path);
}

// Send data to Deskly. Every write carries the CSRF token.
export function postJson(path: string, data?: object) {
  return fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify(data ?? {}),
  });
}

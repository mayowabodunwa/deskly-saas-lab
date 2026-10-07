// Course progress is kept in the reader's own browser (localStorage). It is a
// convenience only: a private window or cleared site data starts fresh, and
// every read and write is wrapped so the page still works if storage is blocked.
const KEY = "course-progress-v1";

type Progress = { lessons: Record<string, boolean>; checks: Record<string, boolean> };

export function load(): Progress {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { lessons: {}, checks: {}, ...JSON.parse(raw) };
  } catch {}
  return { lessons: {}, checks: {} };
}

export function save(progress: Progress) {
  try {
    localStorage.setItem(KEY, JSON.stringify(progress));
  } catch {}
}

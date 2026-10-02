// Sisselogimine püsib brauseris aasta.
const KEY = "kuku.session";
const YEAR_MS = 365 * 24 * 60 * 60 * 1000;

export function saveSession(storage, token, now = Date.now()) {
  storage.setItem(KEY, JSON.stringify({ token, expires: now + YEAR_MS }));
}

export function loadSession(storage, now = Date.now()) {
  try {
    const s = JSON.parse(storage.getItem(KEY));
    return s && typeof s.token === "string" && s.expires > now ? s.token : null;
  } catch {
    return null;
  }
}

export function clearSession(storage) {
  storage.removeItem(KEY);
}

// Pooleli jäänud koht iga osa kohta (ainult selles brauseris).
const PREFIX = "kuku.pos.";
const FINISHED_TAIL_S = 30;

function read(storage, id) {
  try {
    return JSON.parse(storage.getItem(PREFIX + id)) || null;
  } catch {
    return null;
  }
}

export function savePosition(storage, id, seconds, duration, now = Date.now()) {
  const finished = duration > 0 && seconds >= duration - FINISHED_TAIL_S;
  storage.setItem(PREFIX + id, JSON.stringify({ t: Math.floor(seconds), d: duration, finished, at: now }));
}

export function loadPosition(storage, id) {
  const p = read(storage, id);
  return p && !p.finished ? p.t : 0;
}

export function isFinished(storage, id) {
  return Boolean(read(storage, id)?.finished);
}

export function progressFraction(storage, id) {
  const p = read(storage, id);
  if (!p) return 0;
  return p.finished ? 1 : Math.min(1, p.t / (p.d || 1));
}

export function lastInProgress(storage, ids) {
  let best = null, bestAt = -1;
  for (const id of ids) {
    const p = read(storage, id);
    if (p && !p.finished && p.t > 0 && p.at > bestAt) {
      best = id;
      bestAt = p.at;
    }
  }
  return best;
}

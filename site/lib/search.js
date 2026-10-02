// Saadete otsing: tõstutundetu, täpitähed (õ, ä, ö, ü) võrdsustatud.
export function normalize(text) {
  return (text || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export function searchShows(shows, query, limit = 50) {
  const words = normalize(query).split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const scored = [];
  for (const show of shows) {
    const name = normalize(show.name);
    const all = `${name} ${normalize(show.description)}`;
    if (!words.every(w => all.includes(w))) continue;
    const score = words.every(w => name.includes(w)) ? (name.startsWith(words[0]) ? 0 : 1) : 2;
    scored.push([score, show]);
  }
  scored.sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name, "et"));
  return scored.slice(0, limit).map(([, s]) => s);
}

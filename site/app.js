import { encryptToken, decryptToken } from "./lib/crypto.js";
import { saveSession, loadSession, clearSession } from "./lib/session.js";
import { searchShows } from "./lib/search.js";
import { getFile, putFile } from "./lib/github.js";
import { savePosition, loadPosition, isFinished, progressFraction, lastInProgress } from "./lib/progress.js";

const SHOWS_PATH = "site/data/shows.json";
const AUTH_PATH = "site/data/auth.json";
const SOON_DAYS = 14;

const ICONS = {
  play: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.52.85l10.4-6.5a1 1 0 0 0 0-1.7L9.52 4.65A1 1 0 0 0 8 5.5z"/></svg>',
  pause: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="4.5" width="4" height="15" rx="1.2"/><rect x="14" y="4.5" width="4" height="15" rx="1.2"/></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m20 20-4.6-4.6"/></svg>',
  down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>',
  left: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>',
  back15: '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 13A10 10 0 1 1 8 21.5"/><path d="M6 6.5V13h6.5"/><text x="16.5" y="20" font-size="8.5" font-weight="700" text-anchor="middle" fill="currentColor" stroke="none" font-family="Figtree, sans-serif">15</text></svg>',
  fwd30: '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M25.5 13A10 10 0 1 0 24 21.5"/><path d="M26 6.5V13h-6.5"/><text x="15.5" y="20" font-size="8.5" font-weight="700" text-anchor="middle" fill="currentColor" stroke="none" font-family="Figtree, sans-serif">30</text></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>',
  logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 17l-5-5 5-5M5 12h11"/></svg>',
  mark: '<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#26262a"/><circle cx="32" cy="32" r="18" fill="none" stroke="#f5b73b" stroke-width="5"/><circle cx="32" cy="32" r="6" fill="#f5b73b"/></svg>',
};

const state = {
  repo: "",
  status: { ok: true },
  catalog: { shows: [] },
  library: { shows: [] },
  auth: null,
  token: null,
  shows: [],
  showsSha: null,
  current: null, // { episode, show }
  query: "",
};

const $ = id => document.getElementById(id);
const view = $("view");
const audio = $("audio");
const store = (() => {
  try { localStorage.setItem("kuku.t", "1"); localStorage.removeItem("kuku.t"); return localStorage; }
  catch { const m = new Map(); return { getItem: k => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k) }; }
})();

/* ---------------- helpers ---------------- */

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const dateFmt = new Intl.DateTimeFormat("et-EE", { day: "numeric", month: "long" });
const dateYearFmt = new Intl.DateTimeFormat("et-EE", { day: "numeric", month: "long", year: "numeric" });
const timeFmt = new Intl.DateTimeFormat("et-EE", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });

function fmtDate(iso) {
  const d = new Date(iso);
  return (d.getFullYear() === new Date().getFullYear() ? dateFmt : dateYearFmt).format(d);
}

function fmtClock(s) {
  s = Math.max(0, Math.floor(s || 0));
  const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

function fmtMinutes(s) {
  return `${Math.round(s / 60)} min`;
}

function greeting() {
  const h = new Date().getHours();
  if (h >= 5 && h < 8) return "Tere varahommikust";
  if (h >= 8 && h < 10) return "Tere hommikust";
  if (h >= 10 && h < 12) return "Tere ennelõunat";
  if (h >= 12 && h < 14) return "Tere! On lõunasöögi aeg.";
  if (h >= 14 && h < 18) return "Tere! On õhtuoote aeg.";
  if (h >= 18 && h < 22) return "Tere õhtupoolikut";
  return "Head ööd";
}

function hue(text) {
  let h = 0;
  for (const c of String(text)) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}

function initials(name) {
  return String(name).split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join("").toUpperCase();
}

function catalogShow(id) {
  return state.catalog.shows.find(s => s.id === id);
}

function coverHtml(show, cls = "") {
  const cat = catalogShow(show.id) || show;
  const name = show.name || cat.name || "";
  const fallback = `<span class="cover__fallback" style="--fallback:hsl(${hue(name)} 32% 30%)">${esc(initials(name))}</span>`;
  const img = cat.image ? `<img src="${esc(cat.image)}" alt="" loading="lazy" onerror="this.remove()">` : "";
  return `<span class="cover ${cls}">${fallback}${img}</span>`;
}

function libraryShow(id) {
  return state.library.shows.find(s => s.id === id);
}

function allEpisodes() {
  return state.library.shows.flatMap(s => s.episodes.map(e => ({ episode: e, show: s })));
}

async function fetchJson(path) {
  const resp = await fetch(path, { cache: "no-store" });
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(`${path}: ${resp.status}`);
  return resp.json();
}

function setChrome(visible) {
  $("tabs").hidden = !visible;
  document.body.classList.toggle("no-chrome", !visible);
  updateMini();
}

function renderBanner() {
  const b = $("banner");
  const st = state.status || {};
  b.classList.toggle("banner--quiet", st.ok !== false);
  if (st.ok === false && st.kind === "error") {
    b.hidden = false;
    b.innerHTML = `<strong>Viimane uuendus ebaõnnestus. Järgmine katse on 3 tunni pärast.</strong>
      <code>${esc(st.message)}</code>`;
  } else if (st.ok === false) {
    b.hidden = false;
    b.innerHTML = `<strong>Kuku on midagi muutnud — salvestamine on peatunud ja kood vajab parandamist.</strong>
      <code>${esc(st.message)}</code><br>
      <a href="https://github.com/${esc(state.repo)}/issues?q=is%3Aopen+label%3Akuku-muutus" target="_blank" rel="noopener">Vaata teadet GitHubis</a>`;
  } else if (st.message && state.token) {
    b.hidden = false;
    b.innerHTML = esc(st.message);
  } else {
    b.hidden = true;
  }
}

/* ---------------- auth ---------------- */

const EXPIRED = "GitHubi võti on aegunud või tühistatud. Loo uus võti ja seadista leht uuesti.";

function signOut(message) {
  clearSession(store);
  state.token = null;
  audio.pause();
  route(message);
}

function handleError(err, errEl) {
  if (err && err.name === "AuthError") {
    state.authExpired = true;
    signOut(EXPIRED);
    return;
  }
  if (errEl) errEl.textContent = err?.message || "Midagi läks valesti. Proovi uuesti.";
}

function renderSetup(message = "") {
  setChrome(false);
  const guide = `https://github.com/${esc(state.repo)}#seadistamine`;
  view.innerHTML = `
    <section class="auth">
      <span class="auth__mark">${ICONS.mark}</span>
      <h1>${message ? "Seadista uuesti" : "Seadista Kuku arhiiv"}</h1>
      <p>${message ? esc(message) : "Seda tehakse üks kord. Vali parool, millega sina ja su lähedased lehele sisse logite."}</p>
      <ol class="steps">
        <li>Loo GitHubis võti, mis lubab muuta ainult seda repot (<a href="${guide}" target="_blank" rel="noopener">juhend</a>).</li>
        <li>Kleebi võti siia ja vali parool.</li>
      </ol>
      <form class="form" id="setup-form" novalidate>
        <label class="field"><span>GitHubi võti</span>
          <input name="token" autocomplete="off" spellcheck="false" placeholder="github_pat_…" required></label>
        <label class="field"><span>Parool</span>
          <input name="pw" type="password" autocomplete="new-password" required>
          <small>Vähemalt 12 märki. Parooli ei salvestata kuhugi.</small></label>
        <label class="field"><span>Parool uuesti</span>
          <input name="pw2" type="password" autocomplete="new-password" required></label>
        <p class="err" id="setup-err" role="alert"></p>
        <button class="pill pill--primary" type="submit">Salvesta ja logi sisse</button>
      </form>
    </section>`;
  const form = $("setup-form");
  form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const err = $("setup-err");
    const token = form.token.value.trim(), pw = form.pw.value, pw2 = form.pw2.value;
    err.textContent = "";
    if (!token) return (err.textContent = "Kleebi GitHubi võti.");
    if (pw.length < 12) return (err.textContent = "Parool peab olema vähemalt 12 märki pikk.");
    if (pw !== pw2) return (err.textContent = "Paroolid ei kattu.");
    const btn = form.querySelector("button");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Salvestan…';
    try {
      const blob = await encryptToken(token, pw);
      const existing = await getFile(state.repo, AUTH_PATH, token);
      await putFile(state.repo, AUTH_PATH, blob, existing?.sha, token, "Seadista lehe parool");
      state.auth = blob;
      state.authExpired = false;
      saveSession(store, token);
      state.token = token;
      await loadShows();
      location.hash = "#/";
      route();
    } catch (e) {
      handleError(e, err);
      if (e?.name === "AuthError") return;
      btn.disabled = false;
      btn.textContent = "Salvesta ja logi sisse";
    }
  });
}

function renderLogin(message = "") {
  setChrome(false);
  view.innerHTML = `
    <section class="auth">
      <span class="auth__mark">${ICONS.mark}</span>
      <h1>Kuku arhiiv</h1>
      <p>Sinu salvestatud Kuku saated, reklaamideta.</p>
      <form class="form" id="login-form" novalidate>
        <label class="field"><span>Parool</span>
          <input name="pw" type="password" autocomplete="current-password" required autofocus></label>
        <p class="err" id="login-err" role="alert">${esc(message)}</p>
        <button class="pill pill--primary" type="submit">Logi sisse</button>
      </form>
    </section>`;
  const form = $("login-form");
  form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const err = $("login-err");
    err.textContent = "";
    const btn = form.querySelector("button");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Kontrollin…';
    try {
      const token = await decryptToken(state.auth, form.pw.value);
      saveSession(store, token);
      state.token = token;
      await loadShows();
      route();
    } catch (e) {
      btn.disabled = false;
      btn.textContent = "Logi sisse";
      if (e?.name === "WrongPassword") {
        err.textContent = "Vale parool.";
        form.pw.select();
      } else {
        handleError(e, err);
      }
    }
  });
}

/* ---------------- data ---------------- */

async function loadShows() {
  try {
    const file = await getFile(state.repo, SHOWS_PATH, state.token);
    state.shows = file?.json || [];
    state.showsSha = file?.sha || null;
  } catch (e) {
    if (e?.name === "AuthError") throw e;
    state.shows = (await fetchJson("data/shows.json")) || [];
  }
}

async function changeShows(mutate, message) {
  const file = await getFile(state.repo, SHOWS_PATH, state.token);
  const shows = mutate(file?.json || []);
  state.showsSha = await putFile(state.repo, SHOWS_PATH, shows, file?.sha, state.token, message);
  state.shows = shows;
}

/* ---------------- views ---------------- */

function showStatusLine(show) {
  const lib = libraryShow(show.id);
  if (!lib) return "Ootel";
  const n = lib.episodes.length;
  return n === 1 ? "1 osa" : `${n} osa`;
}

function renderHome() {
  setChrome(true);
  const ids = allEpisodes().map(x => x.episode.id);
  const resumeId = lastInProgress(store, ids);
  let resume = resumeId && allEpisodes().find(x => x.episode.id === resumeId);
  let label = "Jätka kuulamist";
  if (!resume) {
    resume = allEpisodes()
      .filter(x => !isFinished(store, x.episode.id))
      .sort((a, b) => b.episode.published_at.localeCompare(a.episode.published_at))[0];
    label = "Uusim osa";
  }
  const shows = [...state.shows].sort((a, b) => a.name.localeCompare(b.name, "et"));
  const checked = state.status?.checked_at ? `Viimati kontrollitud ${timeFmt.format(new Date(state.status.checked_at))}` : "";

  view.innerHTML = `
    <header class="topbar">
      <div><h1>${greeting()}</h1>${checked ? `<p class="checked">${checked}</p>` : ""}</div>
      <button class="icon-btn" id="logout" aria-label="Logi välja" title="Logi välja">${ICONS.logout}</button>
    </header>
    ${resume ? `
      <section class="section section--first" aria-labelledby="resume-h">
      <h2 class="section__title" id="resume-h">${label}</h2>
      <div class="resume">
        ${coverHtml(resume.show, "cover--md")}
        <div class="resume__text">
          <p class="resume__title">${esc(resume.episode.title)}</p>
          <p class="resume__show">${esc(resume.show.name)} · ${fmtDate(resume.episode.published_at)}</p>
          <div class="bar" aria-hidden="true"><span style="width:${(progressFraction(store, resume.episode.id) * 100).toFixed(1)}%"></span></div>
        </div>
        <button class="play" data-play="${resume.episode.id}" aria-label="Esita ${esc(resume.episode.title)}">${ICONS.play}</button>
      </div>
      </section>` : ""}
    <section class="section" aria-labelledby="my-shows">
      <h2 class="section__title" id="my-shows">Sinu saated</h2>
      ${shows.length ? `<div class="grid">${shows.map(s => `
        <a class="tile ${libraryShow(s.id) ? "" : "tile--pending"}" href="#/saade/${s.id}">
          ${coverHtml(s)}
          <p class="tile__name">${esc(s.name)}</p>
          <p class="tile__meta">${showStatusLine(s)}</p>
        </a>`).join("")}</div>` : `
        <div class="empty">
          <h2>Siin pole veel ühtegi saadet</h2>
          <p>Otsi Kuku saade ja vajuta „Salvesta“. Uued tasuta osad laaditakse edaspidi ise alla ja neid hoitakse 6 kuud.</p>
          <a class="pill pill--primary" href="#/otsi">${ICONS.search} Otsi saadet</a>
        </div>`}
    </section>`;
  $("logout").addEventListener("click", () => signOut());
  syncPlayButtons();
}

function renderShow(id) {
  setChrome(true);
  const show = state.shows.find(s => s.id === id) || libraryShow(id) || catalogShow(id);
  if (!show) {
    view.innerHTML = `<a class="back" href="#/">${ICONS.left} Tagasi</a>
      <div class="empty"><h2>Saadet ei leitud</h2><p>Võib-olla eemaldati see vahepeal.</p></div>`;
    return;
  }
  const saved = state.shows.some(s => s.id === id);
  const lib = libraryShow(id);
  const cat = catalogShow(id);
  const now = Date.now();
  const episodes = lib?.episodes || [];

  const list = episodes.map(e => {
    const left = (new Date(e.expires_at) - now) / 864e5;
    const frac = progressFraction(store, e.id);
    const heard = isFinished(store, e.id);
    return `
      <li class="ep" data-ep="${e.id}">
        <p class="ep__title">${esc(e.title)}</p>
        <p class="ep__meta">
          <span>${fmtDate(e.published_at)}</span>${e.duration_seconds ? `<span>${fmtMinutes(e.duration_seconds)}</span>` : ""}
          ${heard ? `<span class="heard">${ICONS.check} Kuulatud</span>` : ""}
          ${left <= SOON_DAYS ? `<span class="soon">${ICONS.clock} Kustub varsti · ${fmtDate(e.expires_at)}</span>` : `<span>Kustub ${fmtDate(e.expires_at)}</span>`}
        </p>
        ${frac > 0 && !heard ? `<div class="bar" aria-hidden="true"><span style="width:${(frac * 100).toFixed(1)}%"></span></div>` : ""}
        <button class="play" data-play="${e.id}" aria-label="Esita ${esc(e.title)}">${ICONS.play}</button>
      </li>`;
  }).join("");

  let body;
  if (!saved) {
    body = `<div class="empty"><p>Seda saadet sa praegu ei salvesta.</p></div>`;
  } else if (!lib) {
    body = `<div class="empty"><h2>Ootel</h2><p>Esimesed osad ilmuvad mõne minuti jooksul. Laadimine võtab aega, sest iga osa on umbes 100 MB.</p></div>`;
  } else if (!episodes.length) {
    body = `<div class="empty"><h2>Praegu pole ühtegi tasuta osa</h2><p>Kuku annab osi tasuta kuulata umbes kuu aega. Uued osad lisanduvad siia ise, kui need ilmuvad.</p></div>`;
  } else {
    body = `<ul class="episodes">${list}</ul>`;
  }

  view.innerHTML = `
    <a class="back" href="#/">${ICONS.left} Sinu saated</a>
    <header class="show-head">
      ${coverHtml(show)}
      <div><h1>${esc(show.name)}</h1>${lib ? `<p>${episodes.length} osa · hoitakse 6 kuud</p>` : ""}</div>
    </header>
    ${saved ? "" : `<div class="show-actions"><button class="pill pill--primary" id="add">${ICONS.plus} Salvesta</button></div><p class="err" id="show-err" role="alert"></p>`}
    ${cat?.description ? `<p class="show-desc">${esc(cat.description)}</p>` : ""}
    ${body}
    ${saved ? `
      <section class="danger-zone">
        <p>Eemaldamisel kustutatakse ka kõik selle saate salvestised. Seda ei saa tagasi võtta.</p>
        <button class="pill pill--danger" id="remove">Eemalda saade</button>
        <p class="err" id="show-err" role="alert"></p>
      </section>` : ""}`;

  $("add")?.addEventListener("click", ev => addShow(show, ev.currentTarget, $("show-err")));
  $("remove")?.addEventListener("click", async ev => {
    if (!confirm(`Eemaldada „${show.name}“ ja kustutada kõik selle salvestised?`)) return;
    const btn = ev.currentTarget;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Eemaldan…';
    try {
      await changeShows(list => list.filter(s => s.id !== id), `Eemalda saade: ${show.name}`);
      location.hash = "#/";
    } catch (e) {
      btn.disabled = false;
      btn.textContent = "Eemalda saade";
      handleError(e, $("show-err"));
    }
  });
  syncPlayButtons();
}

async function addShow(show, btn, errEl) {
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Salvestan…';
  if (errEl) errEl.textContent = "";
  try {
    await changeShows(list => list.some(s => s.id === show.id) ? list : [...list, { id: show.id, name: show.name }],
      `Lisa saade: ${show.name}`);
    btn.className = "pill pill--done";
    btn.innerHTML = `${ICONS.check} Salvestatud`;
    if (location.hash.startsWith("#/saade/")) route();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICONS.plus} Salvesta`;
    handleError(e, errEl);
  }
}

function renderSearch() {
  setChrome(true);
  view.innerHTML = `
    <header class="topbar"><h1>Otsi</h1></header>
    <div class="search" role="search">
      <label><span aria-hidden="true">${ICONS.search}</span>
        <span class="sr-only">Otsi Kuku saadet</span>
        <input id="q" type="search" placeholder="Saate nimi, nt Digitund" autocomplete="off" enterkeyhint="search" value="${esc(state.query)}">
      </label>
    </div>
    <div id="results"></div>`;
  const input = $("q");
  input.addEventListener("input", () => { state.query = input.value; renderResults(); });
  renderResults();
  if (!state.query) input.focus();
}

function renderResults() {
  const box = $("results");
  const shows = state.catalog.shows;
  if (!shows.length) {
    box.innerHTML = `<p class="hint">Saadete nimekiri pole veel valmis. See uueneb mõne minuti jooksul pärast esimest käivitust.</p>`;
    return;
  }
  const found = state.query.trim() ? searchShows(shows, state.query) : shows;
  if (!found.length) {
    box.innerHTML = `<p class="hint">„${esc(state.query)}“ — ei leidnud ühtegi saadet. Proovi lühemat sõna.</p>`;
    return;
  }
  box.innerHTML = `
    ${state.query.trim() ? "" : `<p class="hint">Kõik Kuku saated (${shows.length})</p>`}
    <ul class="results">${found.map(s => {
      const saved = state.shows.some(x => x.id === s.id);
      return `<li class="result">
        <a href="#/saade/${s.id}">${coverHtml(s)}</a>
        <a class="result__text" href="#/saade/${s.id}" style="text-decoration:none">
          <p class="result__name">${esc(s.name)}</p>
          ${s.description ? `<p class="result__desc">${esc(s.description)}</p>` : ""}
        </a>
        ${saved ? `<span class="pill pill--done">${ICONS.check} Salvestatud</span>`
                : `<button class="pill" data-add="${s.id}">${ICONS.plus} Salvesta</button>`}
      </li>`;
    }).join("")}</ul>
    <p class="err" id="search-err" role="alert"></p>`;
  box.querySelectorAll("[data-add]").forEach(btn => btn.addEventListener("click", () => {
    const show = catalogShow(Number(btn.dataset.add));
    addShow(show, btn, $("search-err"));
  }));
}

/* ---------------- player ---------------- */

function findEpisode(id) {
  return allEpisodes().find(x => x.episode.id === id);
}

function play(id) {
  const found = findEpisode(id);
  if (!found) return;
  if (state.current?.episode.id === id) {
    audio.paused ? audio.play() : audio.pause();
    return;
  }
  if (state.current) savePosition(store, state.current.episode.id, audio.currentTime, audio.duration || state.current.episode.duration_seconds);
  state.current = found;
  audio.src = found.episode.url;
  const start = loadPosition(store, id);
  audio.addEventListener("loadedmetadata", () => { if (start) audio.currentTime = start; }, { once: true });
  audio.play().catch(() => {});
  updateMini();
  updateMediaSession();
}

function updateMini() {
  const mini = $("mini");
  const show = Boolean(state.current) && !$("tabs").hidden;
  mini.hidden = !show;
  if (!state.current) return;
  const { episode, show: s } = state.current;
  $("mini-cover").outerHTML = coverHtml(s, "cover--sm").replace('class="cover', 'id="mini-cover" class="cover');
  $("mini-title").textContent = episode.title;
  $("mini-show").textContent = s.name;
  $("sheet-cover").outerHTML = coverHtml(s, "cover--xl sheet__art").replace('class="cover', 'id="sheet-cover" class="cover');
  $("sheet-title").textContent = episode.title;
  $("sheet-show").textContent = `${s.name} · ${fmtDate(episode.published_at)}`;
  $("sheet-show").href = `#/saade/${s.id}`;
  syncPlayButtons();
}

function syncPlayButtons() {
  const playing = state.current && !audio.paused;
  const icon = playing ? ICONS.pause : ICONS.play;
  const label = playing ? "Peata" : "Esita";
  for (const id of ["mini-toggle", "sheet-toggle"]) {
    $(id).innerHTML = icon;
    $(id).setAttribute("aria-label", label);
  }
  document.querySelectorAll("[data-play]").forEach(btn => {
    const mine = state.current && Number(btn.dataset.play) === state.current.episode.id;
    btn.innerHTML = mine && playing ? ICONS.pause : ICONS.play;
    btn.closest(".ep")?.classList.toggle("is-current", Boolean(mine));
  });
}

function updateProgress() {
  const d = audio.duration || state.current?.episode.duration_seconds || 0;
  const t = audio.currentTime;
  const pct = d ? (t / d) * 100 : 0;
  $("mini-bar").style.width = `${pct}%`;
  const resumeBar = state.current && document.querySelector(`.resume:has([data-play="${state.current.episode.id}"]) .bar > span`);
  if (resumeBar) resumeBar.style.width = `${pct}%`;
  const scrub = $("scrub");
  if (!scrub.matches(":active")) {
    scrub.max = Math.floor(d) || 100;
    scrub.value = Math.floor(t);
  }
  scrub.style.setProperty("--p", `${pct}%`);
  $("t-now").textContent = fmtClock(t);
  $("t-left").textContent = `−${fmtClock(d - t)}`;
}

let lastSaved = 0;
audio.addEventListener("timeupdate", () => {
  updateProgress();
  if (state.current && Date.now() - lastSaved > 5000) {
    lastSaved = Date.now();
    savePosition(store, state.current.episode.id, audio.currentTime, audio.duration || state.current.episode.duration_seconds);
  }
});
audio.addEventListener("pause", () => {
  if (state.current) savePosition(store, state.current.episode.id, audio.currentTime, audio.duration || state.current.episode.duration_seconds);
  syncPlayButtons();
});
audio.addEventListener("play", syncPlayButtons);
audio.addEventListener("ended", () => {
  if (state.current) savePosition(store, state.current.episode.id, audio.duration, audio.duration);
  syncPlayButtons();
});
audio.addEventListener("error", () => {
  if (!state.current) return;
  $("mini-show").textContent = "Faili ei saanud laadida. Proovi hiljem uuesti.";
});

function seekBy(delta) {
  audio.currentTime = Math.max(0, Math.min((audio.duration || Infinity) - 1, audio.currentTime + delta));
}

const SPEEDS = [1, 1.25, 1.5];
$("speed").addEventListener("click", () => {
  const next = SPEEDS[(SPEEDS.indexOf(audio.playbackRate) + 1) % SPEEDS.length] || 1;
  audio.playbackRate = next;
  $("speed").textContent = `${String(next).replace(".", ",")}×`;
  $("speed").classList.toggle("is-fast", next !== 1);
});
$("back").innerHTML = ICONS.back15;
$("fwd").innerHTML = ICONS.fwd30;
$("sheet-close").innerHTML = ICONS.down;
$("back").addEventListener("click", () => seekBy(-15));
$("fwd").addEventListener("click", () => seekBy(30));
$("scrub").addEventListener("input", ev => {
  audio.currentTime = Number(ev.target.value);
  updateProgress();
});
$("mini-toggle").addEventListener("click", () => audio.paused ? audio.play() : audio.pause());
$("sheet-toggle").addEventListener("click", () => audio.paused ? audio.play() : audio.pause());
$("mini-open").addEventListener("click", openSheet);
$("sheet-close").addEventListener("click", closeSheet);
$("sheet-show").addEventListener("click", closeSheet);
document.addEventListener("keydown", ev => { if (ev.key === "Escape" && !$("sheet").hidden) closeSheet(); });

function openSheet() {
  const sheet = $("sheet");
  sheet.classList.remove("is-closing");
  sheet.hidden = false;
  document.body.style.overflow = "hidden";
  updateProgress();
  $("sheet-close").focus();
}

function closeSheet() {
  const sheet = $("sheet");
  if (sheet.hidden) return;
  sheet.classList.add("is-closing");
  document.body.style.overflow = "";
  const done = () => { sheet.hidden = true; sheet.classList.remove("is-closing"); $("mini-open").focus(); };
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) done();
  else sheet.addEventListener("animationend", done, { once: true });
}

function updateMediaSession() {
  if (!("mediaSession" in navigator) || !state.current) return;
  const { episode, show } = state.current;
  const image = catalogShow(show.id)?.image;
  navigator.mediaSession.metadata = new MediaMetadata({
    title: episode.title,
    artist: show.name,
    album: "Kuku arhiiv",
    artwork: image ? [{ src: image, sizes: "250x250" }] : [],
  });
  const handlers = {
    play: () => audio.play(),
    pause: () => audio.pause(),
    seekbackward: () => seekBy(-15),
    seekforward: () => seekBy(30),
    seekto: d => { audio.currentTime = d.seekTime; },
  };
  for (const [action, fn] of Object.entries(handlers)) {
    try { navigator.mediaSession.setActionHandler(action, fn); } catch { /* toetamata */ }
  }
}

document.addEventListener("click", ev => {
  const btn = ev.target.closest("[data-play]");
  if (btn) play(Number(btn.dataset.play));
});
window.addEventListener("pagehide", () => {
  if (state.current) savePosition(store, state.current.episode.id, audio.currentTime, audio.duration || state.current.episode.duration_seconds);
});

/* ---------------- routing ---------------- */

function route(message) {
  renderBanner();
  if (!state.auth || state.authExpired) return renderSetup(message);
  if (!state.token) return renderLogin(message);
  const hash = location.hash || "#/";
  document.querySelectorAll(".tabs a").forEach(a => a.removeAttribute("aria-current"));
  const m = hash.match(/^#\/saade\/(\d+)/);
  if (m) {
    renderShow(Number(m[1]));
  } else if (hash.startsWith("#/otsi")) {
    document.querySelector('[data-tab="search"]').setAttribute("aria-current", "page");
    renderSearch();
  } else {
    document.querySelector('[data-tab="home"]').setAttribute("aria-current", "page");
    renderHome();
  }
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", () => { closeSheet(); route(); });

async function init() {
  document.querySelectorAll("[data-icon]").forEach(el => { el.innerHTML = ICONS[el.dataset.icon]; });
  try {
    const [config, status, catalog, library, auth] = await Promise.all([
      fetchJson("data/config.json"), fetchJson("data/status.json"), fetchJson("data/catalog.json"),
      fetchJson("data/library.json"), fetchJson("data/auth.json"),
    ]);
    state.repo = config?.repo || "";
    state.status = status || { ok: true };
    state.catalog = catalog || { shows: [] };
    state.library = library || { shows: [] };
    state.auth = auth;
  } catch {
    view.innerHTML = `<div class="empty"><h2>Lehte ei saanud laadida</h2><p>Kontrolli internetiühendust ja värskenda lehte.</p></div>`;
    return;
  }
  state.token = state.auth ? loadSession(store) : null;
  if (state.token) {
    try {
      await loadShows();
    } catch (e) {
      if (e?.name === "AuthError") {
        clearSession(store);
        state.token = null;
        state.authExpired = true;
        return route(EXPIRED);
      }
    }
  }
  route();
}

init();

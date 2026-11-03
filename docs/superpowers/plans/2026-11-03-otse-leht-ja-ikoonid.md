# Otse-eetri alamlehe ja ikoonide uuendamise plaan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Luua veebirakendusse uus alamleht „Otse“ Raadio Kuku reaalajas kuulamiseks koos reklaamipauside automaatse asendamisega Radio Swiss Pop muusikaga, ning tagada Androidi ja brauserite PWA ikoonide värskendus Kuku ametlikule logole.

**Architecture:** Staatilises veebirakenduses (`site/`) lisatakse alamleht `#/otse` koos reaalajas helimootoriga, mis juhib kahte helivoogu (Kuku Icecast ja Radio Swiss Pop). Reklaamipauside ajal tehakse sujuv helivahetus (*crossfade*). PWA ikoonid ja manifest saavad versioonitunnused vahemälu värskendamiseks.

**Tech Stack:** Vanilla ES modules, Web Audio / HTML5 Audio API, CSS custom properties, Service Worker, Node.js test runner (`node --test`), pytest.

**Spec:** Vestluses kokku lepitud disain (Navigatsioonisakk "Otse", Kuku otse-eetri striim, Radio Swiss Pop asendusmuusika reklaamide ajal koos sujuva ülemineku ja käsitsi lülitiga, Kuku logo ikoonidena ilma veebipäise logota).

## Global Constraints

- Rakendus töötab täielikult staatilisena GitHub Pages'il ilma ehitussammuta (vanilla JS ES moodulid).
- Kasutajaliides ja tekstid on puhtas eesti keeles (sõbralik, selge ja mittetehniline).
- Veebilehe päisesse logo ei panda (päis jääb minimalistlikuks nagu soovitud).
- Mõlemad testikomplektid (`npm test` ja `python -m pytest`) peavad iga sammu järel läbima 100%.

## Review Focus

1. **Striimi katkematus mobiilis:** Kui kasutaja paneb ekraani lukku, peab helivoog edasi mängima standardse `<audio>` elemendi kaudu.
2. **Korduvate reklaamide vältimine:** Radio Swiss Pop voog peab käivituma ainult reklaamide ajal ja vaibuma sujuvalt, kui Kuku naaseb.
3. **Vahemälu värskendamine:** Android ja brauserid peavad saama uue manifesti ja ikoonid kätte ilma vana kollast ringi näitamata.
4. **Pleierite mittekonfliktsus:** Otse-eetri esitamine peab viisakalt peatama järelkuulamise saate ning vastupidi.
5. **Käsitsi lülitus:** Kasutaja peab saama igal hetkel ühe puudutusega lülitada muusika ja eetri vahel.

---

### Task 1: PWA ja ikoonide vahemälu versioonid

**Files:**
- Modify: `site/manifest.webmanifest`
- Modify: `site/index.html`
- Modify: `site/sw.js`
- Test: `tests_js/icons_and_refresh.test.mjs`

- [x] **Step 1: Kirjuta test, mis kontrollib versioonitunnuseid manifestis ja index.html-s**
  Lisa faili `tests_js/icons_and_refresh.test.mjs` kontroll, et `manifest.webmanifest`, `icon.svg` ja `apple-touch-icon.png` omavad versiooniparameetreid ning manifestis on unikaalne `id`.
- [x] **Step 2: Käivita test ja veendu läbikukkumises**
  Run: `npm test`
- [x] **Step 3: Uuenda `site/manifest.webmanifest`**
  Määra `"id": "/?v=4"`, ikoonide teed `"icon-192.png?v=4"` ja `"icon-512.png?v=4"`.
- [x] **Step 4: Uuenda `site/index.html`**
  Lisa `icon.svg?v=4`, `apple-touch-icon.png?v=4`, `manifest.webmanifest?v=4`.
- [x] **Step 5: Uuenda `site/sw.js`**
  Tõsta `CACHE_NAME = "kuku-v4"`.
- [x] **Step 6: Käivita testid ja veendu õnnestumises**
  Run: `npm test`

---

### Task 2: Navigatsioon ja „Otse“ alamlehe vaade

**Files:**
- Modify: `site/index.html:39-43`
- Modify: `site/app.js`
- Modify: `site/style.css`
- Test: `tests_js/otse.test.mjs`

- [x] **Step 1: Kirjuta test alamlehe `#/otse` ja menüünupu kohta**
  Loo `tests_js/otse.test.mjs` ja lisa test, mis kontrollib, et `#tabs` sisaldab saki `#/otse` ning `app.js` renderdab otse-eetri vaate.
- [x] **Step 2: Käivita test ja veendu läbikukkumises**
  Run: `npm test`
- [x] **Step 3: Lisa menüünupp faili `site/index.html`**
  Lisa `#tabs` navigatsiooni:
  ```html
  <a href="#/otse" data-tab="live"><span class="tabs__icon" data-icon="live"></span>Otse</a>
  ```
- [x] **Step 4: Lisa `ICONS.live` ja marsruut `#/otse` faili `site/app.js`**
  Lisa `ICONS.live` raadiomasti/eetri ikoonina, lisa ruuting `#/otse` funktsiooni `route()` ning loo esialgne `renderLive(view)` funktsioon.
- [x] **Step 5: Lisa stiilid faili `site/style.css`**
  Stiili `.live-view`, `.live-badge`, `.live-card`, `.live-indicator`, `.live-source`, `.live-btn`.
- [x] **Step 6: Käivita testid ja veendu õnnestumises**
  Run: `npm test`

---

### Task 3: Kahe helivoo mootor ja sujuv reklaamiasendus

**Files:**
- Modify: `site/app.js`
- Modify: `site/style.css`
- Test: `tests_js/otse.test.mjs`

- [x] **Step 1: Kirjuta test helimootori ja asendusloogika kohta**
  Lisa faili `tests_js/otse.test.mjs` testid, mis kontrollivad:
  - Otse-eetri striimi URL-i (`https://router.euddn.net/8103046e16b71d15d692b57c187875c7/kuku.mp3`)
  - Radio Swiss Pop striimi URL-i (`https://stream.srg-ssr.ch/m/rsp/mp3_128`)
  - Lülitamist ja staatuse muutumist.
- [x] **Step 2: Käivita test ja veendu läbikukkumises**
  Run: `npm test`
- [x] **Step 3: Implementeeri `LiveAudioEngine` klass või moodul failis `site/app.js`**
  - Haldab kahte audio voogu: Kuku ja Radio Swiss Pop.
  - Implementeeri pehme helitugevuse *crossfade* (0.5s) voogude vahel.
  - Lisa ajapõhised automaatsed aknad Kuku tüüpilisteks reklaamipausideks (minutid 19:30–22:00, 33:00–35:30, 45:30–48:00, 58:00–03:00).
  - Lisa käsitsi lüliti nupp ekraanile: "Hüppa muusikale" / "Tagasi Kuku peale".
  - Seadistus: võimalus automaatne muusikaasendus sisse/välja lülitada (salvestub `localStorage`-isse).
  - Kui otse-eeter käivitub, peatatakse järelkuulamise pleier ja vastupidi.
- [x] **Step 4: Käivita testid ja veendu õnnestumises**
  Run: `npm test`

---

### Task 4: Täielik integratsioonitestimine ja kontroll

**Files:**
- Test: `tests_js/*.test.mjs`
- Test: Python testid `tests/`

- [x] **Step 1: Käivita kõik JavaScripti testid**
  Run: `npm test`
- [x] **Step 2: Käivita kõik Pythoni testid**
  Run: `python -m pytest`
- [x] **Step 3: Kontrolli `git status` ja puhtust**
  Veendu, et kõik failid on puhtad ja reeglid (AGENTS.md, kasutaja käsitsi muudatuste kaitse) täidetud.

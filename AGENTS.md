# AGENTS.md — Kuku Raadio Arhiiv

## 1. Projekti ülevaade ja eesmärk
Isiklik Raadio Kuku saadete arhiiv ja otse-eetri salvestaja. Kasutaja saab veebilehel (GitHub Pages) valida saated, mille uued osad salvestatakse automaatselt (kas järelkuulamise API-st või otse-eetri voost) GitHubi *Releases* alla ning on 6 kuud reklaamivabalt kuulatavad telefonis või arvutis.

## 2. Tehnoloogiad
- **Taustaloogika ja salvestamine:** Python 3.12 (`urllib`, `pytz`, `ffmpeg` striimi salvestamiseks ja reklaamide lõikamiseks)
- **Veebiliides (`site/`):** Staatiline HTML/CSS/vanilla JS (ES-moodulid, ilma build-sammuta), majutatud GitHub Pages'is
- **Andmehoidla:** JSON-failid kaustas `site/data/` (`shows.json`, `library.json`, `catalog.json`, `status.json`, `auth.json`, `config.json`) ja MP3-helifailid GitHub Releases'is
- **Automaatika:** GitHub Actions (`.github/workflows/sync.yml` ja `.github/workflows/record_live.yml`)

## 3. Kaustastruktuur ja peamised failid
- `kuku/api.py` — Kuku järelkuulamise API klient (`api.postimees.ee` / `kuku.pleier.ee`) ja vastuste valideerimine
- `kuku/logic.py` — Osade allalaadimise ja aegunud osade (6 kuud) kustutamise äriloogika
- `kuku/releases.py` — GitHub Releases ja Issues API klient
- `kuku/sync.py` — Taustatöö järelkuulamise sünkroniseerimiseks (`python -m kuku.sync`)
- `kuku/live.py` — Otse-eetri saatekava tuvastamine (`get_premiere_schedules`, `should_record_now`) ja reklaamide eemaldamine (`remove_ads`)
- `kuku/record_live.py` — Otse-eetri striimi (`STREAM_URL`) salvestamise ja GitHub Releases'isse üleslaadimise CLI tööriist
- `kuku/auto_record.py` — Automaatne otse-eetri kontrollija ja salvestaja (`python -m kuku.auto_record`)
- `site/` — Veebirakenduse esikülg (`index.html`, `app.js`, `style.css`, `lib/`)
- `tests/` — Pythoni üksustestid (`pytest`)
- `tests_js/` — JavaScripti üksustestid (`node --test`)

## 4. Testimine ja arenduskäsud
- Pythoni sõltuvused: `pip install -r requirements.txt`
- Pythoni testid: `python -m pytest`
- JavaScripti testid (Node 22+): `npm test`
- Kohalik veebiserver: `python -m http.server -d site 8000`

## 5. Koodi- ja stiilinõuded
- Kasutajaliidese ja dokumentatsiooni keel on **eesti keel** (mittetehniline, selge, kasutajasõbralik).
- Veebileht töötab täielikult staatilisena ilma kompileerimiseta (vanilla ES modules).
- Iga muudatuse järel tuleb käivitada nii Pythoni (`pytest`) kui ka JS (`npm test`) testid.

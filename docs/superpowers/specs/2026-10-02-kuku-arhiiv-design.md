# Kuku arhiiv — disain

Kuupäev: 2026-10-02 · Kinnitatud vestluses

## Eesmärk

Isiklik veebileht (GitHub Pages), kus saab Raadio Kuku saateid otsida, valida salvestamiseks ja
salvestatud osi kuulata. Salvestised tulevad Kuku järelkuulamisest (reklaamid on Kuku poolt juba
välja lõigatud) seni, kuni osa on tasuta (~4–5 nädalat pärast eetrit). Salvestisi hoitakse 6 kuud.

## Mida kasutaja ütles

- Leht GitHubis, saadete otsing, kuulamine samal lehel.
- Mitu saadet (~10), igaüks ~kord nädalas, hoida 6 kuud ja kustuvad ise.
- Avalik repo ja avalikud failid on kasutajale vastuvõetavad.
- Parooliga sisselogimine, brauser jääb sisse logituks 1 aastaks.
- Kui Kuku midagi muudab, peab programm sellest selgelt teada andma.

## Eeldused / teadaolevad faktid

- Kuku API: `https://ams.postimees.ee/api` (pole ametlik avalik API, võib muutuda).
  - `GET /kuula/shows?domain=kuku.pleier.ee&page=N` → `{results:[{id,name,description_short,thumbnail}], current_page, total_pages}` (~146 saadet)
  - `GET /kuula/shows/{id}/episodes?domain=kuku.pleier.ee&page=N` → `{show, episodes:{results:[{id,title,published_at,is_premium,is_playable,duration_seconds}], total_pages}}`
  - `GET /kuula/episodes/urls?ids={id}` → `{"<id>": "<ajutine mp3 URL>"}`
- CORS lubab ainult `kuku.pleier.ee` → leht ei saa Kukut otse pärida; kõik Kuku päringud teeb GitHub Actions.
- Osa on ~110 MB (320 kbit/s). Git-failide piir on 100 MB → helifailid lähevad GitHub Releases'i
  (piir 2 GiB faili kohta, kogumahule piiri pole). 10 saadet × 26 osa ≈ 29 GB.
- Tasulise osa (`is_premium: 1`) URL annab vaid ~1 min teaserit. Tasulisi osi ei laadita.

## Arhitektuur

```
GitHub Actions (sync.yml)                       GitHub Pages (site/)
  schedule iga 3 h / käsitsi / push shows.json    index.html + app.js + style.css
  python -m kuku.sync                             loeb site/data/*.json
   ├─ kataloog  → site/data/catalog.json          <audio> mängib Releases'i faile
   ├─ uued osad → Releases (tag saade-<id>)        kirjutab shows.json / auth.json GitHub API kaudu
   ├─ kustuta > 182 päeva
   ├─ library.json, status.json
   ├─ commit + push site/data
   └─ deploy Pages
```

Bot'i `GITHUB_TOKEN`-iga tehtud push ei käivita teisi töövooge, seega `sync.yml` deploy'b Pages'i ise.
Lehelt (kasutaja võtmega) tehtud `shows.json` commit käivitab `sync.yml` → uus saade laetakse kohe.
`concurrency` grupp hoiab ära kaks paralleelset käivitust.

## Komponendid

### `kuku/api.py` — Kuku klient
- Funktsioonid: `list_shows()`, `list_episodes(show_id, max_pages)`, `episode_url(episode_id)`.
- Iga vastus valideeritakse: oodatud võtmed ja tüübid olemas. Kõrvalekalle →
  `KukuApiChanged("<mis puudus/oli vale, millises päringus>")`.
- HTTP 404/410 või mitte-JSON vastus → `KukuApiChanged`. Võrgu-/5xx vead → 3 korduskatset, siis tavaline viga.

### `kuku/sync.py` — põhiloogika
- Loeb `site/data/shows.json` (`[{id, name}]`).
- Kataloog: kirjutab `catalog.json` (`[{id, name, description, image}]`).
- Iga valitud saate kohta: osad, mis on `is_premium == 0`, `is_playable`, avaldatud viimase 182 päeva
  jooksul ja mida Releases'is veel pole → laadi alla → kontrolli → laadi üles.
- Allalaaditud faili kontroll: algab MP3 päisega (`ID3` või kaadri sünk) ja suurus ≥
  `duration_seconds × 8000` baiti (≥ 64 kbit/s). Muidu `KukuApiChanged` (nt teaser tavaosa asemel).
- Kustutab Releases'ist failid, mille osa on avaldatud üle 182 päeva tagasi. Eemaldatud saate
  release kustutatakse.
- `library.json`: Releases'i põhjal (tõe allikas) `[{show_id, show_name, episodes:[{id, title,
  published_at, expires_at, duration_seconds, url}]}]`.
- `status.json`: `{ok, message, checked_at}`.
- Puhtad funktsioonid (testitavad): `select_new_episodes`, `select_expired`, `looks_like_full_mp3`.

### `kuku/github.py` — Releases
- `requests` + `GITHUB_TOKEN`: release'i loomine/leidmine tag'i järgi, asset'ite list/üleslaadimine/kustutamine.
- Faili nimi: `<episode_id>.mp3`; asset'i `label` = osa pealkiri; metaandmed hoitakse ka library.json-is.

### Veateavitus
- `KukuApiChanged` korral: `status.json` → `ok:false` + sõnum; GitHubi issue sildiga `kuku-muutus`
  (kui avatud issue juba on, lisatakse kommentaar); töövoog lõpeb veaga. Leht näitab punast bännerit.
- Muud vead: töövoog lõpeb veaga (GitHub saadab omanikule e-kirja).

### Leht (`site/`)
- Ilma sisselogimiseta: ainult sisselogimise vorm (ja vea-bänner, kui `status.ok == false`).
- **Esmane seadistus** (kui `data/auth.json` puudub): GitHubi võti + parool kaks korda → leht
  krüpteerib võtme ja commit'ib `auth.json`-i selle sama võtmega.
- **Sisselogimine**: parool → dekrüpteeri `auth.json` → võti `localStorage`-isse koos aegumisega
  (365 päeva). "Logi välja" kustutab selle.
- **Otsing**: kliendipoolne otsing `catalog.json`-ist (nimi + kirjeldus, tõstutundetu, täpitähtede
  suhtes paindlik). "Salvesta" / "Eemalda" muudab `shows.json`-i GitHub Contents API kaudu.
- **Minu saated ja kuulamine**: saated ja osad (uuemad eespool), `<audio>` pleier, kuupäev, kustumise aeg.
  Kohe pärast lisamist: "Ootel — esimesed osad ilmuvad mõne minuti jooksul".
- Krüpto: WebCrypto, PBKDF2-SHA256 600 000 iteratsiooni → AES-GCM 256. `auth.json` =
  `{v:1, salt, iv, iterations, ciphertext}` (base64). Parooli ei salvestata kuskile.
- Kujundus: impeccable'i töövoog (shape enne ehitamist, audit/polish lõpus). Eesti keeles, mobiilisõbralik.

## Turvalisus — teadlikud piirangud
- Kuulamise "kaitse" on ainult kasutajaliideses: Releases'i failid on avalikud.
- `auth.json` on avalikus repos; tugev parool + võti piiratud ainult selle repo Contents read/write õigusega.

## Testid
- Python (pytest): API valideerimine (õiged/katkised näidisvastused), `select_new_episodes`,
  `select_expired`, `looks_like_full_mp3`, issue/status loogika (GitHub mock).
- JS (node:test): krüpteeri → dekrüpteeri, vale parool ebaõnnestub, otsingu normaliseerimine.
- Käsitsi: päris sync ühe saatega (Digitund), lehe läbiklõpsamine brauseris, `<audio>` kerimine Releases'i failiga.

## Väljaspool ulatust
- Otse-eetri salvestamine (`record.py` eemaldatakse).
- Mitu kasutajat, päris serveripoolne autentimine.

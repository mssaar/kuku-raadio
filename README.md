# Kuku arhiiv

Isiklik Raadio Kuku saadete arhiiv. Valid veebilehel saated ja nende uued osad salvestatakse
automaatselt ning on 6 kuud kuulatavad, telefonis või arvutis.

- Osad tulevad Kuku järelkuulamisest seni, kuni need on tasuta (umbes 4–5 nädalat pärast eetrit).
  Seal on reklaamid juba välja lõigatud.
- GitHub Actions kontrollib iga 3 tunni tagant uusi osi, laeb need GitHubi *Releases*'i ja kustutab
  üle 6 kuu vanad.
- Leht töötab GitHub Pages'is, sisselogimine käib parooliga ja brauser jääb aastaks sisse logituks.
- Pooleli jäänud osa jätkub samast kohast (iga brauser mäletab oma kohta).

## Seadistamine

Seda tehakse üks kord.

1. **Lülita leht sisse.** GitHubis: *Settings → Pages → Build and deployment → Source:*
   **GitHub Actions**.
2. **Käivita esimene uuendus.** *Actions → Kuku sync → Run workflow*. Mõne minuti pärast on leht
   aadressil `https://mssaar.github.io/kuku-raadio/`.
3. **Loo GitHubi võti** (lubab lehel saadete nimekirja muuta):
   1. ava <https://github.com/settings/personal-access-tokens/new>;
   2. *Token name*: `kuku-arhiiv`, *Expiration*: 1 aasta (või *Custom*);
   3. *Repository access*: **Only select repositories** → `kuku-raadio`;
   4. *Permissions → Repository permissions → Contents*: **Read and write**;
   5. *Generate token* ja kopeeri see (`github_pat_…`).
4. **Ava leht**, kleebi võti ja vali parool (vähemalt 12 märki). Parooli võid lähedastega jagada.

Võti salvestatakse repos ainult sinu parooliga krüpteerituna (`site/data/auth.json`). Kui võti
aegub, palub leht seadistada uuesti — loo uus võti ja korda 3.–4. sammu.

## Kui Kuku midagi muudab

Programm kasutab Kuku järelkuulamise liidest, mis pole ametlik avalik liides. Kui selle vastused
muutuvad, siis:

- lehe ülaossa ilmub punane teade „Kuku on midagi muutnud“;
- repos tekib *issue* sildiga `kuku-muutus` (GitHub saadab e-kirja);
- töövoog *Kuku sync* märgitakse ebaõnnestunuks.

Parandus käib failis `kuku/api.py`.

## Teadmiseks

- Repo ja helifailid on avalikud: parool kaitseb lehte ja saadete muutmist, aga *Releases*'i
  failid leiab ka otse GitHubist.
- Üks osa on ~110 MB. 10 iganädalast saadet × 6 kuud ≈ 29 GB (GitHub Releases'il kogumahu piirangut pole).

## Arendus

```
pip install -r requirements.txt
python -m pytest        # Pythoni testid
npm test                # lehe testid (Node 22)
python -m http.server -d site 8000
```

Failid:

- `kuku/api.py` — Kuku API klient ja kontrollid
- `kuku/logic.py` — millised osad laadida ja millal kustutada
- `kuku/releases.py` — GitHub Releases ja issue'd
- `kuku/sync.py` — taustatöö (`python -m kuku.sync`)
- `site/` — veebileht; `site/data/` — taustatöö kirjutatud andmed

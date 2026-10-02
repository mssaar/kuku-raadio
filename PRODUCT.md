# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Staatiline HTML/CSS/vanilla JS (ES-moodulid, ilma build-sammuta), avaldatud GitHub Pages'is. Andmed tulevad
`site/data/*.json` failidest, mida GitHub Actions uuendab. Kinnitatud tööplaanis
(`docs/superpowers/plans/2026-10-02-kuku-arhiiv.md`).

## Users

Omanik ja paar lähedast, kellega parooli jagatakse; viimased pole tehnilised. Kuulatakse peamiselt
telefonis — liikvel olles, jalutades, autos. Töö: leida Raadio Kuku saade, valida see salvestamiseks
ja hiljem salvestatud osi kuulata.

## Product Purpose

Isiklik Kuku saadete arhiiv: tasuta järelkuulamise aknas (~4–5 nädalat) olevad reklaamideta osad
salvestatakse automaatselt ja on kuulatavad 6 kuud. Õnnestumine: valitud saadete uued osad ilmuvad
ise ja neid saab telefonis vaevata kuulata.

## Positioning

Kuku enda pleier pakub osa tasuta vaid mõne nädala; see arhiiv hoiab valitud saateid pool aastat ühes
kohas, ilma reklaamideta, ilma et kasutaja peaks midagi meeles pidama.

## Operating Context

- Sisselogimine ühise parooliga; brauser jääb aastaks sisse logituks.
- Saadete otsing Kuku kataloogist (~146 saadet), "Salvesta"/"Eemalda".
- Osad: pealkiri, kuupäev, kestus (~45–50 min), kustumise kuupäev, pleier.
- Pikk osa jätkub sealt, kus kuulamine pooleli jäi (koht meeles brauseris).
- Uus saade: esimesed osad ilmuvad mõne minuti jooksul (taustatöö).
- Kui Kuku liides muutub, näitab leht selget hoiatust.

## Capabilities and Constraints

- Ainult staatiline leht; Kuku API-t brauserist pärida ei saa (CORS) — kõik andmed on eelnevalt kogutud.
- Helifailid on avalikud GitHub Releases'is; parool kaitseb kasutajaliidest ja saadete muutmist.
- Kogu tekst eesti keeles.
- Pole Kuku ametlik toode: ei tohi kasutada Kuku logo ega jäljendada Kuku brändi.

## Brand Commitments

- Kasutaja valis teadlikult tuttava voogedastusäpi grammatika: "midagi Spotify sarnast" (2026-10-02).
  Kvaliteedi latt on Spotify mobiiliäpp; Spotify logo, nime ega brändirohelist ei kasutata.
- Tulevikusoov (mitte praegu): salvestised mõnda kuulamisäppi viia (nt privaatne RSS-voog).

## Evidence on Hand

Kuku saadete nimed, kirjeldused ja ruudukujulised kaanepildid (`catalog.json`, pildid f302.pmo.ee).
Muud sisu, logo ega brändivara pole.

## Product Principles

- Kuulamine enne haldamist: telefonis avades on esimene asi värskeim osa ja pleier.
- Ise toimiv: pärast saate valimist ei pea kasutaja midagi tegema.
- Mittetehniline keel: ei mingit "token", "release", "sync" tavavaates.
- Ausad olekud: ootel, kustub varsti, Kuku muutus — alati nähtav ja arusaadav.

## Accessibility & Inclusion

Suured puutealad telefonis, loetav kontrast õues; pleier klaviatuuri ja ekraanilugejaga kasutatav.

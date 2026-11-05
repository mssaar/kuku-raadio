# Cloudflare Worker — Kuku Raadio Helivoo Vahendaja

See Worker lahendab probleemi, kus **iPhone (iOS Safari ja Messengeri sisebrauser)** keeldub mängimast GitHub Releases'is asuvaid saateid vale failitüübi (`application/octet-stream`) ja allalaadimise päise (`attachment`) tõttu.

Worker võtab GitHubi helivoo ning tagastab selle iPhone'ile puhta `Content-Type: audio/mpeg` ja `Content-Disposition: inline` päisega, toetades ka kerimist (*Range requests*).

Teenus on Cloudflare'is **100% tasuta** (tasuta pakett lubab kuni 100 000 päringut päevas, millest piisab isiklikuks arhiiviks enam kui küllalt).

---

## Paigaldamine 1 minutiga (veebibrauseris)

1. Logi sisse [dash.cloudflare.com](https://dash.cloudflare.com/) (kui kontot pole, loo tasuta konto).
2. Vali vasakult menüüst **Workers & Pages** -> **Overview** (või **Create application**).
3. Vajuta sinist nuppu **Create Worker**.
4. Pane nimeks näiteks `kuku-audio-proxy` ja vajuta **Deploy**.
5. Vajuta paremal üleval nupule **Edit code**.
6. Kustuta olemasolev näidiskood, kopeeri asemele faili [`worker.js`](worker.js) sisu ja vajuta **Deploy**.
7. Kopeeri oma Workeri aadress (näiteks: `https://kuku-audio-proxy.sinunimi.workers.dev`).

---

## Rakendusega ühendamine

Ava oma koodis fail [`site/data/config.json`](../site/data/config.json) ja lisa sinna oma Workeri aadress:

```json
{
  "repo": "mssaar/kuku-raadio",
  "audioProxy": "https://kuku-audio-proxy.sinunimi.workers.dev"
}
```

Pärast selle faili salvestamist ja GitHubi pushimist mängivad kõik saated iPhone'is (sh Messengeris ja Safaris) veebipleieris otse ja veatult.

---

## Alternatiiv: paigaldamine käsurealt (Wrangler)

Kui soovid paigaldada arvutist:

```bash
cd cloudflare-worker
npx wrangler login
npx wrangler deploy
```

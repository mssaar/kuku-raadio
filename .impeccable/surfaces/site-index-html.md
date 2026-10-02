---
version: 1
slug: "site-index-html"
primary_target: "site/index.html"
related_targets: []
---

# Kuku arhiiv — leht (site/index.html)

Mode: Operate. Telefon esmajärjekorras (390 px), töötab ka arvutis. Kasutajad: omanik + paar lähedast, mittetehnilised.
Ülesanne: kuula salvestatud osi (jätka poolelijäänut), lisa/eemalda saateid otsingu kaudu.
Piirangud: staatiline leht, eesti keel, Kuku brändi ei jäljendata, Spotify logo/nime/rohelist ei kasutata.

## Direction contract

THESIS: Isiklik arhiiv voogedastusäpi grammatikas (kasutaja valitud kanon: "Spotify sarnane"): kaanepildid ja pidev pleieririba juhivad, haldus on teisejärguline. Keeldub admin-tabeli / seadete-lehe paigutusest.

OWN-WORLD: Peaaegu must taust, üks heledusaste kõrgemad pinnad, ümarad kaanepildid ja pillikujulised nupud; üks soe merevaigukollane aktsent (raadioskaala lamp) ainult esitusele ja aktiivsele olekule; Figtree, rasked pealkirjad tiheda tähevahega; joonistatud SVG ikoonid ühes jämeduses.

STORY: Kuulaja avab telefonis, näeb kohe "Jätka" kaarti poolelijäänud või uusima osaga, vajutab esitust; pleieririba jääb alla. Saated kaanepiltidena; saate lehel osad koos kuupäeva, kestuse ja kustumisajaga. "Otsi" vaates leiab Kuku saate ja salvestab ühe nupuga.

FIRST VIEWPORT: Ülal tervitus päeva aja järgi + väljalogimise ikoon; selle all lai "Jätka kuulamist" plokk (kaas 72 px, pealkiri, saate nimi, edenemisriba, suur ümar esitusnupp paremal); edasi "Sinu saated" kaheveeruline kaanteruudustik. Põhja kinnitatud mini-pleier (kaas, pealkiri, edenemisjoon, esitus/paus) ja selle all alumine navigatsioon Kodu / Otsi. Esmane tegevus: esitusnupp.
Allkirjainteraktsioon: mini-pleier laieneb ühel teljel (alt üles) täisekraani "Praegu mängib" lehtedeks: suur kaas, kerimisriba, −15/+30 s, kiirus 1×/1,25×/1,5×; lukustuskuva juhtnupud Media Session API kaudu.

FORM: kanon (standing exit, kasutaja valik), kvaliteedi latt Spotify mobiiliäpp; seed 04f2ee18.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

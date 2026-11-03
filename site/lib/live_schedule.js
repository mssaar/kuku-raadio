/**
 * Raadio Kuku otse-eetri reklaamiajad ja striimide konfiguratsioon.
 */

export const KUKU_STREAM_URL = "https://router.euddn.net/8103046e16b71d15d692b57c187875c7/kuku.mp3";
export const SWISS_POP_STREAM_URL = "https://stream.srg-ssr.ch/m/rsp/mp3_128";

/**
 * Striimi puhverdamisest ja võrgukompressioonist tulenev viivitus (sekundites)
 * reaalajas stuudiokella ja kuulaja kõrvu jõudva helivoo vahel (~15 s).
 */
export const STREAM_DELAY_SEC = 15;

/**
 * Raadio Kuku stuudiokella järgsed ametlikud reklaamikõllide intervallid sekundites tunni algusest (0..3600):
 * Vastab kuku/live.py ja kuku/jingles.py etalonkõllide ajastusele:
 * 1. 20:28 - 21:42 (1228 .. 1302 s) — 1. reklaamipaus
 * 2. 33:10 - 34:49 (1990 .. 2089 s) — 2. reklaamipaus
 * 3. 45:44 - 47:54 (2744 .. 2874 s) — 3. reklaamipaus
 * 4. 57:43 - 60:00 (3463 .. 3600 s) — Saatelõpu reklaamid enne uudiseid
 * 5. 03:45 - 06:53 (225 .. 413 s) — Uudistejärgsed reklaamid enne uue saate algust
 */
export const STUDIO_AD_WINDOWS = [
  { name: "1. reklaamipaus", startSec: 1228, endSec: 1302 },
  { name: "2. reklaamipaus", startSec: 1990, endSec: 2089 },
  { name: "3. reklaamipaus", startSec: 2744, endSec: 2874 },
  { name: "Enne täistundi", startSec: 3463, endSec: 3600 },
  { name: "Pärast uudiseid", startSec: 225, endSec: 413 },
];

/**
 * Striimi viivitusega korrigeeritud reklaamiaknad kuulaja helivoo jaoks.
 */
export const AD_WINDOWS = STUDIO_AD_WINDOWS.map(w => {
  const startSec = (w.startSec + STREAM_DELAY_SEC) % 3600;
  const endSec = (w.endSec + STREAM_DELAY_SEC) % 3600;
  return {
    ...w,
    startSec,
    endSec,
    crossesHour: startSec > endSec,
  };
});

/**
 * Tuvastab, kas antud ajahetkel kõlab Kuku helivoos reklaamikõll ja reklaamipaus.
 * Võtab automaatselt arvesse striimi viivitust.
 * @param {Date} [date] - Kontrollitav aeg (vaikimisi praegune hetk)
 * @param {number} [delaySec] - Vooviivitus sekundites (vaikimisi STREAM_DELAY_SEC)
 * @returns {boolean}
 */
export function isKukuAdTime(date = new Date(), delaySec = STREAM_DELAY_SEC) {
  // Arvutame vastava helihetke stuudiokella järgi:
  const streamDate = delaySec ? new Date(date.getTime() - delaySec * 1000) : date;
  const m = streamDate.getMinutes();
  const s = streamDate.getSeconds();
  const sec = m * 60 + s;

  for (const w of STUDIO_AD_WINDOWS) {
    if (sec >= w.startSec && sec < w.endSec) {
      return true;
    }
  }
  return false;
}

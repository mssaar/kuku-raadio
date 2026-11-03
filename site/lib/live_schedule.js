/**
 * Raadio Kuku otse-eetri reklaamiajad ja striimide konfiguratsioon.
 */

export const KUKU_STREAM_URL = "https://router.euddn.net/8103046e16b71d15d692b57c187875c7/kuku.mp3";
export const SWISS_POP_STREAM_URL = "https://stream.srg-ssr.ch/m/rsp/mp3_128";

/**
 * Tavalised reklaami- ja vaheklipid igas tunnis sekundites (0..3600):
 * 1. 19:30 - 22:30 (1170 .. 1350 s)
 * 2. 33:00 - 35:30 (1980 .. 2130 s)
 * 3. 45:30 - 48:30 (2730 .. 2910 s)
 * 4. 58:00 - 03:30 (3480 .. 3600 s ja 0 .. 210 s)
 */
export const AD_WINDOWS = [
  { name: "1. reklaamipaus", startSec: 19 * 60 + 30, endSec: 22 * 60 + 30 },
  { name: "2. reklaamipaus", startSec: 33 * 60, endSec: 35 * 60 + 30 },
  { name: "3. reklaamipaus", startSec: 45 * 60 + 30, endSec: 48 * 60 + 30 },
  { name: "Täistunni paus", startSec: 58 * 60, endSec: 3 * 60 + 30, crossesHour: true },
];

/**
 * Tuvastab, kas antud ajahetkel on Kuku eetris tavapärane reklaamipaus.
 * @param {Date} [date] - Kontrollitav aeg (vaikimisi praegune hetk)
 * @returns {boolean}
 */
export function isKukuAdTime(date = new Date()) {
  const m = date.getMinutes();
  const s = date.getSeconds();
  const sec = m * 60 + s;

  for (const w of AD_WINDOWS) {
    if (w.crossesHour) {
      if (sec >= w.startSec || sec < w.endSec) return true;
    } else {
      if (sec >= w.startSec && sec < w.endSec) return true;
    }
  }
  return false;
}

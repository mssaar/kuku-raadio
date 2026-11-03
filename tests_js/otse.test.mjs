import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { isKukuAdTime, KUKU_STREAM_URL, SWISS_POP_STREAM_URL } from "../site/lib/live_schedule.js";

const SITE_DIR = path.resolve("site");

test("index.html navigatsioonis on olemas Otse-eetri sakk", () => {
  const indexHtml = fs.readFileSync(path.join(SITE_DIR, "index.html"), "utf-8");
  assert.ok(indexHtml.includes('href="#/otse"'), "Menüü peab sisaldama linki #/otse");
  assert.ok(indexHtml.includes('data-tab="live"'), "Menüülink peab omama data-tab='live'");
  assert.ok(indexHtml.includes('data-icon="live"'), "Menüülink peab omama data-icon='live'");
});

test("live_schedule.js arvutab Kuku reklaamiajad kõllide ja striimiviivituse järgi", () => {
  assert.ok(KUKU_STREAM_URL.includes("router.euddn.net") && KUKU_STREAM_URL.includes("kuku.mp3"));
  assert.ok(SWISS_POP_STREAM_URL.includes("stream.srg-ssr.ch") && SWISS_POP_STREAM_URL.includes("rsp/mp3_128"));

  // Tavalise saate keskel (nt 10:15) EI OLE reklaamipaus
  const dNormal = new Date(2026, 10, 3, 10, 15, 0);
  assert.equal(isKukuAdTime(dNormal), false);

  // 1. reklaamipaus: stuudios 20:28 - 21:42 (+15s striimiviivitus -> striimis 20:43 - 21:57)
  // 10:20:15: saate jutt kestab veel (vana kood lülitus siin valesti liiga vara)
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 20, 15)), false);
  // 10:20:45: reklaamikõll algas (20:43) -> lülitub muusikale
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 20, 45)), true);
  // 10:21:30: reklaamipaus kestab
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 21, 30)), true);
  // 10:22:00: reklaami lõpukõll lõppes (21:57) -> saade jätkub
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 22, 0)), false);

  // 2. reklaamipaus: stuudios 33:10 - 34:49 (+15s striimiviivitus -> striimis 33:25 - 35:04)
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 33, 0)), false);
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 34, 0)), true);
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 35, 10)), false);

  // 3. reklaamipaus: stuudios 45:44 - 47:54 (+15s striimiviivitus -> striimis 45:59 - 48:09)
  // 10:45:30: saade kestab veel (vana kood lülitus 45:30 liiga vara)
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 45, 30)), false);
  // 10:46:15: reklaamikõll kõlas -> reklaam
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 46, 15)), true);
  // 10:48:15: lõpukõll kõlas (48:09) -> saade jätkub
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 48, 15)), false);

  // Täistunni eelne reklaam: stuudios 57:43 - 60:00 (+15s -> 57:58 - 00:15)
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 57, 30)), false);
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 10, 58, 30)), true);
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 11, 0, 10)), true);

  // Täistunni uudised: 00:15 - 04:00 (uudised ei ole reklaamid)
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 11, 1, 30)), false);

  // Uudistejärgsed reklaamid enne uut saadet: stuudios 03:45 - 06:53 (+15s -> 04:00 - 07:08)
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 11, 4, 30)), true);
  assert.equal(isKukuAdTime(new Date(2026, 10, 3, 11, 7, 30)), false);
});

test("app.js toetab käsitsi tagasi lülitamist ega sunni vägisi muusikat peale", () => {
  const appJs = fs.readFileSync(path.join(SITE_DIR, "app.js"), "utf-8");
  assert.ok(appJs.includes("manualOverride"), "liveState peab sisaldama manualOverride lippu");
  assert.ok(appJs.includes("lastLiveAdState"), "app.js peab jälgima reklaamiaja olekuüleminekuid (lastLiveAdState)");
  assert.ok(appJs.includes("isAd !== lastLiveAdState"), "Automaatne vahetus peab toimuma ainult oleku muutumisel, mitte pidevalt üle kirjutades");
});

test("app.js sisaldab otse-eetri marsruuti ja ICONS.live ikooni", () => {
  const appJs = fs.readFileSync(path.join(SITE_DIR, "app.js"), "utf-8");
  assert.ok(appJs.includes("live: '<svg"), "ICONS.live peab olema defineeritud");
  assert.ok(appJs.includes('path === "/otse"'), "Marsruut #/otse peab olema implementeeritud");
  assert.ok(appJs.includes("renderLive"), "Funktsioon renderLive peab olema defineeritud");
});

test("app.js sisaldab Kuku ja Radio Swiss Pop striimide aadresse", () => {
  const appJs = fs.readFileSync(path.join(SITE_DIR, "app.js"), "utf-8");
  assert.ok(appJs.includes("router.euddn.net") && appJs.includes("kuku.mp3"), "Kuku otse-eetri striim peab olema konfigureeritud");
  assert.ok(appJs.includes("stream.srg-ssr.ch") && appJs.includes("rsp/mp3_128"), "Radio Swiss Pop asendusstriim peab olema konfigureeritud");
});

test("app.js initsialiseerub korrektselt (store on defineeritud enne liveState kasutust)", () => {
  const appJs = fs.readFileSync(path.join(SITE_DIR, "app.js"), "utf-8");
  const storePos = appJs.indexOf("const store =");
  const liveStatePos = appJs.indexOf("const liveState =");
  assert.ok(storePos !== -1, "store peab olema defineeritud");
  assert.ok(liveStatePos !== -1, "liveState peab olema defineeritud");
  assert.ok(storePos < liveStatePos, "store peab olema defineeritud ENNE liveState objekti (et vältida TDZ ReferenceError)");
});

test("app.js integreerib reaalajas helivoo akustilise kõllituvastaja LiveAudioDetector", () => {
  const appJs = fs.readFileSync(path.join(SITE_DIR, "app.js"), "utf-8");
  assert.ok(appJs.includes("LiveAudioDetector"), "app.js peab importima LiveAudioDetectori");
  assert.ok(appJs.includes("createMediaElementSource"), "app.js peab ühendama Kuku helivoo Web Audio API-ga");
  assert.ok(appJs.includes("jingles.json"), "app.js peab initsialiseerima kõllide profiilid (jingles.json)");
});

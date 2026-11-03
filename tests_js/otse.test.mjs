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

test("live_schedule.js arvutab Kuku reklaamiajad ja pakub voogude URL-e", () => {
  assert.ok(KUKU_STREAM_URL.includes("router.euddn.net") && KUKU_STREAM_URL.includes("kuku.mp3"));
  assert.ok(SWISS_POP_STREAM_URL.includes("stream.srg-ssr.ch") && SWISS_POP_STREAM_URL.includes("rsp/mp3_128"));

  // Tavalise saate keskel (nt 10:15) EI OLE reklaamipaus
  const dNormal = new Date(2026, 10, 3, 10, 15, 0);
  assert.equal(isKukuAdTime(dNormal), false);

  // 1. reklaamipaus: 19:45 -> reklaam
  const dAd1 = new Date(2026, 10, 3, 10, 20, 15);
  assert.equal(isKukuAdTime(dAd1), true);

  // 2. reklaamipaus: 34:00 -> reklaam
  const dAd2 = new Date(2026, 10, 3, 10, 34, 0);
  assert.equal(isKukuAdTime(dAd2), true);

  // 3. reklaamipaus: 46:30 -> reklaam
  const dAd3 = new Date(2026, 10, 3, 10, 46, 30);
  assert.equal(isKukuAdTime(dAd3), true);

  // Täistunni uudised/reklaamid: 59:10 -> reklaam
  const dAd4 = new Date(2026, 10, 3, 10, 59, 10);
  assert.equal(isKukuAdTime(dAd4), true);

  // Täistunni algus: 01:30 -> reklaam
  const dAd5 = new Date(2026, 10, 3, 11, 1, 30);
  assert.equal(isKukuAdTime(dAd5), true);

  // Pärast täistundi saate algus: 04:30 -> saate aeg
  const dShowStart = new Date(2026, 10, 3, 11, 4, 30);
  assert.equal(isKukuAdTime(dShowStart), false);
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

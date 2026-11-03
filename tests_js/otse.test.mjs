import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const SITE_DIR = path.resolve("site");

test("index.html navigatsioonis on olemas Otse-eetri sakk", () => {
  const indexHtml = fs.readFileSync(path.join(SITE_DIR, "index.html"), "utf-8");
  assert.ok(indexHtml.includes('href="#/otse"'), "Menüü peab sisaldama linki #/otse");
  assert.ok(indexHtml.includes('data-tab="live"'), "Menüülink peab omama data-tab='live'");
  assert.ok(indexHtml.includes('data-icon="live"'), "Menüülink peab omama data-icon='live'");
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

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const SITE_DIR = path.resolve("site");

test("icon.svg sisaldab Kuku logo ja mitte vana kollast ringi", () => {
  const content = fs.readFileSync(path.join(SITE_DIR, "icon.svg"), "utf-8");
  assert.ok(content.includes("#0062AC"), "Kuku brändi sinine (#0062AC) peab olema ikoonis");
  assert.ok(!content.includes("#f5b73b"), "Vana kollane ring (#f5b73b) ei tohi olla ikoonis");
  assert.ok(content.includes("svg"), "Korrektne SVG fail");
});

test("PNG ikoonid on kehtivad PNG-failid õige signatuuriga", () => {
  const pngHeader = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  for (const name of ["apple-touch-icon.png", "icon-192.png", "icon-512.png"]) {
    const filePath = path.join(SITE_DIR, name);
    assert.ok(fs.existsSync(filePath), `${name} peab eksisteerima`);
    const buf = fs.readFileSync(filePath);
    assert.ok(buf.length > 500, `${name} peab olema sisukas fail`);
    assert.ok(buf.subarray(0, 8).equals(pngHeader), `${name} peab olema kehtiv PNG`);
  }
});

test("app.js sisaldab värskendamise ikooni ja uut Kuku logo märki", () => {
  const appJs = fs.readFileSync(path.join(SITE_DIR, "app.js"), "utf-8");
  assert.ok(appJs.includes("refresh: '<svg"), "ICONS.refresh peab olema defineeritud");
  assert.ok(appJs.includes("#0062AC"), "ICONS.mark peab kasutama Kuku sinist värvi");
  assert.ok(!appJs.includes("#f5b73b"), "app.js ICONS.mark ei tohi sisaldada vana kollast ringi (#f5b73b)");
  assert.ok(appJs.includes("_t="), "fetchJson peab kasutama timestamp parameetrit puhvri eiramiseks");
  assert.ok(appJs.includes("refreshData"), "refreshData funktsioon peab olema defineeritud");
});

test("sw.js kasutab uut puhvriversiooni ja sisaldab live_schedule.js", () => {
  const swJs = fs.readFileSync(path.join(SITE_DIR, "sw.js"), "utf-8");
  assert.ok(swJs.includes('"kuku-v7"'), "sw.js peab kasutama CACHE_NAME kuku-v7");
  assert.ok(swJs.includes("live_schedule.js"), "sw.js ASSETS peab sisaldama live_schedule.js");
  assert.ok(swJs.includes("live_detector.js"), "sw.js ASSETS peab sisaldama live_detector.js");
  assert.ok(swJs.includes("jingles.json"), "sw.js ASSETS peab sisaldama jingles.json");
});

test("index.html ja manifest.webmanifest kasutavad vahemälu versiooniparameetreid", () => {
  const indexHtml = fs.readFileSync(path.join(SITE_DIR, "index.html"), "utf-8");
  assert.ok(indexHtml.includes('manifest.webmanifest?v='), "manifest.webmanifest peab omama versioonitunnust");
  assert.ok(indexHtml.includes('apple-touch-icon.png?v='), "apple-touch-icon.png peab omama versioonitunnust");
  assert.ok(indexHtml.includes('icon.svg?v='), "icon.svg peab omama versioonitunnust");

  const manifest = JSON.parse(fs.readFileSync(path.join(SITE_DIR, "manifest.webmanifest"), "utf-8"));
  assert.ok(manifest.id && manifest.id.includes("v="), "manifest peab omama id välja versiooniga");
  assert.ok(manifest.icons.some(i => i.src.includes("icon-192.png?v=")), "icon-192.png peab omama versioonitunnust");
});

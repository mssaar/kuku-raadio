import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const SITE_DIR = path.resolve("site");

test("paroolifail auth.json ja krüptomoodul crypto.js on eemaldatud", () => {
  assert.ok(!fs.existsSync(path.join(SITE_DIR, "data", "auth.json")), "auth.json ei tohi eksisteerida");
  assert.ok(!fs.existsSync(path.join(SITE_DIR, "lib", "crypto.js")), "crypto.js ei tohi eksisteerida");
});

test("app.js ei sisalda sisselogimise ega parooliloogikat", () => {
  const appJs = fs.readFileSync(path.join(SITE_DIR, "app.js"), "utf-8");
  assert.ok(!appJs.includes("renderLogin"), "app.js ei tohi sisaldada funktsiooni renderLogin");
  assert.ok(!appJs.includes("renderSetup"), "app.js ei tohi sisaldada funktsiooni renderSetup");
  assert.ok(!appJs.includes("crypto.js"), "app.js ei tohi importida crypto.js");
  assert.ok(!appJs.includes("auth.json"), "app.js ei tohi viidata auth.json failile");
  assert.ok(!appJs.includes("password"), "app.js ei tohi sisaldada paroolivälju");
  assert.ok(!appJs.includes("signOut"), "app.js ei tohi sisaldada väljalogimise loogikat");
  assert.ok(!appJs.includes('id="logout"'), "app.js ei tohi sisaldada logout nuppu");
});

test("sw.js ei puhverda crypto.js faili", () => {
  const swJs = fs.readFileSync(path.join(SITE_DIR, "sw.js"), "utf-8");
  assert.ok(!swJs.includes("crypto.js"), "sw.js ei tohi sisaldada crypto.js");
});

test("index.html navigatsiooniriba ei ole algselt peidetud", () => {
  const indexHtml = fs.readFileSync(path.join(SITE_DIR, "index.html"), "utf-8");
  assert.ok(indexHtml.includes('<nav id="tabs" class="tabs" aria-label="Peamenüü">'), "Navigatsioon peab olema nähtav");
});

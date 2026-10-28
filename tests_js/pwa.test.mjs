import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const SITE_DIR = path.resolve("site");

test("manifest.webmanifest on korrektne PWA manifest", () => {
  const content = fs.readFileSync(path.join(SITE_DIR, "manifest.webmanifest"), "utf-8");
  const manifest = JSON.parse(content);
  assert.equal(manifest.name, "Kuku arhiiv");
  assert.equal(manifest.short_name, "Kuku");
  assert.equal(manifest.display, "standalone");
  assert.equal(manifest.start_url, "./");
  assert.ok(Array.isArray(manifest.icons));
  assert.ok(manifest.icons.length >= 2);
  assert.ok(manifest.icons.some(i => i.sizes === "192x192"));
  assert.ok(manifest.icons.some(i => i.sizes === "512x512"));
});

test("PWA ja iOS ikoonifailid ning Service Worker on olemas", () => {
  assert.ok(fs.existsSync(path.join(SITE_DIR, "sw.js")));
  assert.ok(fs.existsSync(path.join(SITE_DIR, "icon-192.png")));
  assert.ok(fs.existsSync(path.join(SITE_DIR, "icon-512.png")));
  assert.ok(fs.existsSync(path.join(SITE_DIR, "apple-touch-icon.png")));
});

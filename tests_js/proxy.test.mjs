import test from "node:test";
import assert from "node:assert/strict";
import worker from "../cloudflare-worker/worker.js";
import { resolveAudioUrl } from "../site/lib/proxy.js";

test("resolveAudioUrl tagastab algse URL-i kui proxy pole seadistatud", () => {
  const ghUrl = "https://github.com/mssaar/kuku-raadio/releases/download/saade-214/1793790002.mp3";
  assert.equal(resolveAudioUrl(ghUrl, ""), ghUrl);
  assert.equal(resolveAudioUrl(ghUrl, null), ghUrl);
  assert.equal(resolveAudioUrl("", "https://proxy.workers.dev"), "");
});

test("resolveAudioUrl suunab GitHubi lingi läbi proxy", () => {
  const ghUrl = "https://github.com/mssaar/kuku-raadio/releases/download/saade-214/1793790002.mp3";
  const proxy = "https://kuku-proxy.workers.dev";
  const resolved = resolveAudioUrl(ghUrl, proxy);
  assert.equal(
    resolved,
    `https://kuku-proxy.workers.dev/?url=${encodeURIComponent(ghUrl)}`
  );

  // Eemaldab kaldkriipsu proxy aadressi lõpust
  const resolvedSlash = resolveAudioUrl(ghUrl, "https://kuku-proxy.workers.dev/");
  assert.equal(
    resolvedSlash,
    `https://kuku-proxy.workers.dev/?url=${encodeURIComponent(ghUrl)}`
  );
});

test("resolveAudioUrl ei muuda kolmandate osapoolte aadresse", () => {
  const otherUrl = "https://router.euddn.net/kuku.mp3";
  assert.equal(resolveAudioUrl(otherUrl, "https://proxy.workers.dev"), otherUrl);
});

test("Cloudflare Worker vastab OPTIONS päringule CORS päistega ja staatusega 204", async () => {
  const req = new Request("https://worker.test/", { method: "OPTIONS" });
  const res = await worker.fetch(req);
  assert.equal(res.status, 204);
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), "*");
  assert.ok(res.headers.get("Access-Control-Allow-Methods").includes("GET"));
});

test("Cloudflare Worker blokeerib mittetoetatud HTTP meetodid (POST)", async () => {
  const req = new Request("https://worker.test/?url=https://github.com/test.mp3", { method: "POST" });
  const res = await worker.fetch(req);
  assert.equal(res.status, 405);
});

test("Cloudflare Worker annab selgituse kui ?url parameeter puudub", async () => {
  const req = new Request("https://worker.test/");
  const res = await worker.fetch(req);
  assert.equal(res.status, 200);
  const text = await res.text();
  assert.ok(text.includes("Kuku Raadio Audio Proxy töötab"));
});

test("Cloudflare Worker blokeerib kahtlased või mitte-GitHub domeenid (SSRF kaitse)", async () => {
  const req = new Request("https://worker.test/?url=https://evil.com/malicious.mp3");
  const res = await worker.fetch(req);
  assert.equal(res.status, 403);
});

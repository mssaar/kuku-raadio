import { test } from "node:test";
import assert from "node:assert/strict";
import { saveSession, loadSession, clearSession } from "../site/lib/session.js";

function mem() {
  const m = new Map();
  return { getItem: k => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k) };
}

test("sessioon kehtib aasta", () => {
  const s = mem(), now = Date.UTC(2026, 9, 2);
  saveSession(s, "tok", now);
  assert.equal(loadSession(s, now + 364 * 864e5), "tok");
  assert.equal(loadSession(s, now + 366 * 864e5), null);
});

test("väljalogimine ja katkine sisu", () => {
  const s = mem();
  saveSession(s, "tok");
  clearSession(s);
  assert.equal(loadSession(s), null);
  s.setItem("kuku.session", "{katki");
  assert.equal(loadSession(s), null);
});

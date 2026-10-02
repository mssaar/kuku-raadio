import { test } from "node:test";
import assert from "node:assert/strict";
import { savePosition, loadPosition, isFinished, lastInProgress } from "../site/lib/progress.js";

function mem() {
  const m = new Map();
  return { getItem: k => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k) };
}

test("koht salvestub ja loetakse osa kaupa", () => {
  const s = mem();
  savePosition(s, 77, 600, 2800, 1000);
  assert.equal(loadPosition(s, 77), 600);
  assert.equal(loadPosition(s, 78), 0);
});

test("lõpuni kuulatud osa on lõpetatud ja algab algusest", () => {
  const s = mem();
  savePosition(s, 77, 2790, 2800);
  assert.ok(isFinished(s, 77));
  assert.equal(loadPosition(s, 77), 0);
});

test("viimati kuulatud pooleli osa", () => {
  const s = mem();
  savePosition(s, 1, 100, 2800, 1000);
  savePosition(s, 2, 200, 2800, 2000);
  savePosition(s, 3, 2799, 2800, 3000);
  assert.equal(lastInProgress(s, [1, 2, 3]), 2);
  assert.equal(lastInProgress(s, [1]), 1);
  assert.equal(lastInProgress(s, [9]), null);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { normalize, searchShows } from "../site/lib/search.js";

const shows = [
  { id: 1, name: "Digitund", description: "Tehnoloogia" },
  { id: 2, name: "Õiguse horisont", description: "" },
  { id: 3, name: "Kuku hommikuraadio", description: "digi uudised" },
];

test("normalize eemaldab täpid ja suurtähed", () => {
  assert.equal(normalize("Õiguse HÖRISONT"), "oiguse horisont");
});

test("nimi enne kirjeldust, täpitähed paindlikud", () => {
  assert.deepEqual(searchShows(shows, "digi").map(s => s.id), [1, 3]);
  assert.deepEqual(searchShows(shows, "oigus").map(s => s.id), [2]);
  assert.deepEqual(searchShows(shows, "  ").map(s => s.id), []);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { encryptToken, decryptToken } from "../site/lib/crypto.js";

test("krüpteeri ja dekrüpteeri", async () => {
  const blob = await encryptToken("ghp_abc", "salasõna", 1000);
  assert.equal(blob.v, 1);
  assert.ok(!JSON.stringify(blob).includes("ghp_abc"));
  assert.equal(await decryptToken(blob, "salasõna"), "ghp_abc");
});

test("vale parool annab WrongPassword", async () => {
  const blob = await encryptToken("ghp_abc", "õige", 1000);
  await assert.rejects(decryptToken(blob, "vale"), { name: "WrongPassword" });
});

test("rikutud blob annab WrongPassword", async () => {
  await assert.rejects(decryptToken({ v: 1, salt: "x", iv: "y", iterations: 1000, ciphertext: "z" }, "p"),
    { name: "WrongPassword" });
});

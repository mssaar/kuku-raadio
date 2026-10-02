// GitHubi võtme krüpteerimine parooliga (PBKDF2-SHA256 → AES-GCM 256).
const enc = new TextEncoder();
const dec = new TextDecoder();
const b64 = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes)));
const unb64 = text => Uint8Array.from(atob(text), c => c.charCodeAt(0));

async function deriveKey(password, salt, iterations) {
  const base = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt, iterations },
    base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

export async function encryptToken(token, password, iterations = 600000) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(password, salt, iterations);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, enc.encode(token));
  return { v: 1, salt: b64(salt), iv: b64(iv), iterations, ciphertext: b64(ciphertext) };
}

export async function decryptToken(blob, password) {
  try {
    const key = await deriveKey(password, unb64(blob.salt), blob.iterations);
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(blob.iv) }, key, unb64(blob.ciphertext));
    return dec.decode(plain);
  } catch {
    const err = new Error("Vale parool");
    err.name = "WrongPassword";
    throw err;
  }
}

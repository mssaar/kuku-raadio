// Repo failide lugemine ja kirjutamine GitHub Contents API kaudu.
const API = "https://api.github.com";

function headers(token) {
  return { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json" };
}

function toBase64Utf8(text) {
  return btoa(String.fromCharCode(...new TextEncoder().encode(text)));
}

function fromBase64Utf8(b64) {
  return new TextDecoder().decode(Uint8Array.from(atob(b64.replace(/\n/g, "")), c => c.charCodeAt(0)));
}

export class AuthError extends Error {
  constructor() {
    super("GitHubi võti ei kehti või tal pole õigusi");
    this.name = "AuthError";
  }
}

export async function getFile(repo, path, token) {
  const resp = await fetch(`${API}/repos/${repo}/contents/${path}`, { headers: headers(token), cache: "no-store" });
  if (resp.status === 404) return null;
  if (resp.status === 401 || resp.status === 403) throw new AuthError();
  if (!resp.ok) throw new Error(`GitHub vastas ${resp.status}`);
  const data = await resp.json();
  return { json: JSON.parse(fromBase64Utf8(data.content)), sha: data.sha };
}

export async function putFile(repo, path, value, sha, token, message) {
  const body = { message, content: toBase64Utf8(JSON.stringify(value, null, 1) + "\n") };
  if (sha) body.sha = sha;
  const resp = await fetch(`${API}/repos/${repo}/contents/${path}`,
    { method: "PUT", headers: headers(token), body: JSON.stringify(body) });
  if (resp.status === 401 || resp.status === 403) throw new AuthError();
  if (resp.status === 409) throw new Error("Fail muutus vahepeal, proovi uuesti");
  if (!resp.ok) throw new Error(`GitHub vastas ${resp.status}`);
  return (await resp.json()).content.sha;
}

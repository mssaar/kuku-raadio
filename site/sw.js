const CACHE_NAME = "kuku-v2";
const ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
  "./icon.svg",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png",
  "./manifest.webmanifest",
  "./lib/crypto.js",
  "./lib/github.js",
  "./lib/progress.js",
  "./lib/search.js",
  "./lib/session.js"
];

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);

  // ÄRA KUNAGI puutu teiste domeenide päringuid (GitHub Releases helifailid, ümbersuunamised, CDN jne)!
  // See hoiab ära helivoogude hangumise ja Range-päringute katkemise.
  if (url.origin !== self.location.origin) {
    return;
  }

  // Ära puutu helifaile, andmefaile ega Range päringuid
  if (
    event.request.destination === "audio" ||
    event.request.destination === "video" ||
    event.request.headers.has("range") ||
    url.pathname.includes("/data/") ||
    url.pathname.endsWith(".mp3")
  ) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});

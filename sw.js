// Skyline service worker — installable PWA + offline app shell
const CACHE = "skyline-v1";
const SHELL = [
  "/", "/static/style.css", "/static/app.js",
  "/static/vendor/chart.umd.js",
  "/static/vendor/leaflet/leaflet.js", "/static/vendor/leaflet/leaflet.css",
  "/static/icons/icon-192.png", "/manifest.webmanifest"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.origin !== location.origin) return;           // let tiles/fonts/APIs hit the network
  if (url.pathname.startsWith("/api/")) {                // API: network first, fall back to cache
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }
  // static shell: cache first
  e.respondWith(
    caches.match(e.request).then((cached) => cached ||
      fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      }).catch(() => caches.match("/")))
  );
});

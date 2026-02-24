const CACHE = "shem-tov-v3";  // bump when assets change

// Assets to cache on first install (app shell)
const PRECACHE = [
  "/",
  "/static/manifest.json",
  "/static/names.json",          // critical — needed for offline card browsing
  "/static/icons/icon-192.png",
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  // Never intercept API calls — let JS handle fallback via localStorage
  if (url.pathname.startsWith("/api/")) return;

  // Network-first for HTML navigation (fresh page when online)
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
          return res;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  // Cache-first for static assets (JS, CSS, fonts, icons, names.json)
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) {
        // Refresh in background
        fetch(e.request).then(res => {
          if (res && res.status === 200)
            caches.open(CACHE).then(c => c.put(e.request, res));
        }).catch(err => { console.error('SW background fetch failed:', err); });
        return cached;
      }
      return fetch(e.request).then(res => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      });
    })
  );
});

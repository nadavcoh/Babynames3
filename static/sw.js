const CACHE = "shem-tov-v6";

const PRECACHE = [
  "/static/manifest.json",
  "/static/names.json",
  "/static/icons/icon-192.png",
];

// Minimal offline shell — shown when cache is empty and server is unreachable.
// Self-contained: no network requests, loads app state from localStorage.
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>\u05E9\u05DD \u05D8\u05D5\u05D1</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#f7f3ee;color:#1a1208;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:32px 24px;text-align:center}
.logo{font-size:2rem;font-weight:900;letter-spacing:-.5px;margin-bottom:8px}
.logo span{color:#c8973a}
h2{font-size:1.1rem;font-weight:700;margin:24px 0 8px}
p{font-size:.85rem;color:#8a7f74;line-height:1.6;margin-bottom:16px}
.pill{display:inline-block;background:#e8f3ec;color:#2d6b45;font-size:.75rem;font-weight:700;padding:4px 12px;border-radius:14px;margin:4px}
.names{margin-top:16px;font-size:1.4rem;direction:rtl;line-height:2;color:#1a5c8a}
.retry{margin-top:28px;background:#1a1208;color:#f7f3ee;border:none;border-radius:22px;padding:12px 28px;font-size:.9rem;font-weight:600;cursor:pointer}
.note{font-size:.72rem;color:#b0a898;margin-top:12px}
</style>
</head>
<body>
<div class="logo">\u05E9\u05DD <span>\u05D8\u05D5\u05D1</span></div>
<p style="font-size:.8rem;color:#9b2335;font-weight:600">\u26A1 Server unreachable</p>
<h2>Your saved names</h2>
<div class="names" id="names-out">Loading\u2026</div>
<button class="retry" onclick="location.reload()">Try reconnecting</button>
<p class="note">Make sure Tailscale is running on your iPhone,<br>then tap "Try reconnecting".</p>
<script>
try{
  var saved = JSON.parse(localStorage.getItem('local-state') || '{}');
  var liked = saved.liked || [];
  var ratings = JSON.parse(localStorage.getItem('cached-ratings') || '{}');
  var el = document.getElementById('names-out');
  if(!liked.length){ el.textContent = 'No saved names yet.'; }
  else {
    el.innerHTML = liked.map(function(h){
      var r = ratings[h] || 0;
      var stars = r ? '\u2605'.repeat(r) : '';
      return '<div>' + h + (stars ? ' <span style="font-size:.9rem;color:#c8973a">' + stars + '</span>' : '') + '</div>';
    }).join('');
  }
}catch(e){}
</script>
</body>
</html>`;

// ── Install: cache app shell ─────────────────────────────────────────────────
self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: clear old caches ───────────────────────────────────────────────
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// ── Fetch: serve from cache, fall back to embedded offline page ──────────────
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  // API calls: pass through, never cache
  if (url.pathname.startsWith("/api/")) return;

  if (e.request.mode === "navigate") {
    e.respondWith(
      // Always try network first — HTML is never cached (changes with every deploy)
      fetch(e.request)
        .catch(() =>
          // Network failed → embedded offline shell
          new Response(OFFLINE_HTML, {
            headers: { "Content-Type": "text/html; charset=utf-8" }
          })
        )
    );
    return;
  }

  // Static assets: cache-first, refresh in background
  e.respondWith(
    caches.match(e.request).then(cached => {
      const networkFetch = fetch(e.request).then(res => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => null);

      return cached || networkFetch;
    })
  );
});

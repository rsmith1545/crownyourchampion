/* Admin PWA service worker — scoped to /admin.html, isolated from sw_hub. */
const CACHE = 'cyc-admin-v1';
const ASSETS = ['/admin.html', '/admin-icon-192.png', '/admin-icon-512.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()).catch(()=>self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE && k.indexOf('cyc-admin') === 0).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  let u; try { u = new URL(e.request.url); } catch (_) { return; }
  // Never touch cross-origin (Firebase/Firestore/Google auth/gstatic) — let them go straight to network.
  if (u.origin !== location.origin) return;
  // Admin doc: network-first so data/UI stay fresh, fall back to cache offline.
  if (e.request.mode === 'navigate' || u.pathname === '/admin.html') {
    e.respondWith(
      fetch(e.request).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put('/admin.html', cp)); return r; })
                      .catch(() => caches.match('/admin.html'))
    );
    return;
  }
  // Same-origin static assets: cache-first.
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});

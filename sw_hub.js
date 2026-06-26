/* eslint-disable no-undef */
var cacheName = 'crown-champion-hub-v4';
var assets = [
  './',
  './index.html',
  './cyc-logo.png',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable-512.png',
  '/apple-touch-icon.png',
  './manifest_hub.json'
];

self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(caches.open(cacheName).then(function(cache){ return cache.addAll(assets); }).catch(function(){}));
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){ return k !== cacheName; }).map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(event) {
  var req = event.request;
  var _u; try { _u = new URL(req.url); } catch(e) { _u = null; }
  // Leave the Admin PWA's scope + assets entirely to sw_admin / network.
  if (_u && _u.origin === location.origin && (_u.pathname.indexOf('/admin') === 0 || _u.pathname === '/manifest_admin.json' || _u.pathname === '/sw_admin.js')) { return; }
  var isHTML = req.mode === 'navigate' || (req.headers.get('accept') || '').indexOf('text/html') !== -1;
  if (isHTML) {
    // Network-first, bypass HTTP cache so deploys show immediately
    event.respondWith(
      fetch(req, { cache: 'reload' }).then(function(r){
        var copy = r.clone(); caches.open(cacheName).then(function(c){ c.put(req, copy); }); return r;
      }).catch(function(){ return caches.match(req).then(function(r){ return r || caches.match('./index.html'); }); })
    );
    return;
  }
  event.respondWith(caches.match(req).then(function(r){ return r || fetch(req); }));
});

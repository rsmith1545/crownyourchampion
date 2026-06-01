/* eslint-disable no-undef */
var cacheName = 'crown-champion-ff-v1';
var assets = [
  './',
  './index.html',
  './manifest_ff.json',
  './bg-gorge.jpg',
  './bg-westpalm.jpg',
  './bg-spac.jpg',
  './bg-camden.jpg'
];
self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(caches.open(cacheName).then(function(cache){ return cache.addAll(assets); }));
});
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){return k!==cacheName;}).map(function(k){return caches.delete(k);}));
    }).then(function(){ return self.clients.claim(); })
  );
});
self.addEventListener('fetch', function(event) {
  var req = event.request;
  var isHTML = req.mode === 'navigate' || (req.headers.get('accept')||'').indexOf('text/html') !== -1;
  if (isHTML) {
    event.respondWith(
      fetch(req).then(function(response){
        var copy = response.clone();
        caches.open(cacheName).then(function(cache){ cache.put(req, copy); });
        return response;
      }).catch(function(){ return caches.match(req).then(function(r){ return r || caches.match('./index.html'); }); })
    );
    return;
  }
  event.respondWith(caches.match(req).then(function(response){ return response || fetch(req); }));
});

/* eslint-disable no-undef */
var cacheName = 'crown-champion-hendrix-v2';
var assets = ['./','./index.html','./manifest_hendrix.json','./cyc-logo.png'];
self.addEventListener('install', function(e){ self.skipWaiting(); e.waitUntil(caches.open(cacheName).then(function(c){return c.addAll(assets);})); });
self.addEventListener('activate', function(e){ e.waitUntil(caches.keys().then(function(keys){return Promise.all(keys.filter(function(k){return k!==cacheName;}).map(function(k){return caches.delete(k);}));}).then(function(){return self.clients.claim();})); });
self.addEventListener('fetch', function(e){
  var req=e.request;
  try{ if(new URL(req.url).origin !== self.location.origin) return; }catch(_){ return; }
  var isHTML=req.mode==='navigate'||(req.headers.get('accept')||'').indexOf('text/html')!==-1;
  if(isHTML){ e.respondWith(fetch(req).then(function(r){var c=r.clone();caches.open(cacheName).then(function(ca){ca.put(req,c);});return r;}).catch(function(){return caches.match(req).then(function(r){return r||caches.match('./index.html');});})); return; }
  e.respondWith(caches.match(req).then(function(r){return r||fetch(req);}));
});

var CACHE='sfs-v1';
var ASSETS=['/shuffle/home.html','/shuffle/index.html','/shuffle/manifest.webmanifest','/shuffle/icon-192.png','/shuffle/icon-512.png','/shuffle/apple-touch-icon.png'];
self.addEventListener('install',function(e){ e.waitUntil(caches.open(CACHE).then(function(c){return c.addAll(ASSETS).catch(function(){});}).then(function(){return self.skipWaiting();})); });
self.addEventListener('activate',function(e){ e.waitUntil(caches.keys().then(function(keys){return Promise.all(keys.map(function(k){if(k!==CACHE)return caches.delete(k);}));}).then(function(){return self.clients.claim();})); });
self.addEventListener('fetch',function(e){ var req=e.request; try{ if(new URL(req.url).origin!==self.location.origin) return; }catch(_){ return; }
  e.respondWith(caches.match(req).then(function(r){ return r||fetch(req).catch(function(){ return caches.match('/shuffle/home.html'); }); })); });

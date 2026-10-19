const CACHE = 'fieldnote-shell-v12';
const ASSETS = ['/', '/index.html', '/style.css', '/app.js', '/camera.js', '/local-store.js', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('fieldnote-shell-') && k!==CACHE).map(k=>caches.delete(k)))));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if(event.request.method!=='GET' || url.origin!==self.location.origin || !ASSETS.includes(url.pathname)) return;
  // Public application shell only. Never cache API responses, photos or exports.
  event.respondWith(fetch(event.request).catch(()=>caches.match(url.pathname)));
});

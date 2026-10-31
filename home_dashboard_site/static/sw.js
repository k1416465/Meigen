// PWA install support. Network behavior remains unchanged.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
// A fetch listener enables PWA install criteria without caching dynamic Flask pages.
self.addEventListener('fetch', () => {});

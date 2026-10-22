const CACHE_NAME = 'pc-remote-v4';
const SHELL_ASSETS = [
  '/',
  '/index.html',
  '/assets/icons.svg',
  '/assets/fonts/DMSansVariable.woff2',
  '/assets/logo/favicon.svg',
  '/assets/logo/icon-192.png',
  '/assets/logo/icon-512.png',
  '/css/tokens.css',
  '/css/base.css',
  '/css/components.css',
  '/css/screens.css',
  '/css/editor.css',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/icons/')) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((res) => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return res;
      })
      .catch(() => caches.match(request))
  );
});

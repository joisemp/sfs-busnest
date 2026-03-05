// BusNest Service Worker
const CACHE_VERSION = 'v3';
const CACHE_NAME = `busnest-${CACHE_VERSION}`;

// Static assets to pre-cache (app shell)
const PRECACHE_ASSETS = [
  '/',
  '/static/utils/bootstrap/css/bootstrap.min.css',
  '/static/utils/bootstrap/js/bootstrap.bundle.min.js',
  '/static/utils/htmx/htmx.min.js',
  '/static/images/logo.svg',
  '/static/images/logo-icon.svg',
  '/static/images/profile-default-icon.jpg',
  '/static/manifest.json',
];

// Install event — pre-cache app shell assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate event — clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event — cache strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip browser extensions, admin URLs, and cross-origin requests
  if (
    url.origin !== location.origin ||
    url.pathname.startsWith('/admin/') ||
    url.pathname.startsWith('/media/')
  ) {
    return;
  }

  // Network-first for static assets (CSS/JS/images)
  // Always fetches fresh from network; falls back to cache only when offline.
  // This ensures style/script updates are visible immediately without hard reload.
  if (
    url.pathname.startsWith('/static/') ||
    url.pathname.startsWith('/staticfiles/')
  ) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Network-first for HTML pages (navigation requests)
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then((cached) => {
            if (cached) return cached;
            // Fallback to cached home page if available
            return caches.match('/');
          });
        })
    );
  }
});

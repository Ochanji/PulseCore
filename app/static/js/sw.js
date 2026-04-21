const CACHE_NAME = 'pulsecore-v1';
const STATIC_ASSETS = [
  '/',
  '/apps/',
  '/static/css/main.css',
  '/static/manifest.json',
  'https://cdn.tailwindcss.com',
];

// Install — cache static shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

// Activate — clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch — network-first for API/forms, cache-first for static assets
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Never intercept non-GET or cross-origin requests except CDN
  if (event.request.method !== 'GET') return;
  if (url.origin !== location.origin && !url.hostname.includes('tailwindcss')) return;

  // Static assets → cache first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cached => cached || fetch(event.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        return resp;
      }))
    );
    return;
  }

  // Navigation / HTML → network first, fallback to cache
  event.respondWith(
    fetch(event.request)
      .then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return resp;
      })
      .catch(() => caches.match(event.request).then(cached => cached || caches.match('/')))
  );
});

// Background sync — replay queued form submissions
self.addEventListener('sync', event => {
  if (event.tag === 'sync-submissions') {
    event.waitUntil(replayQueue());
  }
});

async function replayQueue() {
  const db = await openDB();
  const tx = db.transaction('queue', 'readwrite');
  const store = tx.objectStore('queue');
  const all = await promisify(store.getAll());
  for (const item of all) {
    try {
      const resp = await fetch(item.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: item.body,
      });
      if (resp.ok || resp.redirected) {
        await promisify(store.delete(item.id));
      }
    } catch (_) { /* stay in queue, retry next sync */ }
  }
}

function openDB() {
  return new Promise((res, rej) => {
    const req = indexedDB.open('pulsecore', 1);
    req.onupgradeneeded = e => e.target.result.createObjectStore('queue', { keyPath: 'id', autoIncrement: true });
    req.onsuccess = e => res(e.target.result);
    req.onerror = e => rej(e);
  });
}

function promisify(req) {
  return new Promise((res, rej) => {
    req.onsuccess = e => res(e.target.result);
    req.onerror = e => rej(e);
  });
}

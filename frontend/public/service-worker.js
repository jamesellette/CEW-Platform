/* eslint-disable no-restricted-globals */
/**
 * CEW Training Platform Service Worker
 * Provides offline support and caching for the PWA
 * 
 * SAFETY NOTE: This service worker is designed for training environments only.
 * It caches application assets for offline access but does NOT cache
 * sensitive operational data.
 */

const CACHE_NAME = 'cew-platform-v1';
const STATIC_CACHE = 'cew-static-v1';
const DYNAMIC_CACHE = 'cew-dynamic-v1';

// Assets to cache on install (App Shell)
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/static/js/main.js',
  '/static/css/main.css'
];

// API endpoints that should always go to network
const NETWORK_ONLY_PATHS = [
  '/auth/',
  '/kill-switch',
  '/labs/',
  '/recordings/',
  '/ws/'
];

// API endpoints that can be cached for offline viewing
const CACHE_FIRST_PATHS = [
  '/topologies',
  '/mitre-attack/tactics',
  '/mitre-attack/techniques',
  '/progress/badges',
  '/progress/skill-categories',
  '/rf-simulation/frequency-bands',
  '/rf-simulation/threats'
];

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        // Don't fail installation if some assets aren't available
        return Promise.allSettled(
          STATIC_ASSETS.map(url => 
            cache.add(url).catch(err => console.log(`[SW] Failed to cache: ${url}`, err))
          )
        );
      })
      .then(() => {
        console.log('[SW] Static assets cached');
        return self.skipWaiting();
      })
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Remove old versioned caches
              return name.startsWith('cew-') && 
                     name !== CACHE_NAME && 
                     name !== STATIC_CACHE && 
                     name !== DYNAMIC_CACHE;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

/**
 * Determine caching strategy based on request URL
 */
function getCacheStrategy(url) {
  const pathname = new URL(url).pathname;
  
  // Network only for authentication and real-time operations
  if (NETWORK_ONLY_PATHS.some(path => pathname.includes(path))) {
    return 'network-only';
  }
  
  // Cache first for reference data
  if (CACHE_FIRST_PATHS.some(path => pathname.includes(path))) {
    return 'cache-first';
  }
  
  // Static assets - cache first
  if (pathname.startsWith('/static/') || 
      pathname.endsWith('.js') || 
      pathname.endsWith('.css') ||
      pathname.endsWith('.png') ||
      pathname.endsWith('.ico')) {
    return 'cache-first';
  }
  
  // API calls - network first with cache fallback
  if (pathname.startsWith('/api/') || pathname.includes('/scenarios')) {
    return 'network-first';
  }
  
  // Default: network first
  return 'network-first';
}

/**
 * Cache-first strategy
 */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.log('[SW] Cache-first fetch failed:', error);
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Network-first strategy with cache fallback
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      console.log('[SW] Serving from cache:', request.url);
      return cached;
    }
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      const offlinePage = await caches.match('/offline.html');
      if (offlinePage) {
        return offlinePage;
      }
    }
    
    return new Response(
      JSON.stringify({ error: 'Offline', message: 'Network unavailable' }),
      { 
        status: 503, 
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Network-only strategy
 */
async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch (error) {
    return new Response(
      JSON.stringify({ error: 'Network error', message: 'Please check your connection' }),
      { 
        status: 503, 
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Fetch event - handle all network requests
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  
  // Skip WebSocket requests
  if (request.url.includes('/ws/')) {
    return;
  }
  
  // Skip non-GET requests (POST, PUT, DELETE should always go to network)
  if (request.method !== 'GET') {
    event.respondWith(networkOnly(request));
    return;
  }
  
  const strategy = getCacheStrategy(request.url);
  
  switch (strategy) {
    case 'cache-first':
      event.respondWith(cacheFirst(request));
      break;
    case 'network-only':
      event.respondWith(networkOnly(request));
      break;
    case 'network-first':
    default:
      event.respondWith(networkFirst(request));
      break;
  }
});

/**
 * Push notification event handler
 */
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  
  let data = {
    title: 'CEW Training Platform',
    body: 'You have a new notification',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    tag: 'cew-notification',
    data: {}
  };
  
  if (event.data) {
    try {
      const pushData = event.data.json();
      data = { ...data, ...pushData };
    } catch (e) {
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    data: data.data,
    vibrate: [100, 50, 100],
    actions: data.actions || [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' }
    ],
    requireInteraction: data.requireInteraction || false
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

/**
 * Notification click event handler
 */
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'dismiss') {
    return;
  }
  
  // Open or focus the app
  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window if available
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.navigate(urlToOpen);
            return client.focus();
          }
        }
        // Open new window
        if (self.clients.openWindow) {
          return self.clients.openWindow(urlToOpen);
        }
      })
  );
});

/**
 * Sync event handler (for background sync)
 */
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-progress') {
    event.waitUntil(syncProgress());
  }
});

/**
 * Sync progress data when back online
 */
async function syncProgress() {
  // This would sync any locally stored progress data
  // when the connection is restored
  console.log('[SW] Syncing progress data...');
  // Implementation would depend on IndexedDB storage
}

/**
 * Message event handler (for communication with main app)
 */
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((name) => caches.delete(name))
        );
      })
    );
  }
});

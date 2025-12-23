/**
 * Courius - Service Worker
 * Provides offline support and caching
 */

const CACHE_NAME = 'courius-v3.0.0';
const STATIC_ASSETS = [
    '/web/',
    '/web/index.html',
    '/web/css/main.css',
    '/web/css/editor.css',
    '/web/css/toolbar.css',
    '/web/css/dialogs.css',
    '/web/js/constants.js',
    '/web/js/utils.js',
    '/web/js/security.js',
    '/web/js/accessibility.js',
    '/web/js/config.js',
    '/web/js/line.js',
    '/web/js/screenplay.js',
    '/web/js/undo.js',
    '/web/js/autocompletion.js',
    '/web/js/spellcheck.js',
    '/web/js/spellcheck-v2.js',
    '/web/js/fileio.js',
    '/web/js/export.js',
    '/web/js/reports.js',
    '/web/js/dialogs.js',
    '/web/js/editor.js',
    '/web/js/menu.js',
    '/web/js/scene-navigator.js',
    '/web/js/statistics.js',
    '/web/js/revisions.js',
    '/web/js/plugins.js',
    '/web/js/cloud-sync.js',
    '/web/js/pwa.js',
    '/web/js/app.js'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== CACHE_NAME)
                        .map((name) => {
                            console.log('Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache, fall back to network
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip external requests (like spell check API)
    const url = new URL(event.request.url);
    if (url.origin !== location.origin) {
        // For API requests, try network first, then cache
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cached version
                    return cachedResponse;
                }

                // Not in cache, fetch from network
                return fetch(event.request)
                    .then((networkResponse) => {
                        // Cache the new response
                        if (networkResponse.status === 200) {
                            const responseToCache = networkResponse.clone();
                            caches.open(CACHE_NAME)
                                .then((cache) => {
                                    cache.put(event.request, responseToCache);
                                });
                        }
                        return networkResponse;
                    })
                    .catch(() => {
                        // Network failed and not in cache
                        // Return offline page if available
                        if (event.request.destination === 'document') {
                            return caches.match('/web/index.html');
                        }
                        return new Response('Offline', {
                            status: 503,
                            statusText: 'Service Unavailable'
                        });
                    });
            })
    );
});

// Handle skip waiting message
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// Background sync for offline saves
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-screenplay') {
        event.waitUntil(syncScreenplay());
    }
});

async function syncScreenplay() {
    // Get pending saves from IndexedDB
    const db = await openDatabase();
    const pending = await getPendingSaves(db);

    for (const save of pending) {
        try {
            // Sync to cloud
            // This would integrate with the cloud sync module
            console.log('Syncing:', save.filename);

            // Remove from pending after successful sync
            await removePendingSave(db, save.id);
        } catch (error) {
            console.error('Sync failed:', error);
        }
    }
}

function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('courius-offline', 1);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('pending-saves')) {
                db.createObjectStore('pending-saves', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

function getPendingSaves(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pending-saves'], 'readonly');
        const store = transaction.objectStore('pending-saves');
        const request = store.getAll();

        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
    });
}

function removePendingSave(db, id) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pending-saves'], 'readwrite');
        const store = transaction.objectStore('pending-saves');
        const request = store.delete(id);

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

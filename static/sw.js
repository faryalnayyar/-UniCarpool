const CACHE_NAME = 'unicarpool-v1';
const ASSETS = [
    '/',
    '/auth',
    '/dashboard',
    '/static/css/styles.css',
    '/static/js/rides.js',
    '/static/js/auth.js',
    '/static/img/icon.png',
    '/static/img/landing_hero.png'
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
    );
});

self.addEventListener('fetch', (e) => {
    // Simple cache-first strategy for static assets
    if (e.request.url.includes('/static/')) {
        e.respondWith(
            caches.match(e.request).then((r) => r || fetch(e.request))
        );
    }
});

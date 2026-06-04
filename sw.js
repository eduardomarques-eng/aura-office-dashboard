/* Aura Decore HQ — Service Worker v2 */
const CACHE = 'aura-hq-v2';
const OFFLINE_URL = '/mobile';
const PRECACHE = ['/mobile', '/manifest.json', '/pwa-icon-192.png', '/pwa-icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.allSettled(PRECACHE.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// APIs sempre via rede; assets via cache-first
const API_PATHS = ['/chat','/marathon','/activity','/agent','/shopify','/tasks','/status','/ws'];

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;

  const isApi = API_PATHS.some(p => url.pathname.startsWith(p));

  if (isApi) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({error:'offline'}), {headers:{'Content-Type':'application/json'}})
      )
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached => {
      const net = fetch(e.request).then(resp => {
        if (resp.ok) {
          caches.open(CACHE).then(c => c.put(e.request, resp.clone()));
        }
        return resp;
      }).catch(() => cached || caches.match(OFFLINE_URL));
      return cached || net;
    })
  );
});

// Notificações push (futuro — quando Eduardo ativar)
self.addEventListener('push', e => {
  const d = e.data?.json() || {};
  e.waitUntil(
    self.registration.showNotification(d.title || 'Aura Decore HQ', {
      body: d.body || 'Nova atividade dos agentes',
      icon: '/pwa-icon-192.png',
      badge: '/pwa-icon-192.png',
      tag: 'aura-notif',
      renotify: true,
      vibrate: [200, 100, 200],
      data: {url: d.url || '/mobile'},
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({type:'window'}).then(cs => {
      const c = cs.find(c => c.url.includes('/mobile'));
      if (c) return c.focus();
      return clients.openWindow(e.notification.data?.url || '/mobile');
    })
  );
});

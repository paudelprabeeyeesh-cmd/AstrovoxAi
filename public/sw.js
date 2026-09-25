const CACHE_NAME = 'astrovox-v2'
const STATIC_CACHE = 'astrovox-static-v2'
const DYNAMIC_CACHE = 'astrovox-dynamic-v2'
const API_CACHE = 'astrovox-api-v2'

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/favicon.ico'
]

const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.webmanifest'
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch(() => {
        return cache.add('/')
      })
    })
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => ![STATIC_CACHE, DYNAMIC_CACHE, API_CACHE].includes(key))
          .map((key) => caches.delete(key))
      )
    })
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  if (request.method !== 'GET') {
    return
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request, API_CACHE))
    return
  }

  if (request.destination === 'image' || request.destination === 'font' || request.destination === 'script' || request.destination === 'style') {
    event.respondWith(cacheFirstWithNetwork(request, STATIC_CACHE))
    return
  }

  event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE))
})

async function networkFirstWithCache(request, cacheName) {
  const cache = await caches.open(cacheName)
  try {
    const response = await fetch(request.clone())
    if (response && response.status === 200) {
      cache.put(request, response.clone())
    }
    return response
  } catch (error) {
    const cached = await cache.match(request)
    if (cached) {
      return cached
    }
    return new Response(JSON.stringify({ error: 'Offline', detail: 'You are currently offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    })
  }
}

async function cacheFirstWithNetwork(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  if (cached) {
    const fetchPromise = fetch(request.clone()).then((response) => {
      if (response && response.status === 200) {
        cache.put(request, response.clone())
      }
      return response
    }).catch(() => cached)
    return cached
  }
  try {
    const response = await fetch(request.clone())
    if (response && response.status === 200) {
      cache.put(request, response.clone())
    }
    return response
  } catch (error) {
    return new Response('Offline', { status: 503 })
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  const fetchPromise = fetch(request.clone()).then((response) => {
    if (response && response.status === 200) {
      cache.put(request, response.clone())
    }
    return response
  }).catch(() => cached || new Response('Offline', { status: 503 }))

  return cached || fetchPromise
}

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.delete(CACHE_NAME)
    caches.delete(STATIC_CACHE)
    caches.delete(DYNAMIC_CACHE)
    caches.delete(API_CACHE)
  }
})

const TILE_CACHE = 'map-tiles-v1'
const APP_CACHE = 'app-shell-v1'

// Matsuyama area tile bounds
// zoom 12-14, lat 33.7-34.0, lng 132.6-132.9
const MATSUYAMA = {
  minZoom: 12,
  maxZoom: 14,
  minLat: 33.7,
  maxLat: 34.0,
  minLng: 132.6,
  maxLng: 132.9,
}

function latLngToTile(lat, lng, zoom) {
  const n = Math.pow(2, zoom)
  const x = Math.floor(((lng + 180) / 360) * n)
  const latRad = (lat * Math.PI) / 180
  const y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n)
  return { x, y }
}

function generateTileUrls() {
  const urls = []
  for (let z = MATSUYAMA.minZoom; z <= MATSUYAMA.maxZoom; z++) {
    const topLeft = latLngToTile(MATSUYAMA.maxLat, MATSUYAMA.minLng, z)
    const bottomRight = latLngToTile(MATSUYAMA.minLat, MATSUYAMA.maxLng, z)
    for (let x = topLeft.x; x <= bottomRight.x; x++) {
      for (let y = topLeft.y; y <= bottomRight.y; y++) {
        const subdomain = ['a', 'b', 'c'][Math.abs(x + y) % 3]
        urls.push(`https://${subdomain}.tile.openstreetmap.org/${z}/${x}/${y}.png`)
      }
    }
  }
  return urls
}

async function precacheMatsuyamaTiles() {
  const cache = await caches.open(TILE_CACHE)
  const urls = generateTileUrls()
  const batch = 20
  for (let i = 0; i < urls.length; i += batch) {
    const chunk = urls.slice(i, i + batch)
    await Promise.allSettled(
      chunk.map(async (url) => {
        try {
          const cached = await cache.match(url)
          if (!cached) {
            const res = await fetch(url)
            if (res.ok) await cache.put(url, res)
          }
        } catch (_) {}
      })
    )
  }
}

self.addEventListener('install', (event) => {
  self.skipWaiting()
  event.waitUntil(precacheMatsuyamaTiles().catch(() => {}))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      try {
        const keys = await caches.keys()
        await Promise.all(
          keys
            .filter((k) => k !== TILE_CACHE && k !== APP_CACHE)
            .map((k) => caches.delete(k))
        )
      } catch (_) {}
      await clients.claim()
    })()
  )
})

function isTileRequest(request) {
  return request.url.includes('tile.openstreetmap.org')
}

function isNextStatic(request) {
  return new URL(request.url).pathname.startsWith('/_next/static/')
}

function isAppShell(request) {
  const url = new URL(request.url)
  return (
    request.mode === 'navigate' ||
    url.pathname === '/manifest.json' ||
    url.pathname.startsWith('/icons/')
  )
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  if (cached) return cached
  try {
    const res = await fetch(request)
    if (res.ok) cache.put(request, res.clone())
    return res
  } catch (_) {
    return new Response('', { status: 503 })
  }
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName)
  try {
    const res = await fetch(request)
    if (res.ok) cache.put(request, res.clone())
    return res
  } catch (_) {
    const cached = await cache.match(request)
    return cached || new Response('', { status: 503 })
  }
}

self.addEventListener('fetch', (event) => {
  if (isTileRequest(event.request)) {
    event.respondWith(cacheFirst(event.request, TILE_CACHE))
  } else if (isNextStatic(event.request)) {
    event.respondWith(cacheFirst(event.request, APP_CACHE))
  } else if (isAppShell(event.request)) {
    event.respondWith(networkFirst(event.request, APP_CACHE))
  }
})

// Cambiar la versión si cambia la estrategia de caché o los estáticos sin hash.
const prefijoCache = "condohub-pwa:";
const cacheActual = prefijoCache + "v1:" + archivosPublicos.join("|");
const urlsPublicas = new Set(archivosPublicos.map(ruta => new URL(ruta, self.location.origin).href));

self.addEventListener("install", evento => {
  evento.waitUntil((async () => {
    const cache = await caches.open(cacheActual);
    await cache.addAll(archivosPublicos.map(ruta =>
      new Request(new URL(ruta, self.location.origin), {cache: "reload", credentials: "omit", redirect: "error"})
    ));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", evento => {
  evento.waitUntil((async () => {
    const antiguas = (await caches.keys()).filter(nombre => nombre.startsWith(prefijoCache) && nombre !== cacheActual);
    await Promise.all(antiguas.map(nombre => caches.delete(nombre)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", evento => {
  const peticion = evento.request;
  const url = new URL(peticion.url);
  if (peticion.method !== "GET" || url.origin !== self.location.origin) return;

  if (peticion.mode === "navigate") {
    evento.respondWith(fetch(peticion).catch(async () =>
      (await caches.match(paginaSinConexion, {cacheName: cacheActual})) || Response.error()
    ));
    return;
  }

  // La hoja de estilo del sitio también lleva una versión en la query.
  url.search = "";
  if (urlsPublicas.has(url.href)) {
    evento.respondWith((async () =>
      (await caches.match(url.href, {cacheName: cacheActual})) || fetch(peticion)
    )());
  }
});

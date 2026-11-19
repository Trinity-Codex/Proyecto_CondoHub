// Ejecutar con Playwright y Chromium disponibles, contra una demo local.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");

(async () => {
  const origen = new URL(process.argv[2] || "http://127.0.0.1:8000").origin;
  const navegador = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN || undefined });
  try {
    const contexto = await navegador.newContext();
    // La prueba de la app local es independiente de la disponibilidad de sus CDN.
    await contexto.route(/^https:\/\//, ruta =>
      new URL(ruta.request().url()).origin === origen ? ruta.continue() : ruta.abort()
    );
    const pagina = await contexto.newPage();
    await pagina.goto(origen + "/", {waitUntil: "domcontentloaded"});
    await pagina.waitForFunction(() => navigator.serviceWorker.controller !== null);
    const sesion = await contexto.newCDPSession(pagina);
    const { installabilityErrors } = await sesion.send("Page.getInstallabilityErrors");
    assert.deepEqual(installabilityErrors, [], "Chromium detectó errores de instalación");
    const destino = origen + "/cuentas/iniciar-sesion/";
    await contexto.setOffline(true);
    await pagina.goto(destino);
    assert.equal(await pagina.locator("h1").innerText(), "Sin conexión");
    const rutasCache = await pagina.evaluate(async () => {
      const nombres = (await caches.keys()).filter(n => n.startsWith("condohub-pwa:"));
      return (await Promise.all(nombres.map(async n => (await (await caches.open(n)).keys()).map(r => r.url)))).flat();
    });
    assert.ok(rutasCache.some(r => r.includes("sin-conexion")));
    assert.ok(rutasCache.every(r => new URL(r).pathname.startsWith("/static/")));
    await contexto.setOffline(false);
    await pagina.getByRole("link", {name: "Volver a intentar"}).click();
    await pagina.locator('input[type=password]').waitFor();
    console.log("Chromium: instalación sin errores, navegación sin conexión y recuperación verificadas.");
  } finally {
    await navegador.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

// Demo de solo lectura (#111). base.html carga este archivo solo con config.settings_render_demo.
// El servidor ya rechaza las escrituras (apps/core/middleware_demo.py); aquí solo se marcan los
// botones que envían formularios POST para que se vean y se anuncien como no disponibles.
// Quedan activos los filtros GET, el inicio y cierre de sesión y el cambio de condominio.
(function () {
  "use strict";
  const aviso = document.getElementById("aviso-demo");
  if (!aviso) {
    return;
  }
  const rutaLogin = aviso.dataset.rutaLogin;
  const envios = 'button:not([type="button"]):not([type="reset"]), input[type="submit"]';

  document.querySelectorAll("form").forEach(function (formulario) {
    const esPost = formulario.method === "post";
    const permitido = "demoPermitido" in formulario.dataset
      || new URL(formulario.action).pathname === rutaLogin;
    if (!esPost || permitido) {
      return;
    }
    formulario.querySelectorAll(envios).forEach(function (boton) {
      // aria-disabled (no disabled) mantiene el foco: el lector de pantalla lee el aviso.
      boton.setAttribute("aria-disabled", "true");
      boton.setAttribute("aria-describedby", "aviso-demo");
      boton.title = "No disponible en la demo";
      boton.classList.add("disabled");
    });
    // Enter en un campo también enviaría el formulario: se detiene igual que el clic.
    formulario.addEventListener("submit", function (evento) {
      evento.preventDefault();
    });
  });
})();

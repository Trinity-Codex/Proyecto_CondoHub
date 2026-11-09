/*
 * Búsqueda predictiva (Issue #82): combobox de ARIA 1.2 (patrón «lista con autocompletado») sobre un
 * <input type="search" data-busqueda="<url del JSON>"> dentro de un <form method="get">. Sin npm ni build.
 * Sin JS el campo es un formulario GET normal y filtra igual en el servidor (?q=).
 *  - Pide sugerencias desde 2 caracteres y 250 ms después de la última tecla; cancela la solicitud anterior
 *    (AbortController) y además descarta toda respuesta que no sea la última pedida (número de secuencia).
 *  - Teclado: ↓ abre o baja, ↑ sube (sin dar la vuelta); Enter con opción activa pone su número en `q` y envía
 *    el formulario, sin opción envía lo escrito; Escape cierra la lista y, si ya estaba cerrada, borra el texto.
 *    Tab o salir del campo cierran la lista. El foco nunca sale del campo (aria-activedescendant).
 *  - Anuncia la cantidad de sugerencias en la región [data-busqueda-estado] (aria-live="polite").
 *  - Todo el texto se inserta con textContent y createElement, nunca como HTML. El JS no decide qué mostrar:
 *    pinta lo que trae el JSON y el servidor decide por rol (el comité nunca recibe RUT).
 */
(function (global) {
  "use strict";

  var ESPERA_MS = 250;
  var LARGO_MINIMO = 2;

  /* Mismo recorte que normalizar_busqueda (apps/core/listados.py): sin espacios sobrantes. */
  function normalizar(texto) {
    return String(texto).trim().replace(/\s+/g, " ");
  }

  function anunciarCantidad(datos) {
    var n = datos.resultados.length;
    if (n === 0) return "Sin resultados.";
    if (datos.hay_mas) return n + " sugerencias; hay más, presione Enter para ver todas.";
    return (n === 1 ? "1 sugerencia." : n + " sugerencias.") + " Use las flechas para elegir.";
  }

  /* «Ana Pérez (12.345.678-5), Juan Soto» o «Sin residentes». */
  function textoResidentes(residentes) {
    if (!residentes.length) return "Sin residentes";
    return residentes.map(function (r) {
      return r.rut ? r.nombre + " (" + r.rut + ")" : r.nombre;
    }).join(", ");
  }

  function Busqueda(entrada, indice) {
    this.entrada = entrada;
    this.formulario = entrada.form;
    this.url = entrada.getAttribute("data-busqueda");
    this.estado = this.formulario.querySelector("[data-busqueda-estado]");
    this.opciones = [];
    this.activa = -1;
    this.secuencia = 0;
    this.temporizador = null;
    this.controlador = null;
    this.idLista = (entrada.id || "busqueda-" + indice) + "-lista";
    this.preparar();
  }

  Busqueda.prototype.preparar = function () {
    var entrada = this.entrada;
    var self = this;
    this.lista = document.createElement("ul");
    this.lista.id = this.idLista;
    this.lista.className = "busqueda-lista";
    this.lista.setAttribute("role", "listbox");
    this.lista.setAttribute("aria-label", "Sugerencias");
    this.lista.hidden = true;
    entrada.parentNode.appendChild(this.lista);

    entrada.setAttribute("role", "combobox");
    entrada.setAttribute("aria-autocomplete", "list");
    entrada.setAttribute("aria-expanded", "false");
    entrada.setAttribute("aria-controls", this.idLista);
    entrada.setAttribute("autocomplete", "off");

    entrada.addEventListener("input", function () { self.alEscribir(); });
    entrada.addEventListener("keydown", function (evento) { self.alTeclear(evento); });
    /* Al salir del campo se cierra y se descarta lo pendiente: una respuesta tardía no reabre la lista. */
    entrada.addEventListener("blur", function () {
      global.clearTimeout(self.temporizador);
      self.cancelar();
      self.cerrar();
    });
    /* mousedown + preventDefault: el clic no le quita el foco al campo (así blur no cierra antes del clic). */
    this.lista.addEventListener("mousedown", function (evento) {
      var opcion = evento.target.closest("[role=option]");
      evento.preventDefault();
      if (opcion) self.elegir(Number(opcion.getAttribute("data-indice")));
    });
  };

  Busqueda.prototype.anunciar = function (texto) {
    if (this.estado) this.estado.textContent = texto;
  };

  Busqueda.prototype.alEscribir = function () {
    var self = this;
    var texto = normalizar(this.entrada.value);
    global.clearTimeout(this.temporizador);
    this.cancelar();
    this.marcar(-1);  // la opción activa era de otro texto: Enter debe enviar lo escrito
    if (texto.length < LARGO_MINIMO) {
      this.cerrar();
      this.vaciar();
      this.anunciar("");
      return;
    }
    this.temporizador = global.setTimeout(function () { self.pedir(texto); }, ESPERA_MS);
  };

  Busqueda.prototype.cancelar = function () {
    this.secuencia += 1;  // toda respuesta en camino queda vieja
    if (this.controlador) this.controlador.abort();
    this.controlador = null;
  };

  Busqueda.prototype.pedir = function (texto) {
    var self = this;
    var numero;
    this.cancelar();
    numero = this.secuencia;
    this.controlador = typeof global.AbortController === "function" ? new global.AbortController() : null;
    global.fetch(this.url + (this.url.indexOf("?") === -1 ? "?" : "&") + "q=" + encodeURIComponent(texto), {
      credentials: "same-origin",
      headers: { "Accept": "application/json" },
      signal: this.controlador ? this.controlador.signal : undefined
    }).then(function (respuesta) {
      /* Sin sesión el servidor redirige al inicio de sesión (HTML): se trata como error. */
      var tipo = respuesta.headers.get("Content-Type") || "";
      if (!respuesta.ok || tipo.indexOf("application/json") === -1) throw new Error("respuesta inválida");
      return respuesta.json();
    }).then(function (datos) {
      if (numero !== self.secuencia) return;  // llegó tarde: ya se pidió otra cosa
      self.pintar(datos);
    }).catch(function (error) {
      if (numero !== self.secuencia || (error && error.name === "AbortError")) return;
      self.vaciar();
      self.cerrar();
      self.anunciar("No se pudieron cargar las sugerencias.");
    });
  };

  Busqueda.prototype.vaciar = function () {
    while (this.lista.firstChild) this.lista.removeChild(this.lista.firstChild);
    this.opciones = [];
    this.activa = -1;
    this.entrada.removeAttribute("aria-activedescendant");
  };

  Busqueda.prototype.crearOpcion = function (resultado, i) {
    var opcion = document.createElement("li");
    var titulo = document.createElement("span");
    var detalle = document.createElement("span");
    opcion.id = this.idLista + "-opcion-" + i;
    opcion.className = "busqueda-opcion";
    opcion.setAttribute("role", "option");
    opcion.setAttribute("aria-selected", "false");
    opcion.setAttribute("data-indice", String(i));
    titulo.className = "busqueda-opcion-titulo";
    titulo.textContent = resultado.edificio + " · Unidad " + resultado.unidad;
    detalle.className = "busqueda-opcion-detalle";
    detalle.textContent = textoResidentes(resultado.residentes);
    opcion.appendChild(titulo);
    opcion.appendChild(detalle);
    return opcion;
  };

  Busqueda.prototype.pintar = function (datos) {
    var self = this;
    this.vaciar();
    this.opciones = datos.resultados;
    datos.resultados.forEach(function (resultado, i) {
      self.lista.appendChild(self.crearOpcion(resultado, i));
    });
    if (this.opciones.length) {
      this.abrir();
    } else {
      this.cerrar();
    }
    this.anunciar(anunciarCantidad(datos));
  };

  Busqueda.prototype.abierta = function () {
    return !this.lista.hidden;
  };

  Busqueda.prototype.abrir = function () {
    if (!this.opciones.length) return;
    this.lista.hidden = false;
    this.entrada.setAttribute("aria-expanded", "true");
  };

  Busqueda.prototype.cerrar = function () {
    this.lista.hidden = true;
    this.entrada.setAttribute("aria-expanded", "false");
    this.marcar(-1);
  };

  Busqueda.prototype.marcar = function (indice) {
    var anterior = this.lista.children[this.activa];
    var actual = this.lista.children[indice];
    if (anterior) anterior.setAttribute("aria-selected", "false");
    this.activa = actual ? indice : -1;
    if (actual) {
      actual.setAttribute("aria-selected", "true");
      this.entrada.setAttribute("aria-activedescendant", actual.id);
      if (actual.scrollIntoView) actual.scrollIntoView({ block: "nearest" });
    } else {
      this.entrada.removeAttribute("aria-activedescendant");
    }
  };

  /* Pone el número de la unidad en `q` y envía el formulario (conserva los campos ocultos, como `ocupacion`). */
  Busqueda.prototype.elegir = function (indice) {
    var resultado = this.opciones[indice];
    if (!resultado) return;
    this.entrada.value = resultado.unidad;
    this.cerrar();
    if (typeof this.formulario.requestSubmit === "function") {
      this.formulario.requestSubmit();
    } else {
      this.formulario.submit();
    }
  };

  Busqueda.prototype.bajar = function () {
    if (!this.abierta()) {
      this.abrir();
      if (!this.abierta()) return;
    }
    this.marcar(Math.min(this.activa + 1, this.opciones.length - 1));
  };

  Busqueda.prototype.alEscape = function (evento) {
    evento.preventDefault();  // nunca envía el formulario ni deja que el navegador borre por su cuenta
    if (this.abierta()) {
      this.cerrar();
      return;
    }
    global.clearTimeout(this.temporizador);
    this.cancelar();
    this.entrada.value = "";
    this.vaciar();
    this.anunciar("");
  };

  Busqueda.prototype.alTeclear = function (evento) {
    var tecla = evento.key;
    if (tecla === "ArrowDown" || tecla === "Down") {
      evento.preventDefault();
      this.bajar();
    } else if (tecla === "ArrowUp" || tecla === "Up") {
      if (!this.abierta()) return;
      evento.preventDefault();
      this.marcar(Math.max(this.activa - 1, 0));
    } else if (tecla === "Enter") {
      if (this.abierta() && this.activa >= 0) {
        evento.preventDefault();
        this.elegir(this.activa);
      }
      /* Sin opción activa: envío normal del formulario con lo escrito. */
    } else if (tecla === "Escape" || tecla === "Esc") {
      this.alEscape(evento);
    } else if (tecla === "Tab") {
      this.cerrar();
    }
  };

  var instancias = [];  // una por campo; quedan a mano en CondoHubBusqueda.instancias para depurar

  function iniciar() {
    if (typeof global.fetch !== "function") return;  // navegador muy antiguo: queda el formulario normal
    var campos = document.querySelectorAll("input[data-busqueda]");
    Array.prototype.forEach.call(campos, function (entrada, i) {
      if (entrada.form) instancias.push(new Busqueda(entrada, i));
    });
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", iniciar);
    } else {
      iniciar();
    }
  }
  global.CondoHubBusqueda = {
    normalizar: normalizar, anunciarCantidad: anunciarCantidad, textoResidentes: textoResidentes, instancias: instancias
  };
})(typeof window !== "undefined" ? window : this);

/*
 * Formato progresivo de campos (Issue #76). Sin npm ni build; sin JS todo funciona igual (el servidor
 * acepta las mismas entradas). Regla de oro: el JS nunca cambia un valor sin avisar.
 *  - Mientras se escribe solo reagrupa los puntos que el propio JS pone. Si la persona escribe un punto
 *    o una coma, o pega algo que no es un monto válido, deja de formatear ese campo (dataset.montoManual)
 *    hasta que quede vacío: «1500.5» se envía tal cual y el servidor muestra el error.
 *  - Al salir del campo (focusout) da formato solo si el texto es un monto válido.
 * #77 agrega su formato al registro FORMATOS (p. ej. rut).
 */
(function (global) {
  "use strict";

  /* Misma gramática que normalizar_monto (apps/core/formato.py). */
  var MONTO_SIN_PUNTOS = /^\d+$/;
  var MONTO_AGRUPADO = /^[1-9]\d{0,2}(\.\d{3})+$/;

  /* Dígitos del monto, o null si el texto no es un monto válido. Acepta «$ 1.250.000», «1250000», « 85.000 ». */
  function normalizarMonto(texto) {
    var limpio = String(texto).trim();
    if (limpio.charAt(0) === "$") limpio = limpio.slice(1).trim();
    if (MONTO_SIN_PUNTOS.test(limpio)) return limpio;
    if (MONTO_AGRUPADO.test(limpio)) return limpio.replace(/\./g, "");
    return null;
  }

  function esMontoValido(texto) {
    return normalizarMonto(texto) !== null;
  }

  /* Con ceros a la izquierda («007500») no se agrupa: «007.500» sería rechazado por el servidor. */
  function agruparMiles(digitos) {
    if (/^0\d/.test(digitos)) return digitos;
    return digitos.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  /* Formato final: «1250000» -> «1.250.000». Devuelve el texto intacto si no es un monto válido. */
  function formatearMonto(texto) {
    var digitos = normalizarMonto(texto);
    return digitos === null ? texto : agruparMiles(digitos);
  }

  /*
   * Formato mientras se escribe: solo regrupa los puntos propios. Si el texto tiene algo más que dígitos,
   * puntos y un «$» inicial, no lo toca. Así borrar un dígito en medio de «1.250.000» da «150.000».
   */
  function reagruparMonto(texto) {
    var limpio = String(texto).trim();
    if (limpio.charAt(0) === "$") limpio = limpio.slice(1).trim();
    if (limpio === "" || !/^[\d.]+$/.test(limpio)) return texto;
    return agruparMiles(limpio.replace(/\./g, ""));
  }

  /*
   * Reformatea el valor de `entrada` y deja el cursor tras el mismo dígito.
   * `formatear(texto)` devuelve el texto nuevo; `esSignificativo(caracter)` dice qué caracteres cuentan.
   */
  function reformatear(entrada, formatear, esSignificativo) {
    var antes = entrada.value;
    var cursor = entrada.selectionStart === null ? antes.length : entrada.selectionStart;
    var significativosAntes = 0;
    for (var i = 0; i < cursor; i++) if (esSignificativo(antes.charAt(i))) significativosAntes++;
    var despues = formatear(antes);
    if (despues === antes) return;
    entrada.value = despues;
    var posicion = 0, contados = 0;
    while (posicion < despues.length && contados < significativosAntes) {
      if (esSignificativo(despues.charAt(posicion))) contados++;
      posicion++;
    }
    if (entrada.setSelectionRange) entrada.setSelectionRange(posicion, posicion);
  }

  function esDigito(caracter) {
    return caracter >= "0" && caracter <= "9";
  }

  /*
   * ¿La persona escribió o pegó algo que el JS no debe tocar? Un punto o una coma tipeados, o un pegado
   * que no es un monto válido según la misma gramática del servidor.
   */
  function montoPideDetenerse(evento, entrada) {
    var tipo = evento.inputType || "";
    if (tipo === "insertFromPaste" || tipo === "insertFromDrop") return !esMontoValido(entrada.value);
    /* insertText, insertCompositionText (teclados móviles), etc.: cualquier inserción tipeada con punto o coma. */
    if (tipo.indexOf("insert") === 0 && evento.data && /[.,]/.test(evento.data)) return true;
    return false;
  }

  /* Registro: clave de data-<clave>, formato en vivo, formato al salir, cursor y cuándo detenerse. */
  var FORMATOS = {
    monto: {
      enVivo: reagruparMonto,
      alSalir: formatearMonto,
      esValido: esMontoValido,
      significativo: esDigito,
      pideDetenerse: montoPideDetenerse
    }
  };

  function alEscribir(evento) {
    var entrada = evento.target;
    if (!entrada || !entrada.getAttribute) return;
    Object.keys(FORMATOS).forEach(function (clave) {
      if (entrada.getAttribute("data-" + clave) === null) return;
      var formato = FORMATOS[clave];
      var marca = clave + "Manual";
      if (entrada.value === "") { delete entrada.dataset[marca]; return; }
      if (entrada.dataset[marca]) return;
      if (formato.pideDetenerse(evento, entrada)) { entrada.dataset[marca] = "1"; return; }
      reformatear(entrada, formato.enVivo, formato.significativo);
    });
  }

  /*
   * Un formulario que vuelve con error trae un valor inválido («1500.5») sin marca: al entrar al campo
   * se marca como manual, para que escribir un dígito más no lo reagrupe («1500.50», no «150.050»).
   */
  function alEntrar(evento) {
    var entrada = evento.target;
    if (!entrada || !entrada.getAttribute || entrada.value === undefined) return;
    Object.keys(FORMATOS).forEach(function (clave) {
      if (entrada.getAttribute("data-" + clave) === null) return;
      if (entrada.value !== "" && !FORMATOS[clave].esValido(entrada.value)) entrada.dataset[clave + "Manual"] = "1";
    });
  }

  function alSalir(evento) {
    var entrada = evento.target;
    if (!entrada || !entrada.getAttribute) return;
    Object.keys(FORMATOS).forEach(function (clave) {
      if (entrada.getAttribute("data-" + clave) === null) return;
      var nuevo = FORMATOS[clave].alSalir(entrada.value);
      if (nuevo !== entrada.value) entrada.value = nuevo;
    });
  }

  if (typeof document !== "undefined") {
    document.addEventListener("input", alEscribir);
    document.addEventListener("focusin", alEntrar);
    document.addEventListener("focusout", alSalir);
  }
  global.CondoHubFormato = {
    normalizarMonto: normalizarMonto, esMontoValido: esMontoValido, formatearMonto: formatearMonto,
    reagruparMonto: reagruparMonto, reformatear: reformatear, FORMATOS: FORMATOS
  };
})(typeof window !== "undefined" ? window : this);

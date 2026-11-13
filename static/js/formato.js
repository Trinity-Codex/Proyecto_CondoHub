/*
 * Formato progresivo de campos (Issue #76). Sin npm ni build; sin JS todo funciona igual (el servidor
 * acepta las mismas entradas). Regla de oro: el JS nunca cambia un valor sin avisar.
 *  - Mientras se escribe solo reagrupa los puntos que el propio JS pone. Si la persona escribe un punto
 *    o una coma, o pega algo que no es un monto válido, deja de formatear ese campo (dataset.montoManual)
 *    hasta que quede vacío: «1500.5» se envía tal cual y el servidor muestra el error.
 *  - Al salir del campo (focusout) da formato solo si el texto es un monto válido.
 * RUT (Issue #77): puntos y guion en vivo, «RUT válido.» en la región aria-live [data-rut-aviso] y el error
 * del dígito verificador solo al salir del campo. Si la persona escribe una letra (distinta de K al final),
 * una coma o más de 9 caracteres, el JS deja de tocar el campo (dataset.rutManual) y el servidor muestra el error.
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

  /* ---- RUT (misma gramática que RUT_FORMATO y calcular_dv de apps/core/formato.py) ---- */
  var RUT_NORMALIZADO = /^(\d{7,8})-([\dK])$/;
  var MENSAJE_RUT_FORMATO = "Formato de RUT inválido. Ejemplo: 12.345.678-5";
  var MENSAJE_RUT_DV = "El dígito verificador del RUT no es correcto.";

  /* Quita puntos y espacios y deja la K en mayúscula: « 12.345.678-k » -> «12345678-K». */
  function normalizarRut(texto) {
    return String(texto).replace(/[.\s]/g, "").toUpperCase();
  }

  function calcularDv(numero) {
    var suma = 0, multiplicador = 2;
    for (var i = numero.length - 1; i >= 0; i--) {
      suma += parseInt(numero.charAt(i), 10) * multiplicador;
      multiplicador = multiplicador === 7 ? 2 : multiplicador + 1;
    }
    var resto = 11 - (suma % 11);
    return resto === 11 ? "0" : resto === 10 ? "K" : String(resto);
  }

  /* ¿Es un RUT completo con dígito verificador correcto? Con o sin puntos; el guion es obligatorio. */
  function rutValido(texto) {
    var m = RUT_NORMALIZADO.exec(normalizarRut(texto));
    return m !== null && calcularDv(m[1]) === m[2];
  }

  function agruparCuerpoRut(cuerpo) {
    return cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  /* Formato final: «12345678-5» -> «12.345.678-5». Un texto que no tiene forma de RUT queda intacto. */
  function formatearRut(texto) {
    var m = RUT_NORMALIZADO.exec(normalizarRut(texto));
    return m === null ? texto : agruparCuerpoRut(m[1]) + "-" + m[2];
  }

  /* ¿Solo trae lo que el JS sabe formatear? Dígitos, K, puntos, espacios, a lo más un guion y 9 caracteres. */
  function rutFormateable(texto) {
    var t = String(texto);
    if (!/^[\d.\-\sKk]*$/.test(t)) return false;
    if ((t.match(/-/g) || []).length > 1) return false;
    var cs = t.replace(/[.\-\s]/g, "");
    return cs.length <= 9 && !/[Kk]./.test(cs);
  }

  /* En vivo: el último carácter significativo es el dígito verificador. «123456785» -> «12.345.678-5». */
  function reagruparRut(texto) {
    if (!rutFormateable(texto)) return texto;
    var cs = String(texto).replace(/[.\-\s]/g, "").toUpperCase();
    if (cs.length < 2) return cs;
    return agruparCuerpoRut(cs.slice(0, -1)) + "-" + cs.slice(-1);
  }

  function esSignificativoRut(caracter) {
    return esDigito(caracter) || caracter === "K" || caracter === "k";
  }

  /* Letra que no es K, coma, K antes del final, más de 9 caracteres o un pegado que no es un RUT: dejar de tocar. */
  function rutPideDetenerse(evento, entrada) {
    var tipo = evento.inputType || "";
    if (tipo.indexOf("insert") !== 0) return false;
    return !rutFormateable(entrada.value);
  }

  function escribirAviso(entrada, texto, clase) {
    var id = entrada.id ? entrada.id + "_aviso" : "";
    var aviso = id && document.getElementById(id);
    if (!aviso) return; /* sin región no se avisa: el servidor muestra el error igual */
    aviso.textContent = texto;
    aviso.classList.remove("text-success", "text-danger");
    if (clase) aviso.classList.add(clase);
  }

  /* Quita solo lo que puso este JS (no los errores del servidor). */
  function limpiarErrorRut(entrada) {
    if (!entrada.dataset.rutError) return;
    delete entrada.dataset.rutError;
    entrada.classList.remove("is-invalid");
    entrada.removeAttribute("aria-invalid");
  }

  /* `alSalir` es true en focusout: solo entonces aparece un error. Mientras se escribe, solo «RUT válido.». */
  function avisarRut(entrada, alSalir) {
    var valor = entrada.value;
    if (!alSalir) {
      limpiarErrorRut(entrada);
      if (rutValido(valor)) escribirAviso(entrada, "RUT válido.", "text-success");
      else escribirAviso(entrada, "", null);
      return;
    }
    if (valor.trim() === "") { limpiarErrorRut(entrada); escribirAviso(entrada, "", null); return; }
    if (rutValido(valor)) { limpiarErrorRut(entrada); escribirAviso(entrada, "RUT válido.", "text-success"); return; }
    var m = RUT_NORMALIZADO.exec(normalizarRut(valor));
    escribirAviso(entrada, m ? MENSAJE_RUT_DV : MENSAJE_RUT_FORMATO, "text-danger");
    entrada.dataset.rutError = "1";
    entrada.classList.add("is-invalid");
    entrada.setAttribute("aria-invalid", "true");
  }

  /* Registro: clave de data-<clave>, formato en vivo, formato al salir, cursor y cuándo detenerse. */
  var FORMATOS = {
    monto: {
      enVivo: reagruparMonto,
      alSalir: formatearMonto,
      esValido: esMontoValido,
      significativo: esDigito,
      pideDetenerse: montoPideDetenerse
    },
    rut: {
      enVivo: reagruparRut,
      alSalir: formatearRut,
      esValido: rutFormateable, /* solo se usa en alEntrar: marca manual lo que el JS no sabe formatear */
      significativo: esSignificativoRut,
      pideDetenerse: rutPideDetenerse,
      avisar: avisarRut
    }
  };

  function alEscribir(evento) {
    var entrada = evento.target;
    if (!entrada || !entrada.getAttribute) return;
    Object.keys(FORMATOS).forEach(function (clave) {
      if (entrada.getAttribute("data-" + clave) === null) return;
      var formato = FORMATOS[clave];
      var marca = clave + "Manual";
      if (entrada.value === "") delete entrada.dataset[marca];
      else if (!entrada.dataset[marca]) {
        if (formato.pideDetenerse(evento, entrada)) entrada.dataset[marca] = "1";
        else reformatear(entrada, formato.enVivo, formato.significativo);
      }
      if (formato.avisar) formato.avisar(entrada, false);
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
      if (FORMATOS[clave].avisar) FORMATOS[clave].avisar(entrada, true);
    });
  }

  if (typeof document !== "undefined") {
    document.addEventListener("input", alEscribir);
    document.addEventListener("focusin", alEntrar);
    document.addEventListener("focusout", alSalir);
  }
  global.CondoHubFormato = {
    normalizarMonto: normalizarMonto, esMontoValido: esMontoValido, formatearMonto: formatearMonto,
    reagruparMonto: reagruparMonto, reformatear: reformatear, FORMATOS: FORMATOS,
    normalizarRut: normalizarRut, formatearRut: formatearRut, rutValido: rutValido, calcularDv: calcularDv,
    reagruparRut: reagruparRut
  };
})(typeof window !== "undefined" ? window : this);

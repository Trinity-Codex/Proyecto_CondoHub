# Tasks

## 1. Colores por estado

- [ ] 1.1 Agregar a `static/css/condohub.css` las variables `--estado-*`, `--estado-*-fondo` y `--estado-*-texto` de los seis estados y comentar su contraste. Verificación: script que calcula los pares y confirma ≥3:1 el acento y ≥4,5:1 el texto.
- [ ] 1.2 Crear `.kpi` y `.kpi-<estado>` con `--kpi-acento` (borde superior y punto) y foco con `:focus-visible`, y reemplazar el `nth-child` de `.tarjeta-indicador` por una clase explícita. Verificación: inspección del CSS calculado en el panel.

## 2. Vista

- [ ] 2.1 En `InicioView` armar `tarjetas` (clave, nombre, cantidad, frase, url) por rol: unidades desde `cobranza` sin recalcular, incidentes con una consulta agregada y reservas próximas con un conteo. Verificación: prueba de cantidades con datos de prueba y `assertNumQueries` que muestra que las unidades no suman consultas.
- [ ] 2.2 Dejar en `resumen` solo unidades y residentes, y quitar de la tarjeta de cobranza la cifra de morosas. Verificación: el panel conserva toda la información previa.
- [ ] 2.3 Pruebas de aislamiento (otro condominio no suma) y de acceso (conserje sin unidades ni dinero, residente sin tarjetas) en `apps/core/tests.py`. Verificación: `python manage.py test apps.core`.

## 3. Plantilla

- [ ] 3.1 En `core/inicio.html` recorrer `tarjetas` con `<a class="kpi kpi-{{ t.clave }}">` en la grilla `row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xxl-6`. Verificación: prueba de que el HTML tiene un enlace por tarjeta con nombre y cantidad.
- [ ] 3.2 Medir rectángulos del DOM a 375 px y a 1440 px (solapes, texto cortado, desborde horizontal). Verificación: sin hallazgos; la captura solo confirma.

## 4. Verificación final del PR

- [ ] 4.1 Verificar los datos demo y que el panel se vea con las seis tarjetas. Verificación: `python manage.py cargar_demo` sin errores.
- [ ] 4.2 Escribir en el Issue #80 el contrato `?situacion=` y los enlaces de unidades. Verificación: comentario publicado.
- [ ] 4.3 Ejecutar `python manage.py test apps`, `makemigrations --check` y `openspec validate --all --strict`. Verificación: todo pasa.

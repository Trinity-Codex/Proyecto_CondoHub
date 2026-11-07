# Tasks

## 1. Librería de PDF

- [x] 1.1 Agregar a `requirements.txt` `xhtml2pdf==0.2.28` y sus dependencias exactas (reportlab 5.1.0,
  arabic-reshaper 3.1.0, html5lib 1.1, pillow 13.0.0, pypdf 7.0.0, six 1.17.0, svglib 2.4.0, cssselect2 0.10.1,
  lxml 6.1.3, tinycss2 1.5.1, webencodings 0.6.1, charset-normalizer 3.5.2) con un comentario; verificar que
  `pip install -r requirements.txt` termina en el `venv` de Windows y que `pip check` no reporta conflictos.

## 2. Contrato C0: `renderizar_pdf`

- [x] 2.1 Crear `apps/core/pdf.py` con `renderizar_pdf(plantilla, contexto, nombre)`, `generar_pdf` y `ErrorPDF`
  según `design.md` (decisión 2); verificar con las pruebas de 2.3.
- [x] 2.2 Crear la plantilla base `core/pdf/base.html` y la de prueba `core/pdf/prueba.html` (con "Ñuñoa" y
  "$1.234.567").
- [x] 2.3 Pruebas en `apps/core/tests.py`: la respuesta empieza con `%PDF-`, tiene `Content-Type` y
  `Content-Disposition` correctos, `pypdf` lee "Ñuñoa", un nombre con `/` o sin `.pdf` se corrige y una URL
  externa no se descarga; verificar con `python manage.py test apps.core` en Windows y en la CI.

## 3. Vencimiento y referencia del reglamento

- [x] 3.1 Agregar `fecha_vencimiento`, `referencia_reglamento`, `DIA_VENCIMIENTO`, `vencimiento_por_defecto()` y
  `clean()` a `PeriodoGasto`, y crear la migración `gastos/0006` (agregar nulo, completar, dejar obligatorio);
  verificar con `python manage.py makemigrations --check` y `migrate` sobre la base con la demo cargada.
- [x] 3.2 Sumar los dos campos a `PeriodoForm` (valor inicial del vencimiento y validación de la fecha) y
  mostrarlos en `periodo_formulario.html` y `periodo_detalle.html`.
- [x] 3.3 Pruebas en `apps/gastos/tests.py`, una por escenario del delta de `gastos-comunes`: vencimiento por
  defecto (noviembre → 10 de diciembre; diciembre → 10 de enero del año siguiente), fecha rechazada, partes iguales
  sin y con referencia, migración de períodos existentes, comité (ve y recibe 403 al editar), residente y conserje
  (403) y período de otro condominio (404); verificar con `python manage.py test apps.gastos`.

## 4. Demo por app

- [x] 4.1 Antes de mover código, escribir en `apps/core/tests.py` la prueba de huella (conteos de usuarios,
  condominios, unidades, membresías, residentes, espacios, reservas, comunicados, notificaciones, incidentes,
  proveedores, períodos por estado, egresos, cobros por estado y pagos, más las sumas de montos) para
  `cargar_demo` y `cargar_demo --reiniciar`; verificar que pasa con el código de hoy.
- [x] 4.2 Crear `demo.py` con `cargar(datos)` en cuentas, condominios, reservas, comunicados, incidentes,
  proveedores, gastos, pagos y notificaciones, mover ahí el código y dejar `cargar_demo` como orquestador;
  verificar que la prueba de 4.1 sigue pasando sin cambiar sus números.
- [x] 4.3 Agregar `python manage.py cargar_demo --reiniciar` después de `cargar_demo` en `.github/workflows/ci.yml`
  y verificarlo en la CI del PR.

## 5. Apps nuevas

- [x] 5.1 Crear `apps/auditoria`, `apps/privacidad`, `apps/cartera` y `apps/rendicion` (sin modelos) con su
  `demo.py` vacío, registrarlas en `settings.py` y `config/urls.py` y verificar con `python manage.py check`.
- [x] 5.2 Enlaces en `templates/base.html`: auditoría, cartera y rendición en el menú "Administración" según el rol,
  y "Aviso de privacidad" en el pie, visible también sin sesión.
- [x] 5.3 Pruebas en el `tests.py` de cada app nueva: rol permitido (200), rol no permitido (403), sin sesión
  (redirige al login) y aviso de privacidad sin sesión (200); y en `apps/core/tests.py`, que la página de inicio
  de sesión muestra el enlace "Aviso de privacidad"; verificar con `python manage.py test apps`.

## 6. Documentación y verificación final

- [x] 6.1 Actualizar `docs/GUIA_NUEVA_FEATURE.md` (cómo usar `renderizar_pdf`, CSS que admite xhtml2pdf y cómo
  agregar datos en `demo.py`) y la fila C0 de `docs/equipo/PLAN_PMV_27NOV.md` con lo entregado.
- [x] 6.2 Correr `python manage.py makemigrations --check`, `python manage.py test apps` (243 pruebas de antes más
  las nuevas, todas en verde) y `openspec validate --all --strict`.

## Workflow follow-up

- Cuando el contrato C1 (#27) esté en `main`, registrar con `apps.auditoria.servicios.registrar` la creación y la
  edición de un período (toca dinero): PR aparte que referencia #62.
- Pedir revisión a Maximiliano y Winderson (sus `demo.py` y apps) y archivar con `/opsx:archive` antes de unir.

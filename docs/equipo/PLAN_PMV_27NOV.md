# Plan de trabajo en paralelo — PMV del 27 de noviembre

**Equipo Trinity Codex:** Walther Mora · Maximiliano Soto · Winderson Castrillo
**Hito:** [PMV 27-nov](https://github.com/Trinity-Codex/Proyecto_CondoHub/milestone/2) (Must y Should de MoSCoW).
**Congelamiento:** martes 24 de noviembre, 23:59. **Entrega:** viernes 27, con CondoHub publicado en internet.

El objetivo de este plan es que cada uno trabaje en **su** rama, en **sus** carpetas, y pueda unir sus PR a
`main` sin esperar a los demás.

Planes personales, con las instrucciones para el agente de IA y el modelo y esfuerzo de cada tarea:
[Maximiliano](PMV_Maximiliano_Soto.md) · [Winderson](PMV_Winderson_Castrillo.md).

## 1. Cambio en el proceso (decisión del 6 de noviembre de 2026)

| Antes | Desde el 6 de noviembre |
|---|---|
| PR con 1 aprobación de otro integrante y CI en verde | PR con CI en verde. La revisión de un compañero es **recomendada**, no obligatoria |

**Por qué:** el equipo ya demostró en la entrega del 10 de octubre que trabaja bien en un repositorio compartido,
y con tres semanas para el PMV la espera de aprobaciones se vuelve el cuello de botella. Es una adaptación del
proceso (Scrum con prácticas DevSecOps) decidida por el equipo, y así se explica en la defensa.

**Lo que se mantiene como control:**

- Nadie sube directo a `main`: todo entra por Pull Request con *Squash and merge*.
- La CI debe estar en verde: revisa el proyecto y las migraciones, carga los datos demo, ejecuta las pruebas y
  valida las specs de OpenSpec.
- Cada cambio de comportamiento tiene su propuesta de OpenSpec, visible en el PR.
- **Revisión recomendada** (pide una mirada en el grupo antes de unir) cuando el PR toca un contrato
  (sección 4), un archivo compartido (sección 5) o una carpeta de otro integrante.

## 2. Dueños de las carpetas

Cada carpeta tiene **un dueño durante el PMV**. Solo el dueño la modifica y crea sus migraciones. Leer o importar
modelos y funciones de otra app está permitido: lo que genera conflictos es **editar** los mismos archivos.

| Dueño | Carpetas propias | Apps nuevas que crea |
|---|---|---|
| **Walther** | `apps/gastos` (incluye `reportes.py`), `apps/core` (salvo el panel de inicio), `config/`, `templates/base.html`, `static/` (salvo el service worker), `requirements.txt`, `.github/workflows/`, `docs/` | `apps/cartera` |
| **Winderson** | `apps/pagos`, `apps/proveedores`, `apps/incidentes`, service worker en `static/` | `apps/auditoria`, `apps/rendicion` |
| **Maximiliano** | `apps/cuentas`, `apps/condominios`, `apps/comunicados`, `apps/notificaciones`, `apps/reservas`, panel de inicio (`apps/core/views.py` `InicioView` y `core/inicio.html`) | `apps/privacidad` |

## 3. Reparto de los Issues

| Responsable | Issue | MoSCoW | Carpetas que toca | Necesita de otro | Unir a más tardar |
|---|---|---|---|---|---|
| Walther | **#62 Andamiaje del PMV** | Must | `core`, `gastos`, `config`, `base.html`, `requirements.txt` | — | **Lun 9** |
| Walther | #29 Despliegue | Must | `config`, `requirements.txt`, `docs` | — | Mié 11 (URL pública) |
| Walther | #54 Vista de cartera | Must | `apps/cartera` | — | Dom 15 |
| Walther | #50 Respaldo | Must | scripts y `docs` | #29 | Jue 19 |
| Walther | #8 Fondo de reserva (contrato C5) | Should | `apps/gastos` | C1 (evento de emisión) | **Mié 18** |
| Winderson | #27 Auditoría: núcleo (contrato C1) | Must | `apps/auditoria` | #62 | **Mar 10** |
| Winderson | #53 Anular pagos (contrato C4) | Must | `apps/pagos` y una línea de `gastos/reportes.py` | C1 | **Jue 12** |
| Winderson | #27 Auditoría: vista y eventos de pagos e incidentes | Must | `apps/auditoria`, `apps/pagos`, `apps/incidentes` | C1 | Dom 15 |
| Winderson | #6 Aviso de cobro en PDF | Must | `apps/pagos` | #62 (PDF y vencimiento), C2 | Mié 18 |
| Winderson | #56 Comprobante de pago | Should | `apps/pagos` | #62 (PDF), C2, C4 | Vie 20 |
| Winderson | #55 Rendición mensual | Should | `apps/rendicion`, plantilla del aviso (#6) | C4, C5 | Lun 23 |
| Winderson | #26 PWA sin conexión | Should | `static/` (service worker), una línea de `base.html` | — | Mar 24 |
| Maximiliano | #52 Límite de intentos | Must | `apps/cuentas` | — | Mar 10 |
| Maximiliano | #46 Fechas de residencia (contrato C2) | Must | `apps/condominios` y una línea de `pagos/consultas.py` | — | **Mié 11** |
| Maximiliano | Eventos de auditoría de cuentas y condominios (PR que referencia #27) | Must | `apps/cuentas`, `apps/condominios` | C1 | Vie 13 |
| Maximiliano | #51 Aviso de privacidad | Must | `apps/privacidad`, `apps/cuentas` | #62 (app y enlace del pie) | Dom 15 |
| Maximiliano | #13 Importar unidades | Should | `apps/condominios` | C2 | Jue 19 |
| Maximiliano | #57 Recordatorios e indicadores | Should | `apps/notificaciones`, panel de inicio | #62 (vencimiento) | Sáb 21 |
| Maximiliano | #58 Comunicados: vigencia y lectura | Should | `apps/comunicados` | — | Mar 24 |
| Los tres | #59 Prueba guiada | Should | — | Todo lo anterior | Mié 25 – jue 26 |

Carga estimada: Walther ~40 h, Winderson ~36 h, Maximiliano ~40 h (unas 15 h por semana cada uno).

## 4. Contratos: lo único en que dependemos de otro

Un **contrato** es una pieza pequeña que otro integrante usa. Se une primero, en un PR corto, y su firma no
cambia sin avisar en el grupo.

| Contrato | Dueño | Qué entrega | Lo usan | Unir a más tardar |
|---|---|---|---|---|
| **C0 · Andamiaje (#62)** | Walther | `apps/core/pdf.py` con `renderizar_pdf(plantilla, contexto, nombre)`; librería de PDF fijada en `requirements.txt`; `PeriodoGasto.fecha_vencimiento` y `PeriodoGasto.referencia_reglamento`; datos demo separados por app (`apps/<app>/demo.py`); apps `auditoria`, `privacidad`, `cartera` y `rendicion` creadas y registradas en `settings.py`, `urls.py` y el menú o pie de `base.html`. **Entregado:** xhtml2pdf 0.2.28, `generar_pdf` (bytes) y `ErrorPDF`, plantilla base `core/pdf/base.html`; vencimiento por defecto el día 10 del mes siguiente (`DIA_VENCIMIENTO`, migración `gastos/0006`); `demo.py` con `cargar(datos)` en cada app; páginas provisionales `auditoria:inicio` (administrador), `cartera:inicio` y `rendicion:inicio` (administrador y comité) y `privacidad:aviso` (pública). Cómo usarlo: `docs/GUIA_NUEVA_FEATURE.md`, pasos 10 y 11 | Todos | **Lun 9** |
| **C1 · Registrar un evento (#27)** | Winderson | `apps.auditoria.servicios.registrar(usuario, condominio, accion, objeto, antes=None, despues=None)` | Todos, en sus propios PR | **Mar 10** |
| **C2 · Filtro de residencia (#46)** | Maximiliano | `Residente.desde` y `Residente.hasta`; `apps.condominios.residencias.cobros_visibles(cobros, usuario)` aplicado en `pagos/consultas.py` | #6, #56, #57 | **Mié 11** |
| **C4 · Pagos vigentes (#53)** | Winderson | `Pago.objects.vigentes()` (excluye anulados), aplicado en `pagos/consultas.py`; en `anotar_pagado` de `gastos/reportes.py` el `Sum` filtra `pagos__anulado=False` | #54, #55, reportes | **Jue 12** |
| **C5 · Saldo del fondo (#8)** | Walther | `apps.gastos.fondo.saldo_fondo(condominio, hasta_periodo=None)` y los movimientos del fondo | #55 (rendición y saldo en el aviso de cobro) | **Mié 18** |

Mientras un contrato no esté en `main`, quien lo necesita avanza con lo que no depende de él (plantillas,
pruebas, vistas) o usa un valor provisional en su rama.

## 5. Reglas para archivos compartidos

| Archivo | Regla |
|---|---|
| `config/settings.py`, `config/urls.py` | Las apps nuevas ya quedan registradas en #62. Otro cambio: pedírselo a Walther o PR pequeño con aviso |
| `templates/base.html` | Los enlaces del menú y del pie de las apps nuevas ya quedan en #62. #26 agrega una línea (registro del service worker) |
| `requirements.txt` | Versiones exactas con sus dependencias. La librería de PDF entra en #62; WhiteNoise entra en #29 |
| `apps/core/management/commands/cargar_demo.py` | Después de #62, cada uno edita solo el `demo.py` de su app |
| Migraciones | Solo el dueño de la app las crea. Una migración por PR. Nunca se edita una migración ya unida |
| `openspec/specs/` | Cada cambio modifica su spec al archivarse (`/opsx:archive`). Si dos cambios tocan la misma spec, el segundo actualiza su rama antes de archivar |

## 6. Cómo unir sin inconvenientes

**PR pequeños:** un Issue M se entrega en dos o tres PR parciales (`Refs #N`) y el último cierra el Issue
(`Closes #N`). Un PR no debería acumular más de uno o dos días de trabajo.

**Antes de unir cada PR:**

```bash
git fetch origin
```
```bash
git merge origin/main
```
```bash
python manage.py makemigrations --check
```
```bash
python manage.py test apps
```
```bash
openspec validate --all --strict
```

Luego `git push`, esperar la CI en verde, **Squash and merge** y borrar la rama. Al unir, avisar en el grupo:
"Uní #N; toca X". Quien tenga una rama abierta la actualiza con `main` ese mismo día.

**Riesgo que la CI no ve:** si dos PR se prueban por separado y se unen seguidos, `main` puede quedar con dos
migraciones incompatibles o con pruebas que fallan juntas. Por eso cada uno actualiza su rama con `main` justo
antes de unir. Si `main` queda en rojo, arreglarlo es la prioridad de quien unió el último PR.

## 7. Calendario de uniones

| Día | Uniones previstas |
|---|---|
| Lun 9 | #62 Andamiaje (C0) |
| Mar 10 | #27 núcleo (C1), #52 |
| Mié 11 | #29 URL pública, #46 (C2) |
| Jue 12 | #53 (C4) |
| Vie 13 – dom 15 | Eventos de auditoría de cuentas y condominios, #27 vista, #54, #51 |
| Semana 2 (16–22) | #6 y #8 (C5) el miércoles 18, #50, #13, #56, #57 |
| Lun 23 – mar 24 | #55, #26, #58. **Congelamiento martes 24, 23:59** |
| Mié 25 – jue 26 | #59 prueba guiada, correcciones, datos demo, documentación y ensayo |
| Vie 27 | Entrega |

Revisión del avance: **miércoles 18** en la reunión diaria. Si hay atraso, se corta desde el final del Should:
primero #58 y #26.

# CondoHub

[![CI - pruebas con MySQL 8](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Trinity-Codex/Proyecto_CondoHub/actions/workflows/ci.yml)

Plataforma web de **gestión de condominios**: comunicados, reservas de espacios comunes,
incidentes y notificaciones, con soporte para **varios condominios** y **roles**
(administrador, comité, residente y conserje).

Implementa el diseño del *Informe 2 de Ingeniería de Software — Sistema de Administración
Comunitaria (Condominio Vista Verde)*: requerimientos RF01–RF12, modelo de datos y los patrones
**Observer** (notificaciones) y **Strategy** (prorrateo de gastos comunes, en el backlog).

**Equipo Trinity Codex:** Walther Mora · Maximiliano Soto · Winderson Castrillo

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · Django 5.2 LTS |
| Frontend | Plantillas de Django · Bootstrap 5 · Bootstrap Icons (responsive, instalable como PWA) |
| Base de datos | MySQL 8 |
| Pruebas | Django TestCase · GitHub Actions con MySQL 8 |

## Inicio rápido (Windows)

Requisitos: **Python 3.12**, **MySQL 8** y **Git**.

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/Trinity-Codex/Proyecto_CondoHub.git
   ```
2. Crear la base de datos y el usuario de MySQL (**una sola vez**): ejecutar
   [`docs/crear_base_datos.sql`](docs/crear_base_datos.sql) en MySQL Workbench con el usuario `root`.
3. Doble clic en **`iniciar.bat`**: crea el entorno virtual, instala las librerías, crea las
   tablas, carga los datos de demostración y abre http://127.0.0.1:8000/.

### Usuarios de demostración

Todos con la clave **`condohub2026`**:

| Correo | Rol |
|---|---|
| `administrador@condohub.cl` | Administrador de **dos** condominios (prueba el selector del menú) |
| `comite@condohub.cl` | Comité de administración (y residente de A-201) |
| `conserje@condohub.cl` | Conserje |
| `residente@condohub.cl` | Residente propietario de A-101 |
| `residente2@condohub.cl` | Residente arrendatario de B-102 |
| `residente3@condohub.cl` | Residente del otro condominio (Edificio Los Aromos) |
| `superadmin@condohub.cl` | Superusuario de la plataforma (`/admin/`) |

## Funcionalidades de la base

| Módulo | Qué hace | Requerimientos |
|---|---|---|
| Cuentas | Inicio de sesión con correo; usuario con RUT validado | RF12, RNF02 |
| Condominios | Condominios, edificios, unidades con alícuota, residentes y roles por condominio | RF01 |
| Comunicados | Publicar comunicados generales o por edificio | RF09 |
| Reservas | Disponibilidad por fecha y reservas **sin superposición de horarios** | RF05, RF06 |
| Incidentes | Reportar incidentes y cambiar su estado (recibido → en proceso → resuelto) | RF07, RF08 |
| Notificaciones | Campana con avisos de comunicados e incidentes (patrón Observer) | RF10 |

Las funcionalidades pendientes (gastos comunes, pagos, reportes, proveedores, etc.) están en los
[Issues](https://github.com/Trinity-Codex/Proyecto_CondoHub/issues) y en el tablero del proyecto.

## Pruebas

```bash
python manage.py test apps
```

## Cómo colaborar

Ver [CONTRIBUTING.md](CONTRIBUTING.md): ramas, commits, Pull Requests y revisiones.

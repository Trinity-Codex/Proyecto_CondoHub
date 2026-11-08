# Proposal

Closes #51 · MoSCoW: **Must** · Hito PMV 27-nov · RF22, NTI-11 y SEG-08 (Informe 1).

## Why

La Ley 21.719 rige desde el 1 de diciembre de 2026, y CondoHub trata datos personales (nombre, RUT, correo, teléfono, residencia, deudas y pagos) sin decir para qué ni cómo ejercer los derechos. La página actual es provisional (#62).

## What Changes

- **Aviso de privacidad público:** qué datos se tratan y para qué, quién es responsable (la administración de cada condominio) y quién encargado (la plataforma), cuánto se conservan y cómo ejercer los derechos. Indica que la instancia usa datos de demostración. Se enlaza desde el inicio de sesión, además del pie.
- **Solicitudes del titular:** una persona con sesión pide acceso, rectificación, supresión u oposición en su condominio activo y ve solo sus solicitudes. El administrador de ese condominio las ve, responde y cierra; cada una guarda fecha, tipo, estado y respuesta. Se avisa por la campana y el correo: al administrador cuando llega una y a la persona cuando se cierra.
- **Descargar mis datos** en Mi perfil: un archivo JSON con los datos de la persona en todos sus condominios, con los cobros limitados a su período de residencia (#46).
- Datos demo con una solicitud pendiente y otra cerrada.

**Fuera del alcance:**
- Ejecutar automáticamente una supresión u oposición: el administrador la gestiona y deja constancia en la respuesta.
- Validación del texto por un abogado.
- Plazos legales exactos de respuesta.
- El registro en auditoría queda listo para cuando C1 (#27) esté en `main`; si no llega a tiempo, va en el PR de eventos de auditoría (`Refs #27`).

## Capabilities

### New Capabilities

- `privacidad`: aviso de privacidad, solicitudes del titular y descarga de los datos propios.

### Modified Capabilities

Ninguna.

## Impact

- **Mis carpetas:**
  - `apps/privacidad`: modelo, migración, vistas, formularios, plantillas, `demo.py` y pruebas.
  - `apps/cuentas`: enlace en el inicio de sesión, descarga en Mi perfil y acceso a las solicitudes desde Usuarios.
  - `apps/notificaciones`: suscripción de las solicitudes al Observer.
- **Sin cambios** en `config/`, `templates/base.html` ni `requirements.txt`. El administrador entra a las solicitudes desde Usuarios, porque el menú es de Walther.
- **Dependencia:** C1 (#27) para la auditoría.

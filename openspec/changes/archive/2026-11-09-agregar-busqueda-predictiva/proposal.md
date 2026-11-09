Issue: #82 (`Closes #82`). MoSCoW: Could (UI-7 del reporte de mejoras de interfaz). Depende de #80 (unido: `FiltrosGetMixin`, `q` reservado).
Fuera de alcance: búsqueda en incidentes, egresos u otros listados; buscar por correo, teléfono o residentes dados de baja;
limitar la frecuencia de solicitudes; registrar las búsquedas en la auditoría; índices o migraciones; dependencias nuevas.

## Why

Con decenas o cientos de unidades, encontrar «la del 504» o «la de Ana Pérez» en Unidades obliga a recorrer cada edificio con
la vista o con Ctrl+F, que no sirve en el celular ni encuentra un RUT escrito sin puntos. Entrega PMV: 27 de noviembre de 2026.

## What Changes

- **Búsqueda `?q=` en Unidades**: filtra por número de unidad, nombre o apellido del residente activo y, solo para el
  administrador, por el inicio del RUT (con o sin puntos y guion). Sin JavaScript, Enter envía el formulario. Se combina
  con los chips de ocupación de #80, que cuentan dentro del resultado, y «Limpiar filtros» la quita.
- **Endpoint JSON de sugerencias** (GET `/condominio/unidades/sugerencias/?q=`): parte del mismo queryset del listado, a lo
  más 10 unidades, solo los campos que el listado ya muestra a ese rol, lista vacía con menos de 2 caracteres, 403 para
  roles sin acceso y sin caché en el navegador.
- **`static/js/busqueda.js`**: combobox de ARIA 1.2 activado por `data-busqueda`, con espera de 250 ms, flechas, Enter,
  Escape, estado en `aria-live="polite"` y cancelación de solicitudes viejas.
- **Estilos** de la lista de sugerencias en `condohub.css`, con foco visible y sin desborde a 375 px.
- **`FiltrosGetMixin`** puede declarar que acepta búsqueda; entonces `q` cuenta como filtro activo. Los demás listados no cambian.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `condominios`: se agregan «Búsqueda de unidades y residentes» y «Sugerencias de búsqueda de unidades».
- `plataforma`: se agrega «Búsqueda predictiva accesible».

## Impact

- **Código:** `apps/condominios` (vista y plantilla de Unidades, vista de sugerencias, módulo de búsqueda, URL, pruebas;
  carpeta de Maximiliano), `apps/core/listados.py`, `templates/base.html` (carga de `busqueda.js`), `static/js/busqueda.js`
  (nuevo) y `static/css/condohub.css`. Sin migraciones ni dependencias.
- **Otros integrantes:** cambio transversal; se avisa a Maximiliano al unir.
- **Contratos C0 a C6:** no cambia ninguna firma. `RolRequeridoMixin`, `CondominioQuerysetMixin`, `_chips.html` y
  `_paginacion.html` se usan tal como están.
- **Privacidad:** expone nombre y RUT por un endpoint nuevo; el diseño fija que ningún rol recibe más de lo que ve en el listado.

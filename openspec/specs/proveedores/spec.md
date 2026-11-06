# proveedores Specification

## Purpose
Registrar las empresas que prestan servicios al condominio y vincularlas a los egresos (RF17).
Código: `apps/proveedores`.

## Requirements

### Requirement: Ficha de proveedor
El sistema SHALL registrar por condominio cada proveedor con RUT validado, razón social, rubro y datos de contacto, y MUST impedir dos proveedores con el mismo RUT en un condominio.

#### Scenario: RUT repetido
- **WHEN** el administrador registra un proveedor con un RUT que ya existe en el condominio
- **THEN** el formulario lo rechaza

### Requirement: Desactivar en vez de borrar
El sistema SHALL desactivar los proveedores en lugar de borrarlos, para conservar su vínculo con los egresos pasados; los inactivos no se ofrecen en egresos nuevos.

#### Scenario: Proveedor inactivo
- **WHEN** el administrador registra un egreso nuevo
- **THEN** la lista de proveedores muestra solo los activos

### Requirement: Acceso por rol
El sistema SHALL mostrar los proveedores al administrador y al comité, y solo el administrador SHALL crearlos, editarlos o desactivarlos.

#### Scenario: Residente sin acceso
- **WHEN** un residente abre la lista de proveedores
- **THEN** el sistema responde 403

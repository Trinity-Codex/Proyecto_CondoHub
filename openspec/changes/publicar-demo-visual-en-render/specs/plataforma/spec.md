# Spec Delta

## ADDED Requirements

### Requirement: Demo visual aislada para revisión del cliente

La configuración de Render SHALL publicar por HTTPS las pantallas actuales de CondoHub con datos ficticios e indicar «Demo de solo lectura · Datos ficticios». El servidor MUST conservar el aislamiento y los permisos por rol y condominio, y bloquear las escrituras de negocio incluso ante solicitudes directas. Las sesiones y los metadatos de autenticación pueden escribirse. La configuración habitual SHALL conservar su comportamiento.

#### Scenario: Navegación autorizada según el rol
- **WHEN** un administrador o un residente inicia sesión con los datos de la demo y selecciona un condominio del que es miembro
- **THEN** puede navegar, filtrar y consultar las páginas permitidas para su rol, y cerrar sesión
- **AND** recibe 403 o 404 al solicitar una página o datos de un condominio a los que no tenga acceso

#### Scenario: Acción de escritura bloqueada
- **WHEN** un usuario intenta una escritura de negocio mediante POST, PUT, PATCH o DELETE, o un GET que modifica datos como la apertura de una notificación
- **THEN** el servidor rechaza la operación con una explicación de solo lectura y los datos de negocio se conservan

#### Scenario: Reconstrucción con almacenamiento vacío
- **WHEN** se inicia la demo en una instancia sin base local
- **THEN** se prepara la SQLite aislada con los ejemplos ficticios existentes antes de servir la aplicación
- **AND** repetir la preparación sobre esa misma base conserva los ejemplos sin duplicarlos

## ADDED Requirements

### Requirement: Identidad visual del condominio
El sistema SHALL mostrar el nombre del condominio activo en grande, y su logo si existe, en todas las pantallas con condominio activo, y SHALL permitir que solo el administrador edite nombre, dirección, comuna, logo y portada. Las imágenes MUST ser JPG o PNG reales de hasta 2 MB, MUST guardarse vueltas a codificar sin metadatos y con nombre generado, y MUST entregarse solo a miembros de ese condominio.

#### Scenario: Encabezado en cualquier pantalla
- **WHEN** un miembro del condominio abre cualquier pantalla con ese condominio activo, a 375 o 1440 px de ancho
- **THEN** ve el nombre del condominio en grande y, si tiene logo, el logo junto a él

#### Scenario: Condominio sin imágenes
- **WHEN** el condominio activo no tiene logo ni portada
- **THEN** el encabezado muestra solo el nombre

#### Scenario: Portada en el panel
- **WHEN** el condominio tiene portada y el usuario abre el panel de inicio
- **THEN** la portada se ve detrás del nombre con contraste AA, y en las demás pantallas no se muestra

#### Scenario: Solo el administrador edita
- **WHEN** un miembro del comité, un conserje o un residente abre o envía la pantalla «Datos del condominio»
- **THEN** recibe 403 y el condominio no cambia

#### Scenario: Imagen válida
- **WHEN** el administrador sube un logo o una portada JPG o PNG de hasta 2 MB
- **THEN** se guarda una copia vuelta a codificar, sin EXIF, con nombre generado y reducida a su tamaño máximo, y el cambio queda auditado

#### Scenario: Imagen rechazada
- **WHEN** el administrador sube un SVG, un GIF, un archivo que no es imagen aunque tenga extensión JPG o PNG, o una imagen de más de 2 MB
- **THEN** el formulario muestra un mensaje claro y no guarda ningún cambio

#### Scenario: Reemplazar o quitar
- **WHEN** el administrador reemplaza o quita el logo o la portada
- **THEN** el condominio queda con la imagen nueva o sin imagen, y el archivo anterior se borra

#### Scenario: Imagen de otro condominio o sin sesión
- **WHEN** alguien pide la imagen de un condominio del que no es miembro, o la pide sin iniciar sesión
- **THEN** recibe 404, o es llevado al inicio de sesión, sin recibir la imagen; los archivos subidos no se publican en `/media/`

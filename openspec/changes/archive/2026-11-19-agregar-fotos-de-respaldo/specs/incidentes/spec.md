# Spec Delta

## ADDED Requirements

### Requirement: Fotos de respaldo
El sistema SHALL permitir adjuntar fotos de respaldo a un incidente en dos etapas: «antes» (la sube el residente que lo reporta, al crearlo) y «después» (la suben el administrador o el conserje al gestionarlo). Solo se aceptan imágenes JPG o PNG reales, de hasta 5 MB y 10 por incidente. Solo el administrador y el conserje SHALL borrar fotos, y subida y baja MUST quedar en la auditoría. La galería SHALL mostrar fecha y autor de cada foto, y los archivos MUST NOT servirse por una URL pública.

#### Scenario: Fotos «antes» al reportar
- **WHEN** un residente reporta un incidente adjuntando dos fotos JPG o PNG válidas
- **THEN** el incidente queda con dos fotos en etapa «antes», a nombre del residente, y cada subida queda en la auditoría

#### Scenario: Fotos «después» al resolver
- **WHEN** el administrador o el conserje sube una foto desde el detalle del incidente
- **THEN** queda en etapa «después» con su fecha y su autor, y aparece en la galería junto a las de «antes»

#### Scenario: Archivo que no es una imagen
- **WHEN** se sube un archivo de texto renombrado a `.jpg`, o con extensión distinta de JPG y PNG
- **THEN** el sistema lo rechaza con un mensaje que nombra el archivo y no guarda nada

#### Scenario: Foto de más de 5 MB
- **WHEN** se sube una imagen que pesa más de 5 MB
- **THEN** el sistema la rechaza indicando su peso y el máximo permitido

#### Scenario: Foto número 11
- **WHEN** un incidente ya tiene 10 fotos y se intenta subir otra
- **THEN** el sistema la rechaza indicando que el máximo es 10 por incidente

#### Scenario: Subir o borrar sin permiso
- **WHEN** un residente o un miembro del comité intenta subir fotos «después» o borrar una foto
- **THEN** el sistema responde 403 y la foto no cambia

#### Scenario: Borrar una foto
- **WHEN** el administrador o el conserje borra una foto
- **THEN** la foto y su archivo desaparecen y la baja queda en la auditoría

#### Scenario: Archivo por URL directa sin permiso
- **WHEN** un residente que no reportó el incidente, o alguien de otro condominio, pide el archivo de la foto por su URL
- **THEN** el sistema responde 404 y no entrega la imagen

#### Scenario: Incidente resuelto en el historial
- **WHEN** el residente que lo reportó o la administración abre un incidente resuelto
- **THEN** ve sus fotos de «antes» y de «después», cada una con su fecha y su autor

#### Scenario: Subida de fotos apagada
- **WHEN** la subida de fotos está apagada (`FOTOS_INCIDENTES_HABILITADAS` en falso, el valor por defecto) y alguien adjunta una foto
- **THEN** el formulario la rechaza con «La subida de fotos aún no está habilitada en este servidor», el servicio de subida se niega y no se escribe ningún archivo

#### Scenario: Subidas simultáneas
- **WHEN** dos subidas simultáneas intentan pasar de 10 fotos en el mismo incidente
- **THEN** el servicio cuenta el cupo con el incidente bloqueado, por lo que solo cabe una de ellas y el incidente nunca supera las 10 fotos

#### Scenario: Subida que se revierte
- **WHEN** falla la auditoría u otro paso después de haber guardado un archivo
- **THEN** la transacción se revierte y el archivo ya escrito se borra del disco

#### Scenario: Tipo de archivo igual a su contenido
- **WHEN** se sube un PNG llamado `foto.jpg`
- **THEN** se guarda con extensión `.png` y se entrega como `image/png`

## MODIFIED Requirements

### Requirement: Visibilidad de incidentes
El sistema SHALL mostrar al residente solo sus incidentes, y a administrador, comité y conserje todos los del condominio. Las fotos de respaldo de un incidente SHALL seguir exactamente la misma regla, también al pedir el archivo por su URL directa.

#### Scenario: Incidente ajeno
- **WHEN** un residente abre por URL directa el incidente de otra persona
- **THEN** el sistema responde 404

#### Scenario: Fotos de un incidente ajeno
- **WHEN** un residente pide por URL directa la foto de un incidente que reportó otra persona
- **THEN** el sistema responde 404, igual que con el incidente

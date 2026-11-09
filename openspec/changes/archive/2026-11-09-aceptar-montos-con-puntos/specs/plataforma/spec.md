# Spec Delta

## ADDED Requirements

### Requirement: Montos en pesos legibles
Los campos de dinero que escribe el usuario SHALL aceptar pesos enteros con o sin puntos de miles y signo `$`, mostrarlos con prefijo `$` y puntos, y guardar el mismo entero. MUST rechazar con un mensaje en español toda entrada que no sea un entero en pesos y MUST conservar los mínimos y máximos de cada campo. Todo SHALL funcionar sin JavaScript y MUST NOT cambiar los permisos ni el formato `$1.234.567` de los montos mostrados.

#### Scenario: Monto con puntos y signo
- **WHEN** el administrador registra un egreso escribiendo «$ 1.250.000»
- **THEN** el egreso se guarda con monto 1250000

#### Scenario: Monto sin puntos
- **WHEN** el administrador escribe «1250000» o « 85.000 » en un campo de dinero
- **THEN** se guardan 1250000 y 85000 respectivamente

#### Scenario: Monto ambiguo o inválido
- **WHEN** el usuario escribe «1,5», «1.5», «1.25.000», «0.500», «01.000», «-5» o «abc» en un campo de dinero
- **THEN** el formulario vuelve con un error en ese campo que explica que el monto va en pesos enteros, y no se guarda nada

#### Scenario: El JavaScript no cambia un monto sin avisar
- **WHEN** con JavaScript activo el usuario escribe «1500.5» o «1,5», o pega un texto que no es un monto válido, y sale del campo
- **THEN** el campo conserva exactamente lo escrito (sin reagrupar dígitos) y, al enviar, el servidor muestra el error

#### Scenario: Cero como monto
- **WHEN** el usuario escribe «0» en un egreso y en la tarifa de un espacio común
- **THEN** el egreso se rechaza y la tarifa se acepta con 0 (gratis)

#### Scenario: Monto sobre el máximo
- **WHEN** el administrador escribe un egreso de «1.000.000.000» (sobre el máximo de 999.999.999)
- **THEN** el egreso se rechaza como hasta ahora

#### Scenario: Formulario que vuelve con error
- **WHEN** un formulario con «1.250.000» en el monto vuelve por un error en otro campo
- **THEN** el campo de monto sigue mostrando «1.250.000»

#### Scenario: Editar un monto guardado
- **WHEN** el administrador abre la edición de un egreso de 450000 pesos
- **THEN** el campo muestra «450.000» con el prefijo `$`

#### Scenario: Sin JavaScript
- **WHEN** el navegador no ejecuta JavaScript y el administrador envía «1.250.000»
- **THEN** el monto se guarda igual que con JavaScript

#### Scenario: Montos mostrados sin cambios
- **WHEN** una tabla o un PDF muestra un monto de 1234567, uno negativo de -5000 o uno vacío
- **THEN** se ven «$1.234.567», «-$5.000» y «$0», igual que antes del cambio

#### Scenario: Acceso por rol sin cambios
- **WHEN** un residente intenta abrir el formulario de egreso, de registro de pago o de espacio común
- **THEN** recibe "No tienes permisos" (403), y el administrador del condominio ve el formulario con el campo de monto (200)

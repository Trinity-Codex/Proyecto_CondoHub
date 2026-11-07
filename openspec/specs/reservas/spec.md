# reservas Specification

## Purpose
Reservar los espacios comunes sin choques de horario (RF05, RF06, RF14). Código: `apps/reservas`.

## Requirements

### Requirement: Espacios comunes
El sistema SHALL permitir que el administrador cree y edite espacios con nombre, capacidad, horario de apertura y cierre, tarifa informativa y estado activo.

#### Scenario: Espacio inactivo
- **WHEN** un espacio está inactivo
- **THEN** los residentes no pueden reservarlo

### Requirement: Disponibilidad y reserva
El sistema SHALL mostrar la disponibilidad de un espacio por fecha y permitir que el residente reserve para una de sus unidades, dentro del horario del espacio, en una fecha no pasada y con hora de término posterior a la de inicio.

#### Scenario: Fuera de horario
- **WHEN** un residente reserva fuera del horario de apertura del espacio
- **THEN** la reserva se rechaza indicando el horario permitido

### Requirement: Sin superposición de horarios
El sistema MUST rechazar una reserva que se superponga con otra reserva confirmada del mismo espacio y fecha, aunque empiecen a horas distintas, también ante solicitudes simultáneas.

#### Scenario: Superposición parcial
- **WHEN** existe una reserva de 10:00 a 12:00 y otro residente pide de 11:00 a 13:00
- **THEN** la segunda reserva se rechaza

### Requirement: Cancelación de reservas
El sistema SHALL permitir cancelar solo reservas futuras y confirmadas: el residente las suyas y el administrador cualquiera. La cancelación libera el horario.

#### Scenario: Cancelar una reserva propia
- **WHEN** un residente cancela su reserva futura
- **THEN** el horario queda disponible para otros

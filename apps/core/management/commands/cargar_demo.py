"""
Carga datos de demostración para probar CondoHub.

Uso:
    python manage.py cargar_demo              # carga los datos (si no existen)
    python manage.py cargar_demo --reiniciar  # borra los datos demo y los vuelve a crear

Crea:
  - 2 condominios: "Condominio Vista Verde" (el del Informe 2) y "Edificio Los Aromos",
    para mostrar que la plataforma es multi-condominio.
  - 1 usuario por rol (todos con la clave CLAVE_DEMO, ver tabla en README.md).
  - Edificios y unidades con alícuotas que suman 1, espacios comunes,
    comunicados, incidentes, reservas y gastos comunes (mes anterior emitido y mes actual abierto).
"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.comunicados.models import Comunicado
from apps.condominios.models import Condominio, Edificio, Membresia, Residente, Unidad
from apps.cuentas.models import Usuario
from apps.gastos.models import Egreso, PeriodoGasto
from apps.gastos.servicios import emitir_periodo
from apps.incidentes.models import Incidente
from apps.pagos.models import Pago
from apps.proveedores.models import Proveedor
from apps.reservas.models import EspacioComun, Reserva

CLAVE_DEMO = "condohub2026"
NOMBRES_DEMO = ["Condominio Vista Verde", "Edificio Los Aromos"]

# correo, nombre, apellido, RUT válido
USUARIOS = {
    "superadmin": ("superadmin@condohub.cl", "Super", "Administrador", "11.111.111-1"),
    "administrador": ("administrador@condohub.cl", "Ana", "Rojas", "12.345.678-5"),
    "comite": ("comite@condohub.cl", "Carlos", "Pérez", "13.579.246-2"),
    "conserje": ("conserje@condohub.cl", "Jorge", "Muñoz", "14.725.836-4"),
    "residente": ("residente@condohub.cl", "Valentina", "Soto", "15.975.346-8"),
    "residente2": ("residente2@condohub.cl", "Diego", "Castro", "16.482.759-3"),
    "residente3": ("residente3@condohub.cl", "Camila", "Fuentes", "17.258.369-5"),
}


class Command(BaseCommand):
    help = "Carga datos de demostración (condominios, usuarios por rol, espacios, comunicados...)."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true", help="Borra los datos demo y los crea de nuevo.")

    @transaction.atomic  # todo o nada: si algo falla, no queda la base a medias
    def handle(self, *args, **opciones):
        if Condominio.objects.filter(nombre__in=NOMBRES_DEMO).exists():
            if not opciones["reiniciar"]:
                self.stdout.write(self.style.WARNING(
                    "Los datos demo ya existen. Usa --reiniciar para borrarlos y crearlos de nuevo."
                ))
                return
            # Borrar el condominio borra en cascada edificios, unidades, comunicados, etc.
            Condominio.objects.filter(nombre__in=NOMBRES_DEMO).delete()

        u = self._crear_usuarios()
        vista_verde = self._crear_vista_verde(u)
        self._crear_los_aromos(u)
        # Datos de cada módulo nuevo: un método _demo_<modulo>() por app (ver docs/equipo/PLAN_DE_TRABAJO.md).
        proveedores = self._demo_proveedores(vista_verde)
        self._demo_gastos(vista_verde, u, proveedores)
        self._demo_pagos(vista_verde, u)

        self.stdout.write(self.style.SUCCESS("Datos demo cargados."))
        self.stdout.write(f"Clave de todos los usuarios demo: {CLAVE_DEMO}")
        for correo, *_ in USUARIOS.values():
            self.stdout.write(f"  - {correo}")
        self.stdout.write(f"Suma de alícuotas de {vista_verde}: {vista_verde.suma_alicuotas()}")

    # ------------------------------------------------------------------
    def _crear_usuarios(self):
        usuarios = {}
        for clave, (correo, nombre, apellido, rut) in USUARIOS.items():
            usuario, creado = Usuario.objects.get_or_create(
                email=correo, defaults={"first_name": nombre, "last_name": apellido, "rut": rut}
            )
            if creado:
                usuario.set_password(CLAVE_DEMO)
                if clave == "superadmin":
                    usuario.is_staff = usuario.is_superuser = True
                usuario.save()
            usuarios[clave] = usuario
        return usuarios

    def _crear_vista_verde(self, u):
        condominio = Condominio.objects.create(
            nombre="Condominio Vista Verde", direccion="Av. Los Pinos 1234", comuna="Maipú"
        )
        # Alícuotas por torre: 0.12 + 0.08 + 0.12 + 0.08 + 0.10 = 0.50 -> dos torres = 1 (100 %)
        alicuotas = [("101", 1, "0.12"), ("102", 1, "0.08"), ("201", 2, "0.12"), ("202", 2, "0.08"), ("301", 3, "0.10")]
        unidades = {}
        for nombre_torre in ["Torre A", "Torre B"]:
            torre = Edificio.objects.create(condominio=condominio, nombre=nombre_torre)
            for numero, piso, alicuota in alicuotas:
                unidades[f"{nombre_torre[-1]}-{numero}"] = Unidad.objects.create(
                    edificio=torre, numero=numero, piso=piso, alicuota=Decimal(alicuota)
                )

        # Roles. Residente.save() agrega solo el rol RESIDENTE (ver condominios/models.py).
        Membresia.objects.create(usuario=u["administrador"], condominio=condominio, rol=Membresia.Rol.ADMINISTRADOR)
        Membresia.objects.create(usuario=u["comite"], condominio=condominio, rol=Membresia.Rol.COMITE)
        Membresia.objects.create(usuario=u["conserje"], condominio=condominio, rol=Membresia.Rol.CONSERJE)
        Residente.objects.create(usuario=u["residente"], unidad=unidades["A-101"], tipo=Residente.Tipo.PROPIETARIO)
        Residente.objects.create(usuario=u["comite"], unidad=unidades["A-201"], tipo=Residente.Tipo.PROPIETARIO)
        Residente.objects.create(usuario=u["residente2"], unidad=unidades["B-102"], tipo=Residente.Tipo.ARRENDATARIO)

        quincho = EspacioComun.objects.create(
            condominio=condominio, nombre="Quincho", descripcion="Quincho techado con parrilla y 4 mesas.",
            capacidad=20, tarifa=15000, hora_apertura=time(12), hora_cierre=time(23),
        )
        EspacioComun.objects.create(
            condominio=condominio, nombre="Salón de eventos", descripcion="Salón con cocina, sillas y mesas.",
            capacidad=40, tarifa=25000, hora_apertura=time(10), hora_cierre=time(23),
        )
        EspacioComun.objects.create(
            condominio=condominio, nombre="Gimnasio", descripcion="Máquinas de cardio y pesas.",
            capacidad=8, tarifa=0, hora_apertura=time(6), hora_cierre=time(22),
        )

        # Comunicados: publicar() también genera las notificaciones (patrón Observer).
        Comunicado(
            condominio=condominio, autor=u["administrador"], fijado=True,
            titulo="Bienvenidos a CondoHub",
            contenido="Desde hoy los comunicados, reservas de espacios comunes e incidentes se gestionan en esta plataforma.\n\nCualquier duda, escriban a la administración.",
        ).publicar()
        Comunicado(
            condominio=condominio, autor=u["administrador"], tipo=Comunicado.Tipo.POR_EDIFICIO,
            edificio=condominio.edificios.get(nombre="Torre B"),
            titulo="Corte de agua programado en Torre B",
            contenido="El jueves entre las 10:00 y las 14:00 se cortará el agua en la Torre B por mantención de bombas.",
        ).publicar()

        Incidente(
            condominio=condominio, reportado_por=u["residente"], unidad=unidades["A-101"],
            categoria=Incidente.Categoria.MANTENCION, titulo="Ampolleta quemada en pasillo piso 1",
            descripcion="La luz del pasillo frente al departamento 101 no enciende desde ayer.",
        ).reportar()
        en_proceso = Incidente(
            condominio=condominio, reportado_por=u["residente2"], categoria=Incidente.Categoria.AREAS_COMUNES,
            titulo="Portón de estacionamientos lento", descripcion="El portón demora mucho en abrir.",
        )
        en_proceso.reportar()
        en_proceso.cambiar_estado(Incidente.Estado.EN_PROCESO, "Se solicitó la visita del técnico para el viernes.")

        Reserva(
            espacio=quincho, unidad=unidades["A-101"], solicitante=u["residente"],
            fecha=date.today() + timedelta(days=3), hora_inicio=time(13), hora_fin=time(17),
        ).confirmar()
        return condominio

    def _demo_proveedores(self, condominio):
        """
        Proveedores (Issue #9): empresas que prestan servicios al condominio.
        Devuelve un diccionario {clave: Proveedor} para vincularlos a los egresos.
        Incluye uno inactivo, para mostrar que se desactiva en vez de borrar.
        """
        datos = {
            # clave: (RUT válido, razón social, rubro, contacto, teléfono, correo)
            "ascensores": ("76.123.456-0", "Ascensores Sur SpA", "Ascensores", "Marcela Tapia", "+56 2 2345 6789", "contacto@ascensoressur.cl"),
            "aseo": ("77.234.567-4", "Aseo Limpio Ltda.", "Aseo", "Roberto Díaz", "+56 9 8765 4321", "ventas@aseolimpio.cl"),
            "seguridad": ("78.345.678-8", "Seguridad Andes S.A.", "Seguridad", "Patricia Vera", "+56 2 2987 6543", "camaras@seguridadandes.cl"),
        }
        proveedores = {}
        for clave, (rut, razon, rubro, contacto, telefono, correo) in datos.items():
            proveedores[clave] = Proveedor.objects.create(
                condominio=condominio, rut=rut, razon_social=razon, rubro=rubro,
                contacto=contacto, telefono=telefono, correo=correo,
            )
        # Inactivo: ya no trabaja con el condominio, pero se conserva su historial.
        Proveedor.objects.create(
            condominio=condominio, rut="79.456.789-1", razon_social="Jardines del Valle", rubro="Jardinería",
            contacto="Hugo Reyes", telefono="+56 9 5555 1234", activo=False,
        )
        return proveedores

    def _demo_gastos(self, condominio, u, proveedores=None):
        """
        Gastos comunes (Issues #1 y #2):
          - mes ANTERIOR: emitido, con un cobro por unidad (sirve para el estado de
            cuenta y los pagos);
          - mes ACTUAL: abierto, con egresos, listo para probar la emisión.
        """
        hoy = date.today()
        mes_anterior = hoy.replace(day=1) - timedelta(days=1)  # último día del mes anterior
        anterior = self._periodo_con_egresos(condominio, u, mes_anterior, ajuste=0.97, proveedores=proveedores)
        emitir_periodo(anterior)
        return self._periodo_con_egresos(condominio, u, hoy, proveedores=proveedores)

    def _periodo_con_egresos(self, condominio, u, fecha, ajuste=1.0, proveedores=None):
        """Crea el período del mes de "fecha" con egresos típicos (ajuste: para variar los montos)."""
        proveedores = proveedores or {}
        periodo = PeriodoGasto.objects.create(condominio=condominio, anio=fecha.year, mes=fecha.month)
        C = Egreso.Categoria
        # El 4.º dato es el proveedor (clave del diccionario) o None si no corresponde (sueldos, cuentas básicas).
        egresos = [
            (C.REMUNERACIONES, "Sueldo conserje (jornada completa)", 650000, None),
            (C.REMUNERACIONES, "Sueldo personal de aseo", 520000, None),
            (C.CONSUMOS, "Electricidad áreas comunes", 185430, None),
            (C.CONSUMOS, "Agua áreas comunes y riego", 96780, None),
            (C.MANTENCION, "Mantención mensual de ascensores", 240000, "ascensores"),
            (C.ASEO, "Artículos de aseo", 48990, "aseo"),
            (C.SEGURIDAD, "Monitoreo de cámaras", 75000, "seguridad"),
            (C.ADMINISTRACION, "Honorarios de administración", 350000, None),
        ]
        for dia, (categoria, descripcion, monto, clave_proveedor) in enumerate(egresos, start=1):
            Egreso.objects.create(
                periodo=periodo, categoria=categoria, descripcion=descripcion, monto=round(monto * ajuste),
                fecha=fecha.replace(day=min(dia, fecha.day)), creado_por=u["administrador"],
                proveedor=proveedores.get(clave_proveedor),
            )
        return periodo

    def _demo_pagos(self, condominio, u):
        """
        Pagos (Issue #4), sobre los cobros del período ya emitido:
          - B-102 (Diego): paga el cobro completo -> queda PAGADO;
          - A-101 (Valentina): paga solo $10.000 -> queda con saldo pendiente;
          - las demás unidades quedan sin pagar (para ver la cobranza).
        """
        emitido = PeriodoGasto.objects.get(condominio=condominio, estado=PeriodoGasto.Estado.EMITIDO)
        cobros = {
            f"{d.unidad.edificio.nombre[-1]}-{d.unidad.numero}": d
            for d in emitido.detalles.select_related("unidad__edificio")
        }
        hoy = date.today()
        completo = cobros["B-102"]
        Pago.registrar(
            completo, completo.total, fecha=hoy - timedelta(days=5),
            medio=Pago.Medio.TRANSFERENCIA, observacion="Transferencia del mes", registrado_por=u["administrador"],
        )
        Pago.registrar(
            cobros["A-101"], 10000, fecha=hoy - timedelta(days=2),
            medio=Pago.Medio.EFECTIVO, observacion="Abono en administración", registrado_por=u["administrador"],
        )

    def _crear_los_aromos(self, u):
        condominio = Condominio.objects.create(nombre="Edificio Los Aromos", direccion="Calle Los Aromos 456", comuna="Ñuñoa")
        edificio = Edificio.objects.create(condominio=condominio, nombre="Edificio único")
        unidades = [
            Unidad.objects.create(edificio=edificio, numero=n, piso=int(n[0]), alicuota=Decimal("0.25"))
            for n in ["101", "102", "201", "202"]
        ]
        # El mismo administrador lleva los dos condominios: verá el selector en el menú.
        Membresia.objects.create(usuario=u["administrador"], condominio=condominio, rol=Membresia.Rol.ADMINISTRADOR)
        Residente.objects.create(usuario=u["residente3"], unidad=unidades[0], tipo=Residente.Tipo.PROPIETARIO)
        EspacioComun.objects.create(condominio=condominio, nombre="Sala multiuso", capacidad=15)
        Comunicado(
            condominio=condominio, autor=u["administrador"], titulo="Limpieza de estanques",
            contenido="El sábado se realizará la limpieza anual de los estanques de agua.",
        ).publicar()
        return condominio

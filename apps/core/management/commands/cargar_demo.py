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
    comunicados, incidentes, reservas y gastos comunes (dos meses emitidos, con pagos totales
    y parciales y unidades morosas, y el mes actual abierto).
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
        self._demo_gastos(vista_verde, u)

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

    def _demo_gastos(self, condominio, u):
        """
        Gastos comunes y pagos (Issues #1, #2, #4 y #5):
          - hace DOS meses: emitido; pagaron todos menos A-102 y B-202 (quedan morosas);
          - mes ANTERIOR: emitido; la mitad pagó, B-201 hizo un abono PARCIAL y el
            resto debe (sirve para el estado de cuenta, la cobranza y el reporte);
          - mes ACTUAL: abierto, con egresos, listo para probar la emisión.
        """
        hoy = date.today()
        mes_anterior = hoy.replace(day=1) - timedelta(days=1)  # último día del mes anterior
        hace_dos_meses = mes_anterior.replace(day=1) - timedelta(days=1)

        antiguo = self._periodo_con_egresos(condominio, u, hace_dos_meses, ajuste=1.02)
        emitir_periodo(antiguo)
        self._registrar_pagos(antiguo, u, hace_dos_meses, excepto=["A-102", "B-202"])

        anterior = self._periodo_con_egresos(condominio, u, mes_anterior, ajuste=0.97)
        emitir_periodo(anterior)
        self._registrar_pagos(anterior, u, mes_anterior, solo=["A-201", "A-202", "A-301", "B-101", "B-301"])
        self._registrar_pagos(anterior, u, mes_anterior, solo=["B-201"], monto=100000)  # abono parcial
        return self._periodo_con_egresos(condominio, u, hoy)

    def _registrar_pagos(self, periodo, u, fecha, solo=None, excepto=(), monto=None):
        """
        Registra pagos de los cobros del período con Pago.registrar() (Issue #4), igual
        que lo haría el administrador: así el cobro pasa a PAGADO solo y el residente
        recibe su notificación. Unidades por "Torre-número", ej. "A-102".
        monto=None paga el total; un número registra un abono parcial.
        """
        medios = [Pago.Medio.TRANSFERENCIA, Pago.Medio.EFECTIVO, Pago.Medio.CHEQUE]  # para variar
        cobros = periodo.detalles.select_related("unidad__edificio").order_by("unidad__edificio__nombre", "unidad__numero")
        for i, cobro in enumerate(cobros):
            clave = f"{cobro.unidad.edificio.nombre[-1]}-{cobro.unidad.numero}"
            if (solo is None or clave in solo) and clave not in excepto:
                Pago.registrar(
                    cobro, monto=monto or cobro.total, fecha=fecha, medio=medios[i % len(medios)],
                    registrado_por=u["administrador"],
                )

    def _periodo_con_egresos(self, condominio, u, fecha, ajuste=1.0):
        """Crea el período del mes de "fecha" con egresos típicos (ajuste: para variar los montos)."""
        periodo = PeriodoGasto.objects.create(condominio=condominio, anio=fecha.year, mes=fecha.month)
        C = Egreso.Categoria
        egresos = [
            (C.REMUNERACIONES, "Sueldo conserje (jornada completa)", 650000),
            (C.REMUNERACIONES, "Sueldo personal de aseo", 520000),
            (C.CONSUMOS, "Electricidad áreas comunes", 185430),
            (C.CONSUMOS, "Agua áreas comunes y riego", 96780),
            (C.MANTENCION, "Mantención mensual de ascensores", 240000),
            (C.ASEO, "Artículos de aseo", 48990),
            (C.SEGURIDAD, "Monitoreo de cámaras", 75000),
            (C.ADMINISTRACION, "Honorarios de administración", 350000),
        ]
        for dia, (categoria, descripcion, monto) in enumerate(egresos, start=1):
            Egreso.objects.create(
                periodo=periodo, categoria=categoria, descripcion=descripcion, monto=round(monto * ajuste),
                fecha=fecha.replace(day=min(dia, fecha.day)), creado_por=u["administrador"],
            )
        return periodo

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

"""
Datos demo de comunicados (Issue #62). publicar() también genera las notificaciones (patrón Observer).

Vigencia y lectura (Issue #58), sin agregar comunicados (CargarDemoTest cuenta 3): el corte de
agua de la Torre B ya venció (se ve en «Ver vencidos») y residente2@condohub.cl, que vive en
la Torre B, lo marcó como leído (el administrador ve «1 de N unidades confirmaron»).

Demo del cliente (datos["fecha_referencia_demo"], Issue #96): se suman dos comunicados vigentes, uno
general con fecha de vigencia y uno dirigido a la Torre A con lectura confirmada por
residente@condohub.cl. Se publican al cargar (nunca con fecha futura, que los ocultaría) y la carga
normal conserva sus 3 comunicados. También un aviso prioritario (#118) para la Torre B.
"""
from datetime import timedelta

from django.utils import timezone

from apps.comunicados.models import Comunicado, LecturaComunicado


def cargar(datos):
    admin = datos["usuarios"]["administrador"]
    vista_verde = datos["vista_verde"]
    Comunicado(
        condominio=vista_verde, autor=admin, fijado=True,
        titulo="Bienvenidos a CondoHub",
        contenido="Desde hoy los comunicados, reservas de espacios comunes e incidentes se gestionan en esta plataforma.\n\nCualquier duda, escriban a la administración.",
    ).publicar()
    corte = Comunicado(
        condominio=vista_verde, autor=admin, tipo=Comunicado.Tipo.POR_EDIFICIO,
        edificio=vista_verde.edificios.get(nombre="Torre B"),
        titulo="Corte de agua programado en Torre B",
        contenido="El jueves entre las 10:00 y las 14:00 se cortará el agua en la Torre B por mantención de bombas.",
        vigente_hasta=timezone.localdate() - timedelta(days=1),
    )
    corte.publicar()
    LecturaComunicado.objects.create(comunicado=corte, usuario=datos["usuarios"]["residente2"])
    Comunicado(
        condominio=datos["los_aromos"], autor=admin, titulo="Limpieza de estanques",
        contenido="El sábado se realizará la limpieza anual de los estanques de agua.",
    ).publicar()

    if "fecha_referencia_demo" in datos:
        # Visibles hasta una semana después de la demo: vigentes en el ensayo y el día de la reunión.
        hasta = max(datos["fecha_referencia_demo"], timezone.localdate()) + timedelta(days=7)
        Comunicado(
            condominio=vista_verde, autor=admin,
            titulo="Mantención de ascensores esta semana",
            contenido="Durante esta semana se realizará la mantención preventiva de los ascensores de ambas torres.\n\n"
                      "Cada ascensor quedará fuera de servicio por un máximo de dos horas. Se avisará en el hall.",
            vigente_hasta=hasta,
        ).publicar()
        bicicletas = Comunicado(
            condominio=vista_verde, autor=admin, tipo=Comunicado.Tipo.POR_EDIFICIO,
            edificio=vista_verde.edificios.get(nombre="Torre A"),
            titulo="Retiro de bicicletas abandonadas en Torre A",
            contenido="Las bicicletas sin identificación en la bicicletera de la Torre A se retirarán el próximo lunes. "
                      "Si alguna es suya, márquela con el número de su departamento.",
            vigente_hasta=hasta,
        )
        bicicletas.publicar()
        LecturaComunicado.objects.create(comunicado=bicicletas, usuario=datos["usuarios"]["residente"])

        # Aviso prioritario (#118): a la Torre B, para que residente2 lo vea a pantalla completa
        # al entrar y la cuenta principal del recorrido (residente, Torre A) siga sin bloqueo.
        # Nadie lo ha confirmado: el administrador ve «0 de N» en «Ver quién leyó».
        Comunicado(
            condominio=vista_verde, autor=admin, tipo=Comunicado.Tipo.POR_EDIFICIO, prioritario=True,
            edificio=vista_verde.edificios.get(nombre="Torre B"),
            titulo="Simulacro de evacuación en Torre B",
            contenido="El jueves a las 11:00 se realizará un simulacro de evacuación en la Torre B.\n\n"
                      "Al sonar la alarma, bajen por la escalera de emergencia y reúnanse en la plaza central. "
                      "No usen los ascensores.",
            vigente_hasta=hasta,
        ).publicar()

"""
"Descargar mis datos" (Issue #51, Ley 21.719): todo lo de una persona en un solo JSON.

Reúne la cuenta y lo vinculado a ella en todos sus condominios. Los cobros respetan el
período de residencia (#46) con cobros_visibles, así la descarga nunca muestra la deuda de
quien vivió antes en la unidad. A diferencia de "Mi cuenta", incluye las residencias ya
dadas de baja (dentro de sus fechas): esos cobros siguen siendo datos de la persona.
"""
from apps.condominios.residencias import cobros_visibles
from apps.gastos.models import DetalleGastoComun, PeriodoGasto
from apps.pagos.consultas import pagado_del_cobro, saldo_del_cobro


def datos_de(usuario):
    residencias = usuario.residencias.select_related("unidad__edificio__condominio").order_by("desde")
    cobros = (
        cobros_visibles(DetalleGastoComun.objects.filter(periodo__estado=PeriodoGasto.Estado.EMITIDO), usuario, incluir_bajas=True)
        .select_related("periodo__condominio", "unidad__edificio")
        .prefetch_related("pagos")
        .order_by("periodo__condominio__nombre", "-periodo__anio", "-periodo__mes", "unidad__numero")
    )
    return {
        "cuenta": {
            "correo": usuario.email,
            "nombre": usuario.first_name,
            "apellido": usuario.last_name,
            "rut": usuario.rut,
            "telefono": usuario.telefono,
            "recibir_correos": usuario.recibir_correos,
            "creada": usuario.date_joined,
            "ultimo_ingreso": usuario.last_login,
        },
        "roles": [
            {"condominio": m.condominio.nombre, "rol": m.get_rol_display(), "activo": m.activo, "desde": m.desde}
            for m in usuario.membresias.select_related("condominio").order_by("desde")
        ],
        "residencias": [
            {
                "condominio": r.unidad.edificio.condominio.nombre,
                "unidad": str(r.unidad),
                "tipo": r.get_tipo_display(),
                "activo": r.activo,
                "desde": r.desde,
                "hasta": r.hasta,
            }
            for r in residencias
        ],
        "cobros": [
            {
                "condominio": c.periodo.condominio.nombre,
                "unidad": str(c.unidad),
                "periodo": str(c.periodo),
                "total": c.total,
                "pagado": pagado_del_cobro(c),
                "saldo": saldo_del_cobro(c),
                "estado": c.get_estado_display(),
                "pagos": [
                    {"fecha": p.fecha, "monto": p.monto, "medio": p.get_medio_display()} for p in c.pagos.all()
                ],
            }
            for c in cobros
        ],
        "reservas": [
            {
                "espacio": r.espacio.nombre,
                "unidad": str(r.unidad),
                "fecha": r.fecha,
                "desde": r.hora_inicio,
                "hasta": r.hora_fin,
                "estado": r.get_estado_display(),
            }
            for r in usuario.reservas.select_related("espacio", "unidad__edificio").order_by("fecha")
        ],
        "incidentes": [
            {
                "titulo": i.titulo,
                "categoria": i.get_categoria_display(),
                "descripcion": i.descripcion,
                "estado": i.get_estado_display(),
                "respuesta": i.respuesta,
                "fecha": i.fecha_reporte,
            }
            for i in usuario.incidentes.order_by("fecha_reporte")
        ],
        "solicitudes_de_datos": [
            {
                "condominio": s.condominio.nombre,
                "tipo": s.get_tipo_display(),
                "detalle": s.detalle,
                "estado": s.get_estado_display(),
                "respuesta": s.respuesta,
                "creada": s.creada,
                "cerrada": s.cerrada,
            }
            for s in usuario.solicitudes_titular.select_related("condominio").order_by("creada")
        ],
        "notificaciones": [
            {"titulo": n.titulo, "mensaje": n.mensaje, "leida": n.leida, "creada": n.creada}
            for n in usuario.notificaciones.order_by("creada")
        ],
    }

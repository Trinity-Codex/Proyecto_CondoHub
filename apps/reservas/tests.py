"""Pruebas de reservas: disponibilidad (RF05) y reservas sin superposición (RF06)."""
from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.core.pruebas import crear_escenario

from .models import Reserva

MANANA = date.today() + timedelta(days=1)


class ReglasReservaTest(TestCase):
    """Reglas de negocio del modelo (Reserva.clean)."""

    def setUp(self):
        self.e = crear_escenario()
        self.reservar(time(10), time(12))  # reserva existente: 10:00 a 12:00

    def reservar(self, inicio, fin, fecha=MANANA, unidad=None):
        reserva = Reserva(
            espacio=self.e.quincho, unidad=unidad or self.e.a101, solicitante=self.e.residente,
            fecha=fecha, hora_inicio=inicio, hora_fin=fin,
        )
        reserva.confirmar()
        return reserva

    def test_rechaza_horarios_que_se_topan(self):
        # Todas se superponen con 10:00-12:00 (RF06).
        for inicio, fin in [(time(10), time(12)), (time(11), time(13)), (time(9), time(11)), (time(9), time(13)), (time(10, 30), time(11))]:
            with self.assertRaises(ValidationError, msg=f"{inicio}-{fin}"):
                self.reservar(inicio, fin, unidad=self.e.a102)

    def test_permite_horarios_contiguos(self):
        self.reservar(time(12), time(14))  # empieza justo cuando termina la otra
        self.reservar(time(9), time(10))
        self.assertEqual(Reserva.objects.count(), 3)

    def test_otro_dia_no_se_topa(self):
        self.reservar(time(10), time(12), fecha=MANANA + timedelta(days=1))

    def test_cancelada_libera_el_horario(self):
        Reserva.objects.get().cancelar()
        self.reservar(time(10), time(12))

    def test_fuera_del_horario_del_espacio(self):
        with self.assertRaises(ValidationError):
            self.reservar(time(21), time(23))  # el quincho cierra a las 22:00

    def test_fecha_pasada(self):
        with self.assertRaises(ValidationError):
            self.reservar(time(15), time(16), fecha=date.today() - timedelta(days=1))

    def test_termino_antes_del_inicio(self):
        with self.assertRaises(ValidationError):
            self.reservar(time(16), time(15))


class VistasReservaTest(TestCase):
    def setUp(self):
        self.e = crear_escenario()

    def datos(self, **cambios):
        return {
            "espacio": self.e.quincho.pk, "unidad": self.e.a101.pk, "fecha": MANANA.isoformat(),
            "hora_inicio": "15:00", "hora_fin": "17:00", **cambios,
        }

    def test_residente_reserva(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.post(reverse("reservas:nueva"), self.datos())
        self.assertRedirects(respuesta, reverse("reservas:mis_reservas"))
        self.assertEqual(Reserva.objects.get().solicitante, self.e.residente)

    def test_formulario_muestra_el_tope(self):
        self.client.force_login(self.e.residente)
        self.client.post(reverse("reservas:nueva"), self.datos())
        self.client.force_login(self.e.residente_b)
        respuesta = self.client.post(reverse("reservas:nueva"), self.datos(unidad=self.e.b101.pk, hora_inicio="16:00"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "ya está reservado")
        self.assertEqual(Reserva.objects.count(), 1)

    def test_no_puede_reservar_con_unidad_ajena(self):
        self.client.force_login(self.e.residente)
        respuesta = self.client.post(reverse("reservas:nueva"), self.datos(unidad=self.e.b101.pk))
        self.assertIn("unidad", respuesta.context["form"].errors)

    def test_administrador_sin_unidad_no_reserva(self):
        self.client.force_login(self.e.administrador)
        self.assertEqual(self.client.get(reverse("reservas:nueva")).status_code, 403)

    def test_disponibilidad_del_dia(self):
        Reserva(espacio=self.e.quincho, unidad=self.e.a101, solicitante=self.e.residente,
                fecha=MANANA, hora_inicio=time(10), hora_fin=time(12)).confirmar()
        self.client.force_login(self.e.residente_b)
        respuesta = self.client.get(reverse("reservas:espacio_detalle", args=[self.e.quincho.pk]), {"fecha": MANANA.isoformat()})
        self.assertEqual(len(respuesta.context["reservas_del_dia"]), 1)

    def test_cancelar_propia_y_no_ajena(self):
        reserva = Reserva(espacio=self.e.quincho, unidad=self.e.a101, solicitante=self.e.residente,
                          fecha=MANANA, hora_inicio=time(10), hora_fin=time(12))
        reserva.confirmar()
        url = reverse("reservas:cancelar", args=[reserva.pk])
        self.client.force_login(self.e.residente_b)
        self.client.post(url)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.CONFIRMADA)  # otro residente no puede
        self.client.force_login(self.e.residente)
        self.client.post(url)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.CANCELADA)

    def test_cancelar_no_redirige_a_otro_sitio(self):
        reserva = Reserva(espacio=self.e.quincho, unidad=self.e.a101, solicitante=self.e.residente,
                          fecha=MANANA, hora_inicio=time(10), hora_fin=time(12))
        reserva.confirmar()
        self.client.force_login(self.e.residente)
        respuesta = self.client.post(reverse("reservas:cancelar", args=[reserva.pk]), {"volver": "https://sitio-malicioso.com/"})
        self.assertRedirects(respuesta, reverse("reservas:mis_reservas"))

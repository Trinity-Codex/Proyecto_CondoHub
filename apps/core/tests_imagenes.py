"""Pruebas del validador compartido de imágenes subidas (apps/core/imagenes.py, Issue #116)."""
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from apps.core.imagenes import PIXELES_MAXIMOS, RutaAleatoria, preparar_imagen, validar_imagen


def imagen(formato="JPEG", tamano=(40, 30), modo="RGB", nombre=None, exif=None, color=(200, 30, 30)):
    """Archivo subido con una imagen real del formato pedido."""
    salida = BytesIO()
    extra = {"exif": exif} if exif is not None else {}
    Image.new(modo, tamano, color if modo != "1" else 1).save(salida, format=formato, **extra)
    nombre = nombre or f"foto.{ {'JPEG': 'jpg'}.get(formato, formato.lower()) }"
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type="image/jpeg")


def exif_con_gps_y_orientacion(orientacion=1):
    exif = Image.Exif()
    exif[0x0112] = orientacion  # Orientation
    exif[0x010F] = "CamaraDePrueba"  # Make
    exif[0x8825] = {1: "S", 2: (33.0, 26.0, 0.0)}  # GPSInfo
    return exif.tobytes()


def abrir(contenido):
    return Image.open(BytesIO(contenido.read() if hasattr(contenido, "read") else contenido))


class ValidarImagenTest(SimpleTestCase):
    def test_acepta_jpg_y_png_reales(self):
        self.assertEqual(validar_imagen(imagen("JPEG")), "JPEG")
        self.assertEqual(validar_imagen(imagen("PNG", modo="RGBA", color=(0, 0, 0, 0))), "PNG")

    def test_rechaza_otros_formatos_aunque_la_extension_diga_jpg(self):
        for formato in ("GIF", "BMP", "WEBP", "TIFF"):
            with self.subTest(formato=formato), self.assertRaisesMessage(ValidationError, "JPG o PNG"):
                validar_imagen(imagen(formato, nombre="disfrazada.jpg"))

    def test_rechaza_svg_y_texto(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        for nombre, contenido in [("logo.svg", svg), ("logo.png", svg), ("notas.jpg", b"hola mundo")]:
            with self.subTest(nombre=nombre), self.assertRaisesMessage(ValidationError, "JPG o PNG"):
                validar_imagen(SimpleUploadedFile(nombre, contenido, content_type="image/png"))

    def test_rechaza_imagen_dañada(self):
        completo = imagen("JPEG", tamano=(200, 200)).read()
        with self.assertRaises(ValidationError) as error:
            preparar_imagen(SimpleUploadedFile("cortada.jpg", completo[: len(completo) // 2]))
        self.assertIn(error.exception.code, {"imagen_danada", "imagen_formato"})

    def test_rechaza_archivos_sobre_el_limite_con_mensaje_claro(self):
        archivo = imagen("PNG")
        with self.assertRaisesMessage(ValidationError, "pesa más de 2 MB"):
            validar_imagen(SimpleUploadedFile("grande.png", archivo.read() + b"\0" * (2 * 1024 * 1024)))
        archivo.seek(0)
        with self.assertRaisesMessage(ValidationError, "pesa más de 1,5 MB"):  # el límite se puede ajustar
            validar_imagen(SimpleUploadedFile("media.png", archivo.read() + b"\0" * (1600 * 1024)),
                           tamano_maximo=1536 * 1024)
        self.assertEqual(validar_imagen(imagen("PNG"), tamano_maximo=2 * 1024 * 1024), "PNG")

    def test_rechaza_demasiados_pixeles_sin_decodificarla(self):
        lado = int(PIXELES_MAXIMOS ** 0.5) + 10
        enorme = imagen("PNG", tamano=(lado, lado), modo="1")  # pocos bytes, muchos píxeles
        with self.assertRaisesMessage(ValidationError, "demasiados píxeles"):
            validar_imagen(enorme)

    def test_deja_el_puntero_al_inicio(self):
        archivo = imagen("JPEG")
        validar_imagen(archivo)
        self.assertEqual(archivo.tell(), 0)


class PrepararImagenTest(SimpleTestCase):
    def test_vuelve_a_codificar_sin_exif_y_con_nombre_al_azar(self):
        original = imagen("JPEG", nombre="Mi casa en Ñuñoa.jpg", exif=exif_con_gps_y_orientacion())
        self.assertIn(0x8825, abrir(original).getexif())
        original.seek(0)
        limpia = preparar_imagen(original)
        self.assertRegex(limpia.name, r"^[0-9a-f]{32}\.jpg$")
        resultado = abrir(limpia)
        self.assertEqual(resultado.format, "JPEG")
        self.assertEqual(len(resultado.getexif()), 0)
        limpia.seek(0)
        self.assertNotIn(b"CamaraDePrueba", limpia.read())

    def test_png_conserva_transparencia(self):
        limpia = preparar_imagen(imagen("PNG", modo="RGBA", color=(10, 20, 30, 0)))
        self.assertTrue(limpia.name.endswith(".png"))
        resultado = abrir(limpia)
        self.assertEqual(resultado.mode, "RGBA")
        self.assertEqual(resultado.getpixel((0, 0))[3], 0)

    def test_aplica_la_orientacion_antes_de_quitar_el_exif(self):
        # Orientación 6: la cámara guardó la foto acostada; se debe ver de pie (ancho y alto se intercambian).
        limpia = preparar_imagen(imagen("JPEG", tamano=(40, 30), exif=exif_con_gps_y_orientacion(6)))
        self.assertEqual(abrir(limpia).size, (30, 40))

    def test_reduce_al_lado_maximo_sin_agrandar(self):
        self.assertEqual(abrir(preparar_imagen(imagen("PNG", tamano=(1200, 600)), lado_maximo=300)).size, (300, 150))
        self.assertEqual(abrir(preparar_imagen(imagen("PNG", tamano=(100, 50)), lado_maximo=300)).size, (100, 50))

    def test_lo_que_no_es_una_subida_nueva_pasa_igual(self):
        for valor in (None, False, "", "condominios/logos/ya_guardado.png"):
            with self.subTest(valor=valor):
                self.assertEqual(preparar_imagen(valor), valor)

    def test_propaga_el_error_de_validacion(self):
        with self.assertRaisesMessage(ValidationError, "JPG o PNG"):
            preparar_imagen(imagen("GIF", nombre="x.png"))


class RutaAleatoriaTest(SimpleTestCase):
    def test_genera_nombre_al_azar_en_la_carpeta(self):
        ruta = RutaAleatoria("/condominios/logos/")
        primera, segunda = ruta(None, "abc.PNG"), ruta(None, "abc.PNG")
        self.assertRegex(primera, r"^condominios/logos/[0-9a-f]{32}\.png$")
        self.assertNotEqual(primera, segunda)

    def test_no_usa_el_nombre_ni_extensiones_peligrosas(self):
        self.assertRegex(RutaAleatoria("x")(None, "../../config/settings.py"), r"^x/[0-9a-f]{32}\.bin$")
        self.assertRegex(RutaAleatoria("x")(None, "sin_extension"), r"^x/[0-9a-f]{32}\.bin$")

    def test_se_serializa_para_migraciones(self):
        self.assertEqual(RutaAleatoria("a").deconstruct(), ("apps.core.imagenes.RutaAleatoria", ("a",), {}))
        self.assertEqual(RutaAleatoria("a"), RutaAleatoria("a"))

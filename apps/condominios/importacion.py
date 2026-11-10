"""
Importar edificios, unidades y residentes desde un CSV (Issue #13, RF01).

Tres pasos, separados de las vistas para probarlos solos:

    filas = leer(decodificar(contenido))      # texto -> filas (ArchivoInvalido si no se puede leer)
    resultado = validar(filas, condominio)     # errores por fila y resumen; NO guarda nada
    if resultado.valido:
        cuentas_nuevas = aplicar(resultado, condominio)   # todo o nada (transaction.atomic)

Reimportar el mismo archivo no duplica: edificios, unidades, cuentas y residentes se
buscan por nombre, número y correo, y si ya existen se actualizan.
"""
import csv
import io
import secrets
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.cuentas.models import Usuario
from apps.cuentas.validadores import normalizar_rut, validar_rut

from .auditoria import datos_de, registrar_cambio, registrar_roles, roles_de
from .models import Edificio, Residente, Unidad

COLUMNAS = [
    "edificio", "numero", "piso", "tipo", "alicuota",
    "correo", "nombre", "apellido", "rut", "tipo_residente", "desde",
]
OBLIGATORIAS = ["edificio", "numero", "alicuota"]
MAX_BYTES = 1_000_000  # 1 MB: un condominio de 200 unidades ocupa unos 20 KB
FORMATOS_FECHA = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]

# Filas de ejemplo de la plantilla: una unidad con dos residentes y otra sin residente.
EJEMPLO = [
    ["Torre A", "101", "1", "Departamento", "0,5", "ana.perez@ejemplo.cl", "Ana", "Pérez", "11.111.111-1", "Propietario", "2024-03-01"],
    ["Torre A", "101", "1", "Departamento", "0,5", "tomas.perez@ejemplo.cl", "Tomás", "Pérez", "22.222.222-2", "Familiar", "2024-03-01"],
    ["Torre A", "102", "1", "Departamento", "0,5", "", "", "", "", "", ""],
]


class ArchivoInvalido(Exception):
    """El archivo no se puede leer como la planilla de importación."""


def sin_tildes(texto):
    """ "Número " -> "numero": para comparar encabezados y tipos sin importar tildes ni mayúsculas."""
    texto = unicodedata.normalize("NFKD", texto.strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def opciones(choices):
    """Acepta el valor ("LOCAL") o el nombre visible ("Local comercial") de cada opción."""
    mapa = {}
    for valor, nombre in choices:
        mapa[sin_tildes(valor)] = valor
        mapa[sin_tildes(nombre)] = valor
    return mapa


TIPOS_UNIDAD = opciones(Unidad.Tipo.choices)
TIPOS_RESIDENTE = opciones(Residente.Tipo.choices)


def decodificar(contenido):
    """UTF-8 (con o sin BOM, el que usa Excel "CSV UTF-8") y, si falla, Windows-1252 (el "CSV" de Excel)."""
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("cp1252", errors="replace")


@dataclass
class Fila:
    linea: int               # número de fila en la planilla (la 1 son los encabezados)
    datos: dict
    errores: list = field(default_factory=list)
    # Valores ya interpretados (los llena validar()):
    piso: int = 1
    tipo: str = Unidad.Tipo.DEPARTAMENTO
    alicuota: Decimal = Decimal("0")
    tipo_residente: str = Residente.Tipo.PROPIETARIO
    desde: object = None

    def __getitem__(self, columna):
        # KeyError fuera de las columnas: así las plantillas de Django usan los atributos (fila.errores).
        if columna not in COLUMNAS:
            raise KeyError(columna)
        return self.datos.get(columna, "")

    @property
    def clave_unidad(self):
        return (sin_tildes(self["edificio"]), self["numero"].lower())

    @property
    def correo(self):
        return self["correo"].lower()


def leer(texto):
    """Convierte el texto del CSV en filas. El separador (; o ,) se toma de la línea de encabezados."""
    primera = texto.lstrip().split("\n", 1)[0]
    if not primera.strip():
        raise ArchivoInvalido("El archivo está vacío.")
    separador = ";" if primera.count(";") >= primera.count(",") else ","
    lector = csv.reader(io.StringIO(texto.lstrip()), delimiter=separador)
    encabezados = [sin_tildes(e) for e in next(lector)]
    faltan = [c for c in OBLIGATORIAS if c not in encabezados]
    if faltan:
        raise ArchivoInvalido(
            f"Faltan las columnas {', '.join(faltan)}. Usa los encabezados de la plantilla: {';'.join(COLUMNAS)}."
        )
    # Una columna mal escrita ("correo electronico") se perdería sin aviso: mejor rechazar el archivo.
    desconocidas = [e for e in encabezados if e and e not in COLUMNAS]
    if desconocidas:
        raise ArchivoInvalido(
            f"No reconocemos las columnas {', '.join(desconocidas)}. Usa los encabezados de la plantilla: {';'.join(COLUMNAS)}."
        )
    filas = []
    for linea, valores in enumerate(lector, start=2):
        datos = {c: v.strip() for c, v in zip(encabezados, valores) if c}
        sobran = [v for v in valores[len(encabezados):] if v.strip()]
        if not any(datos.values()) and not sobran:
            continue  # las filas vacías se ignoran
        fila = Fila(linea, datos)
        if sobran:
            # Típico de "0,5" sin comillas en un CSV separado por comas: la alícuota quedaría en "0".
            fila.errores.append(
                "La fila tiene más valores que columnas. Si el separador es la coma, escribe los decimales "
                "con punto (0.0125) o entre comillas."
            )
        filas.append(fila)
    if not filas:
        raise ArchivoInvalido("El archivo no tiene filas con datos.")
    return filas


@dataclass
class Resultado:
    filas: list
    errores_globales: list = field(default_factory=list)
    suma_alicuotas: Decimal = Decimal("0")
    resumen: dict = field(default_factory=dict)

    @property
    def filas_con_error(self):
        return [f for f in self.filas if f.errores]

    @property
    def valido(self):
        return not self.errores_globales and not self.filas_con_error


def leer_fecha(texto):
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def validar_unidad(fila):
    """Campos de la unidad: obligatorios, largo, piso, tipo y alícuota."""
    for columna in OBLIGATORIAS:
        if not fila[columna]:
            fila.errores.append(f"Falta el dato «{columna}».")
    if len(fila["edificio"]) > 80:
        fila.errores.append("El nombre del edificio tiene más de 80 caracteres.")
    if len(fila["numero"]) > 10:
        fila.errores.append("El número de la unidad tiene más de 10 caracteres.")
    if fila["piso"]:
        try:
            fila.piso = int(fila["piso"])
        except ValueError:
            fila.errores.append(f"El piso «{fila['piso']}» no es un número entero.")
        else:
            if not -10 <= fila.piso <= 200:
                fila.errores.append("El piso debe estar entre -10 y 200.")
    if fila["tipo"]:
        fila.tipo = TIPOS_UNIDAD.get(sin_tildes(fila["tipo"]))
        if fila.tipo is None:
            fila.errores.append(f"El tipo «{fila['tipo']}» no existe. Usa: {', '.join(Unidad.Tipo.labels)}.")
    if fila["alicuota"]:
        try:
            fila.alicuota = Decimal(fila["alicuota"].replace(",", "."))
        except InvalidOperation:
            fila.errores.append(f"La alícuota «{fila['alicuota']}» no es un número (ejemplo: 0,0125).")
        else:
            if not Decimal("0") <= fila.alicuota <= Decimal("1"):
                fila.errores.append("La alícuota debe estar entre 0 y 1 (ejemplo: 0,0125 = 1,25 %).")
            elif fila.alicuota.as_tuple().exponent < -6:
                fila.errores.append("La alícuota admite hasta 6 decimales.")


def validar_residente(fila, cuentas, ruts_ocupados):
    """Campos del residente. Los datos de la persona solo se exigen si su correo no tiene cuenta."""
    try:
        validate_email(fila.correo)
    except ValidationError:
        fila.errores.append(f"El correo «{fila['correo']}» no es válido.")
        return
    if fila["tipo_residente"]:
        fila.tipo_residente = TIPOS_RESIDENTE.get(sin_tildes(fila["tipo_residente"]))
        if fila.tipo_residente is None:
            fila.errores.append(
                f"El tipo de residente «{fila['tipo_residente']}» no existe. Usa: Propietario, Arrendatario o Familiar."
            )
    if not fila["desde"]:
        fila.errores.append("Falta la fecha desde (desde cuándo vive en la unidad).")
    else:
        fila.desde = leer_fecha(fila["desde"])
        if fila.desde is None:
            fila.errores.append(f"La fecha «{fila['desde']}» no es válida. Usa AAAA-MM-DD o DD-MM-AAAA.")
        elif fila.desde > timezone.localdate():
            fila.errores.append("La fecha desde no puede ser futura.")
    if fila.correo in cuentas:
        if not cuentas[fila.correo].is_active:
            fila.errores.append(f"La cuenta de {fila.correo} está desactivada. Reactívala antes de importarla.")
        return  # la cuenta ya existe: no se usan ni se cambian sus datos
    for columna in ("nombre", "apellido", "rut"):
        if not fila[columna]:
            fila.errores.append(f"Falta el dato «{columna}»: el correo {fila.correo} no tiene cuenta y hay que crearla.")
        elif len(fila[columna]) > 150:
            fila.errores.append(f"El {columna} tiene más de 150 caracteres.")
    if fila["rut"]:
        try:
            validar_rut(fila["rut"])
        except ValidationError:
            fila.errores.append(f"El RUT «{fila['rut']}» no es válido.")
        else:
            dueno = ruts_ocupados.get(normalizar_rut(fila["rut"]))
            if dueno and dueno != fila.correo:
                fila.errores.append(f"El RUT {fila['rut']} ya pertenece a otra cuenta.")


def existentes(condominio):
    """Edificios y unidades del condominio, por nombre y número sin tildes ni mayúsculas."""
    edificios = {sin_tildes(e.nombre): e for e in Edificio.objects.filter(condominio=condominio)}
    unidades = {
        (sin_tildes(u.edificio.nombre), u.numero.lower()): u
        for u in Unidad.objects.filter(edificio__condominio=condominio).select_related("edificio")
    }
    return edificios, unidades


def validar(filas, condominio):
    """Revisa todo el archivo sin guardar nada. Carga antes lo existente para no consultar por fila."""
    edificios, unidades = existentes(condominio)
    correos = {f.correo for f in filas if f.correo}
    cuentas = {u.email.lower(): u for u in Usuario.objects.filter(email__in=correos)}
    ruts = {normalizar_rut(f["rut"]) for f in filas if f["rut"]}
    ruts_ocupados = {u.rut: u.email.lower() for u in Usuario.objects.filter(rut__in=ruts)}
    activos = {
        (unidad_id, correo.lower())
        for unidad_id, correo in Residente.objects.filter(
            unidad__edificio__condominio=condominio, activo=True
        ).values_list("unidad_id", "usuario__email")
    }

    unidad_vista, residente_visto, persona_vista, ruts_del_archivo = {}, {}, {}, {}
    for fila in filas:
        validar_unidad(fila)
        if fila.correo:
            validar_residente(fila, cuentas, ruts_ocupados)
        clave = fila.clave_unidad
        datos_unidad = (fila.piso, fila.tipo, fila.alicuota)
        if clave in unidad_vista and unidad_vista[clave][1] != datos_unidad:
            fila.errores.append(
                f"La unidad {fila['numero']} de {fila['edificio']} ya aparece en la fila {unidad_vista[clave][0]} "
                "con otro piso, tipo o alícuota."
            )
        unidad_vista.setdefault(clave, (fila.linea, datos_unidad))
        if not fila.correo:
            continue
        if (clave, fila.correo) in residente_visto:
            fila.errores.append(
                f"{fila.correo} ya aparece como residente de esta unidad en la fila {residente_visto[clave, fila.correo]}."
            )
        residente_visto.setdefault((clave, fila.correo), fila.linea)
        if fila.correo not in cuentas:
            persona = (fila["nombre"], fila["apellido"], normalizar_rut(fila["rut"]))
            if fila.correo in persona_vista and persona_vista[fila.correo][1] != persona:
                fila.errores.append(
                    f"{fila.correo} ya aparece en la fila {persona_vista[fila.correo][0]} con otro nombre, apellido o RUT."
                )
            persona_vista.setdefault(fila.correo, (fila.linea, persona))
            # Un RUT nuevo tampoco puede repetirse entre dos correos nuevos del archivo.
            rut = normalizar_rut(fila["rut"])
            if rut:
                dueno = ruts_del_archivo.setdefault(rut, fila.correo)
                if dueno != fila.correo and not any("RUT" in e for e in fila.errores):
                    fila.errores.append(f"El RUT {fila['rut']} ya aparece con otro correo en el archivo.")

    resultado = Resultado(filas=filas)
    # Alícuotas después de importar: las del archivo reemplazan a las de esas unidades.
    alicuotas = {clave: u.alicuota for clave, u in unidades.items()}
    alicuotas.update({clave: datos[1][2] for clave, datos in unidad_vista.items()})
    resultado.suma_alicuotas = sum(alicuotas.values(), Decimal("0"))
    if resultado.suma_alicuotas != 1:
        suma = f"{resultado.suma_alicuotas:.6f}".replace(".", ",")  # coma decimal, como en Chile
        resultado.errores_globales.append(
            f"Después de importar, las alícuotas del condominio sumarían {suma} y deben sumar 1. "
            "Revisa las alícuotas del archivo (las unidades que no están en él conservan la suya)."
        )
    residentes_nuevos = sum(
        1
        for clave, correo in residente_visto
        if not (clave in unidades and (unidades[clave].pk, correo) in activos)
    )
    resultado.resumen = {
        "edificios_nuevos": len({c[0] for c in unidad_vista} - set(edificios)),
        "unidades_nuevas": len(set(unidad_vista) - set(unidades)),
        "unidades_actualizadas": len(set(unidad_vista) & set(unidades)),
        "cuentas_nuevas": len(correos - set(cuentas)),
        "residentes_nuevos": residentes_nuevos,
        "residentes_existentes": len(residente_visto) - residentes_nuevos,
    }
    return resultado


@transaction.atomic
def aplicar(resultado, condominio, usuario=None):
    """
    Guarda todo el archivo en una transacción: si algo falla, no queda nada.
    Devuelve las cuentas creadas (para enviarles la invitación).

    `usuario`: quien confirma la importación. Cada edificio, unidad, cuenta, residente y
    cambio de rol queda en la auditoría a su nombre (Refs #27), en esta misma transacción.
    """
    if not resultado.valido:
        raise ValueError("No se puede importar un archivo con errores.")
    edificios, unidades = existentes(condominio)  # igual que validar(): lo guardado coincide con la vista previa
    cuentas, nuevas, roles_antes = {}, [], {}
    for fila in resultado.filas:
        nombre = sin_tildes(fila["edificio"])
        if nombre not in edificios:
            edificios[nombre] = Edificio.objects.create(condominio=condominio, nombre=fila["edificio"])
            registrar_cambio(usuario, condominio, edificios[nombre], None)
        unidad = unidades.get(fila.clave_unidad)
        if unidad is None:
            unidades[fila.clave_unidad] = unidad = Unidad.objects.create(
                edificio=edificios[nombre], numero=fila["numero"], piso=fila.piso, tipo=fila.tipo, alicuota=fila.alicuota
            )
            registrar_cambio(usuario, condominio, unidad, None)
        elif (unidad.piso, unidad.tipo, unidad.alicuota) != (fila.piso, fila.tipo, fila.alicuota):
            antes = datos_de(unidad)
            unidad.piso, unidad.tipo, unidad.alicuota = fila.piso, fila.tipo, fila.alicuota
            unidad.save(update_fields=["piso", "tipo", "alicuota"])
            registrar_cambio(usuario, condominio, unidad, antes)  # p. ej. la alícuota anterior y la nueva
        if not fila.correo:
            continue
        if fila.correo not in cuentas:
            persona = Usuario.objects.filter(email__iexact=fila.correo).first()
            if persona is None:
                # Clave aleatoria que nadie conoce, como en el alta de usuarios (#11): la persona
                # define la suya con la invitación (PasswordResetForm no escribe a cuentas sin clave usable).
                persona = Usuario.objects.create_user(
                    email=fila.correo,
                    password=secrets.token_urlsafe(16),
                    first_name=fila["nombre"],
                    last_name=fila["apellido"],
                    rut=fila["rut"],
                )
                nuevas.append(persona)
                registrar_cambio(usuario, condominio, persona, None)
            cuentas[fila.correo] = persona
            roles_antes[fila.correo] = roles_de(persona, condominio)
        # Igual que ResidenteForm.save(): crea o reactiva, con el tipo y la fecha del archivo.
        residente, creado = Residente.objects.get_or_create(
            usuario=cuentas[fila.correo], unidad=unidades[fila.clave_unidad], defaults={"desde": fila.desde}
        )
        antes = None if creado else datos_de(residente)
        residente.tipo, residente.desde, residente.activo = fila.tipo_residente, fila.desde, True
        residente.save()  # da el rol RESIDENTE en el condominio
        registrar_cambio(usuario, condominio, residente, antes)
    for correo, persona in cuentas.items():
        registrar_roles(usuario, condominio, persona, roles_antes[correo])
    return nuevas


def plantilla():
    """Texto de la plantilla: separada por ";" (el CSV de Excel en Chile) y con BOM para que Excel lea las tildes."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(COLUMNAS)
    escritor.writerows(EJEMPLO)
    return "﻿" + salida.getvalue()

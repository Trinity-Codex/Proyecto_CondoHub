"""Filtros de la lista de auditoría (Issue #27). Van por GET, así la URL se puede compartir."""
from django import forms

from apps.core.formularios import CampoFecha, FormularioBootstrap

from .models import RegistroAuditoria


class FiltroAuditoriaForm(FormularioBootstrap):
    desde = forms.DateField(label="Desde", required=False, widget=CampoFecha())
    hasta = forms.DateField(label="Hasta", required=False, widget=CampoFecha())
    usuario = forms.ChoiceField(label="Usuario", required=False)

    def __init__(self, *args, condominio_id, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo se ofrecen usuarios con registros en ESTE condominio: así la lista no filtra
        # nombres de personas de otros condominios. Se agrupa por id y nombre porque el
        # nombre se copió en el momento del registro y puede haber cambiado.
        usuarios = (
            RegistroAuditoria.objects.filter(condominio_id=condominio_id, usuario_id__isnull=False)
            .order_by("usuario_nombre", "usuario_id")
            .values_list("usuario_id", "usuario_nombre")
            .distinct()
        )
        self.fields["usuario"].choices = [("", "Todos")] + [(str(i), n) for i, n in usuarios]

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and desde > hasta:
            raise forms.ValidationError("La fecha «Desde» no puede ser posterior a «Hasta».")
        return datos

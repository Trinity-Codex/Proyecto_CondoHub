"""
Vistas de privacidad: aviso de privacidad (Ley 21.719).

Por ahora solo una página provisional (contrato C0, #62); el texto real llega con el
Issue #51. Es la ÚNICA vista de CondoHub sin RolRequeridoMixin: el aviso se debe poder
leer antes de iniciar sesión, por eso no pide sesión, condominio ni rol.
"""
from django.views.generic import TemplateView


class AvisoPrivacidadView(TemplateView):
    """Página pública: no muestra datos de ningún condominio, solo el texto del aviso."""

    template_name = "privacidad/provisional.html"

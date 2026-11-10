"""Tags de plantilla con los datos de la empresa (NIT, nombre).

Se registran como 'builtins' en settings.TEMPLATES, así que funcionan en
cualquier plantilla sin {% load %}, incluso en las que se renderizan con
render_to_string() para generar PDFs (donde no corren context processors).
"""
import base64
import os
from functools import lru_cache

from django import template
from django.conf import settings

register = template.Library()

# Imágenes de los PDF: locales, optimizadas y embebidas (data URI) para que
# Chromium no tenga que descargarlas de internet en cada documento.
PDF_ASSETS = {
    'logo': 'img/pdf/logo_celupro.png',
    'firma': 'img/pdf/firma_gerente.png',
}


@lru_cache(maxsize=None)
def _data_uri(relative_path):
    full_path = os.path.join(settings.BASE_DIR, 'static', relative_path)
    with open(full_path, 'rb') as fh:
        encoded = base64.b64encode(fh.read()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


@register.simple_tag
def pdf_asset(name):
    return _data_uri(PDF_ASSETS[name])


@register.simple_tag
def company_nit():
    return getattr(settings, 'COMPANY_NIT', '')


@register.simple_tag
def company_name():
    return getattr(settings, 'COMPANY_NAME', '')

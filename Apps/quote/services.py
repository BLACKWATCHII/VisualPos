"""Lógica compartida entre el módulo de cotizaciones y facturación."""
from django.utils import timezone

from .models import Quote


class QuoteNotAvailable(Exception):
    """La cotización no existe o ya no está pendiente (facturada/anulada)."""


def parse_quote_id(raw):
    try:
        value = int(str(raw or '').strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def get_pending_quote(quote_id):
    """Devuelve la cotización si está pendiente; si no, lanza QuoteNotAvailable."""
    quote = Quote.objects.filter(pk=quote_id).first()
    if quote is None:
        raise QuoteNotAvailable('La cotización seleccionada no existe.')
    if quote.status != Quote.STATUS_PENDING:
        raise QuoteNotAvailable(
            f'La cotización {quote.code} ya está {quote.get_status_display().lower()}; no se puede volver a facturar.'
        )
    return quote


def link_quote_to_invoice(quote_id, invoice):
    """Marca la cotización como facturada y la amarra a la factura.

    Debe llamarse dentro del transaction.atomic() que crea la factura: bloquea
    la fila para que dos personas no facturen la misma cotización a la vez.
    Si falla, la excepción revierte también la factura.
    """
    quote = Quote.objects.select_for_update().filter(pk=quote_id).first()
    if quote is None or quote.status != Quote.STATUS_PENDING:
        raise QuoteNotAvailable('La cotización ya fue facturada o anulada por otro usuario.')
    quote.status = Quote.STATUS_INVOICED
    quote.invoice = invoice
    quote.invoiced_at = timezone.now()
    quote.save(update_fields=['status', 'invoice', 'invoiced_at', 'updated_at'])
    return quote

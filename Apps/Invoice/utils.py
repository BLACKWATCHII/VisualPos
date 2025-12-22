from decimal import Decimal
from django.db.models import Sum
from .models import Early_Payment


def get_quotas_modified(invoice, expected_quota_amount: Decimal | None = None) -> bool:
    """Detecta si las cuotas del crédito fueron modificadas.

    Heurística: si existen cuotas (number>0) y sus montos no son uniformes con respecto
    al valor esperado por cuota, se considera "modificado" y no se debe mostrar
    "valor por cuota" fijo en el PDF.
    """
    try:
        if invoice.payment_method != 'Credito':
            return False
    except Exception:
        return False

    try:
        cuotas = list(invoice.payment_quotas.filter(number__gt=0))
    except Exception:
        return False

    if len(cuotas) <= 1:
        return False

    if expected_quota_amount is None:
        expected_quota_amount = get_valor_cuota(invoice)

    try:
        expected = Decimal(str(expected_quota_amount)).quantize(Decimal('0.01'))
    except Exception:
        expected = Decimal('0.00')

    tolerance = Decimal('0.01')
    for q in cuotas:
        try:
            amt = Decimal(str(q.amount or 0)).quantize(Decimal('0.01'))
        except Exception:
            amt = Decimal('0.00')
        if (amt - expected).copy_abs() >= tolerance:
            return True

    return False


def _get_items_subtotal(invoice) -> Decimal:
    """Subtotal de productos (sin domicilio), basado en items."""
    try:
        items = invoice.items.all()
    except Exception:
        return Decimal('0.00')

    subtotal = Decimal('0.00')
    for it in items:
        try:
            qty = Decimal(str(it.quantity or 0))
            price = Decimal(str(it.price or 0))
        except Exception:
            continue
        subtotal += qty * price

    return subtotal


def get_total_financiar(invoice):
    # Para crédito: el “total a financiar” se calcula sobre el subtotal de productos
    # (sin domicilio), y se descuenta únicamente la cuota inicial.
    # El domicilio se cobra aparte (pagado) y NO debe restarse del valor financiado.
    subtotal_productos = _get_items_subtotal(invoice)

    discount_percent = invoice.discount or Decimal('0.00')
    try:
        discount_percent = Decimal(str(discount_percent))
    except Exception:
        discount_percent = Decimal('0.00')

    if discount_percent > 0:
        subtotal_productos = subtotal_productos - (subtotal_productos * (discount_percent / Decimal('100')))

    cuota_inicial = invoice.initial_fee or Decimal('0.00')
    total_financiar = subtotal_productos - cuota_inicial

    if total_financiar < 0:
        total_financiar = Decimal('0.00')

    return total_financiar

def get_valor_cuota(invoice):
    if invoice.quotas and invoice.quotas > 0:
        return get_total_financiar(invoice) / invoice.quotas
    return Decimal('0.00')


def get_total_pagado(invoice):
    total = Early_Payment.objects.filter(
        quota__invoice=invoice
    ).aggregate(total=Sum('amount'))['total']

    return total or Decimal('0.00')


def get_saldo_pendiente(invoice):
    # Para crédito, el saldo pendiente debe reflejar SOLO lo financiado (cuotas > 0),
    # sin domicilio y sin cuota inicial (porque no hacen parte del capital financiado).
    try:
        quotas = invoice.payment_quotas.filter(number__gt=0)
    except Exception:
        return Decimal('0.00')

    saldo = Decimal('0.00')
    for q in quotas:
        try:
            saldo += (q.balance if hasattr(q, 'balance') else Decimal(str(q.amount or 0)))
        except Exception:
            continue
    if saldo < 0:
        saldo = Decimal('0.00')
    return saldo

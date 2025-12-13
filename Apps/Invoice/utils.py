from decimal import Decimal
from django.db.models import Sum
from .models import Early_Payment


def get_total_financiar(invoice):
    subtotal = invoice.total or Decimal('0.00')
    cuota_inicial = invoice.initial_fee or Decimal('0.00')
    domicilio = invoice.delivery_amount or Decimal('0.00')

    return subtotal - (cuota_inicial + domicilio)

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
    return invoice.total - get_total_pagado(invoice)

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from customer.models import Customer
from item.models import Item
from Invoice.models import Invoice


class Quote(models.Model):
    """Cotización. No mueve inventario ni cartera: solo se vuelve real cuando
    el usuario la trae a una factura (botón 'Traer cotización' al facturar)."""

    STATUS_PENDING = 'pendiente'
    STATUS_INVOICED = 'facturada'
    STATUS_CANCELED = 'anulada'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_INVOICED, 'Facturada'),
        (STATUS_CANCELED, 'Anulada'),
    ]

    number = models.PositiveIntegerField('Consecutivo', unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='quotes')
    quote_date = models.DateField('Fecha de la cotización', default=date.today)
    valid_until = models.DateField('Válida hasta', null=True, blank=True)
    discount = models.DecimalField('Descuento %', max_digits=5, decimal_places=2, default=Decimal('0'))
    delivery_amount = models.DecimalField('Domicilio', max_digits=10, decimal_places=2, default=Decimal('0'))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    notes = models.TextField('Observaciones', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotes',
        help_text='Factura en la que se usó la cotización',
    )
    invoiced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='quotes')

    class Meta:
        ordering = ['-number']
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'

    def __str__(self):
        return f'{self.code} - {self.customer}'

    @property
    def code(self):
        return f'COT-{self.number:05d}'

    @property
    def is_expired(self):
        return (
            self.status == self.STATUS_PENDING
            and self.valid_until is not None
            and self.valid_until < date.today()
        )

    @property
    def is_editable(self):
        return self.status == self.STATUS_PENDING

    @property
    def discount_amount(self):
        return (self.subtotal * self.discount / Decimal('100')).quantize(Decimal('0.01'))

    def recalculate_totals(self):
        """Misma regla que la factura de contado: (Σ cant×precio) − descuento% + domicilio."""
        subtotal = sum((line.subtotal for line in self.items.all()), Decimal('0'))
        self.subtotal = subtotal
        self.total = subtotal - self.discount_amount + (self.delivery_amount or Decimal('0'))


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='quote_items')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.price

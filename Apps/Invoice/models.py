from django.db import models
from customer.models import Customer
from item.models import Item
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal


class TransactionType(models.Model):
    consecutive = models.IntegerField('Consecutive of the transaction')
    tra_type = models.CharField('Type Transaction', max_length=50)
    iniType = models.CharField('Initial Type', max_length=50, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_types')

    def __str__(self):
        return f"{self.tra_type} - {self.consecutive}"


class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Efectivo'),
            ('credit_card', 'Tarjeta de Crédito'),
            ('debit_card', 'Tarjeta de Débito'),
            ('transfer', 'Transferencia'),
            ('credit', 'Crédito'),
        ],
        default='cash'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('paid', 'Pagada'),
            ('unpaid', 'No Pagada'),
            ('refunded', 'Reembolsada'),
            ('canceled', 'Anulada')
        ],
        default='unpaid'
    )
    transaction_type = models.ForeignKey(
        TransactionType,
        on_delete=models.CASCADE,
        related_name='invoices' 
    )
    invoice_number = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    quotas = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Invoice')

    def __str__(self):
        return f'Factura #{self.id} - {self.customer.name}'


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.quantity * self.price


class PaymentQuota(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payment_quotas'
    )
    number = models.IntegerField(help_text="Número de la cuota")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ('invoice', 'number')

    @property
    def paid_amount(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @property
    def balance(self):
        return self.amount - self.paid_amount



class Early_Payment(models.Model):
    quota = models.ForeignKey(
        PaymentQuota,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    invoice_number = models.IntegerField(null=True, blank=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='early_payments'
    )
    class Meta:
        ordering = ['-date']

    def save(self, *args, **kwargs):
        # Antes de guardar, llenare invoice_number y customer (esto es mas que todo para guardar el nombre de cliente y saber el numero de factura)
        if self.quota and (self.invoice_number is None or self.customer_id is None):
            self.invoice_number = self.quota.invoice.invoice_number
            self.customer = self.quota.invoice.customer
        super().save(*args, **kwargs)

class CanceledInvoice(models.Model):
    original_invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name="cancellation")
    canceled_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)
    transaction_type = models.ForeignKey(TransactionType, on_delete=models.PROTECT)
    cancel_number = models.CharField(max_length=20) 
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Anulación {self.cancel_number} - Factura #{self.original_invoice.id}"
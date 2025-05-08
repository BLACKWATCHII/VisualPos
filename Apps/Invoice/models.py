from django.db import models
from customer.models import Customer
from item.models import Item
from django.contrib.auth.models import User

class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0) 
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Efectivo'),
        ('credit_card', 'Tarjeta de Crédito'),
        ('debit_card', 'Tarjeta de Débito'),
        ('transfer', 'Transferencia'),
        ('credit', 'Crédito'),
    ], default='cash')
    status = models.CharField(max_length=20, choices=[
        ('paid', 'Pagada'),
        ('unpaid', 'No Pagada'),
        ('refunded', 'Reembolsada')
    ], default='unpaid')
    invoice_number = models.CharField(max_length=20, unique=True,blank=True, null=True)  
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
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payment_quotas')
    number = models.IntegerField(help_text="Número de la cuota")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    is_paid = models.BooleanField(default=True)

    class Meta:
        unique_together = ('invoice', 'number')  

class TransactionType(models.Model):
    consecutive = models.IntegerField('Consecutive of the transaction') 
    tra_type = models.CharField('Type Transaction', max_length=50)  
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_types')

    def __str__(self):
        return f"{self.tra_type} - {self.consecutive}" 
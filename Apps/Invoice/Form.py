from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer', 'invoice_date']

InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    fields=('item', 'quantity', 'price'),
    extra=1,
    can_delete=True
)

# apps/invoice/views.py

from django.shortcuts import render, redirect
from .models import Invoice
from Invoice.Form import InvoiceForm, InvoiceItem
from item.models import Item

def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        
        if form.is_valid():
            invoice = form.save(commit=False) 

            items = request.POST.getlist('item_id')
            quantities = request.POST.getlist('quantity')
            prices = request.POST.getlist('price')

            total = 0
            for quantity, price in zip(quantities, prices):
                if quantity and price:
                    total += int(quantity) * float(price)

            # Discount logic
            discount_percent = request.POST.get('discount-percent')
            if discount_percent:
                discount_percent = float(discount_percent)
                discount_amount = total * (discount_percent / 100)
                total -= discount_amount

            invoice.total = total  
            invoice.save()  

            for item_id, quantity, price in zip(items, quantities, prices):
                if item_id:
                    item = Item.objects.get(id=item_id)
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        item=item,
                        quantity=int(quantity),
                        price=float(price),
                    )

                    # Descontar inventario
                    item.Stock -= int(quantity)
                    item.save()
            return redirect('home')    
            # return redirect('invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceForm()

    items = Item.objects.all()

    return render(request, 'invoice/create_invoice.html', {
        'form': form,
        'items': items,
    })

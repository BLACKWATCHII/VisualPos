from django.shortcuts import render, redirect
from .models import Invoice
from Invoice.Form import InvoiceForm, InvoiceItem
from item.models import Item
from decimal import Decimal
import json
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

@login_required
def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        
        if form.is_valid():
            invoice = form.save(commit=False) 

            items = request.POST.getlist('item_id')
            quantities = request.POST.getlist('quantity')
            prices = request.POST.getlist('price')
            payment_method = request.POST.get('payment_method')
            status = request.POST.get('status')
            quotas = request.POST.get('quotas')
            notes = request.POST.get('notes')
            
            
            if status is None:
                status = 'Pagada'
            if payment_method == 'Credit':
                status = 'A credito'
            if quotas is None:
                quotas = 0

            invoice.quotas = quotas
            invoice.payment_method = payment_method 
            invoice.status = status
            invoice.notes = notes
            invoice.user = request.user

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


@login_required
def invoices_report(request):
    invoices = Invoice.objects.all()
    
    # total pagado
    total = Invoice.objects.filter(status='Pagada').aggregate(
        result=Sum('total')
    )
    total_payment = float(total.get('result', 0))
    # Preparar datos para JSON
    invoice_list = [{
        'id': invoice.id,
        'date': invoice.date.strftime('%Y-%m-%d %H:%M:%S'),
        'invoice_number': invoice.invoice_number,
        'customer_id': invoice.customer_id,
        'total': float(invoice.total) if isinstance(invoice.total, Decimal) else invoice.total,
        'payment_method': invoice.payment_method,
        'status': invoice.status,
        'discount': float(invoice.discount) if isinstance(invoice.discount, Decimal) else invoice.discount,
        'notes': invoice.notes,
        'quotas': invoice.quotas,
    } for invoice in invoices]

    return render(request, 'Invoice/Report_invoice.html', {
        'invoices': invoices,
        'invoices_json': json.dumps(invoice_list),
        'total_pagado': total_payment,
    })


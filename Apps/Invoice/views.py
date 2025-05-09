from django.shortcuts import render, redirect, get_object_or_404
from .models import Invoice
from Invoice.Form import InvoiceForm, InvoiceItem
from item.models import Item
from customer.models import Customer
from decimal import Decimal
import json
from django.db.models import Sum, Max
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import Http404
from datetime import timedelta, date
from .models import PaymentQuota 
from .models import TransactionType
from django.contrib import messages


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generando PDF')
    return response

@login_required
def create_type_transaction(request):
    if request.method == 'POST':
        tra_type = request.POST.get('name')  
        consecutive = request.POST.get('consecutive') 
        iniType = request.POST.get('iniType')

        # Validar que iniType no se repita
        if TransactionType.objects.filter(iniType=iniType).exists():
            Trans = TransactionType.objects.all()
            # Mostrar mensaje de error y volver a cargar la página
            message = messages.error(request, f"El valor '{iniType}' ya está en uso. Por favor, elija otro.")
            context = {
                'transactions': Trans,
                'error': message
            }
            return render(request, 'Invoice/create_transaction.html', context)

        TransactionType.objects.create(
            tra_type=tra_type,
            consecutive=consecutive,
            iniType=iniType,
            user=request.user
        )
        messages.success(request, "Transacción creada correctamente.")
        return redirect('create_transaction')
    else:
        Trans = TransactionType.objects.all()
        context = {
            'transactions': Trans
        }
        return render(request, 'Invoice/create_transaction.html', context)

from django.shortcuts import redirect

@login_required
def edit_type_transaction(request, transaction_id):
    transaction = TransactionType.objects.get(id=transaction_id)
    if request.method == 'POST':
        tra_type = request.POST.get('name')  
        consecutive = request.POST.get('consecutive') 
        iniType = request.POST.get('iniType')

        if TransactionType.objects.filter(iniType=iniType).exclude(id=transaction_id).exists():
            messages.error(request, f"La inicial que intenta editar ya está en uso. Por favor, elija otra.")
            return redirect('create_transaction')

        transaction.tra_type = tra_type
        transaction.consecutive = consecutive
        transaction.iniType = iniType
        transaction.save()
        messages.success(request, "Transacción actualizada correctamente.")
        return redirect('create_transaction')

    return redirect('create_transaction')


@login_required
def delete_type_transaction(request, transaction_id):
    transaction = get_object_or_404(TransactionType, id=transaction_id)
    transaction.delete()
    messages.success(request, "Transacción eliminada correctamente.")
    return redirect('create_transaction')


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
            if payment_method == 'credit':
                status = 'credit'

            invoice.quotas = quotas
            invoice.payment_method = payment_method 
            invoice.status = status
            invoice.notes = notes
            invoice.user = request.user

            total = 0
            for quantity, price in zip(quantities, prices):
                if quantity and price:
                    total += int(quantity) * float(price)

            # Descuento
            discount_percent = request.POST.get('discount-percent')
            if discount_percent:
                discount_percent = float(discount_percent)
                discount_amount = total * (discount_percent / 100)
                total -= discount_amount
                invoice.discount = discount_percent
            else:
                invoice.discount = 0

            invoice.total = total

            # Generar número de factura automáticamente
            last_invoice_number = Invoice.objects.aggregate(Max('invoice_number'))['invoice_number__max']
            if last_invoice_number and last_invoice_number.startswith('FV-'):
                try:
                    last_number = int(last_invoice_number.replace('FV-', ''))
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1

            invoice.invoice_number = f"FV-{new_number:02d}" 
            print(invoice)
            invoice.save()

            # payment_quota
            try:
                quotas_int = int(quotas)
            except (ValueError, TypeError):
                quotas_int = 0
            
            if payment_method == 'credit' and quotas_int > 1:
                Quota_amount = invoice.total / quotas_int
                Start_date = invoice.date or date.today()

                for i in range(quotas_int):
                    PaymentQuota.objects.create(    
                        invoice = invoice,
                        number = i+1,
                        amount = Quota_amount,
                        payment_date = Start_date + timedelta(days=30 * i),
                        is_paid = False
                    )

            for item_id, quantity, price in zip(items, quantities, prices):
                if item_id:
                    item = Item.objects.get(id=item_id)
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        item=item,
                        quantity=int(quantity),
                        price=float(price),
                    )
                    item.Stock -= int(quantity)
                    item.save()

            if request.POST.get('download') == 'pdf':
                return render_to_pdf('invoice/receipt_pdf.html', {'invoice': invoice})
            else:
                return redirect('home')
    else:
        form = InvoiceForm()

    items = Item.objects.all()

    return render(request, 'invoice/create_invoice.html', {
        'form': form,
        'items': items,
    })


@login_required
def invoices_report(request):

    invoices = Invoice.objects.select_related('customer').all()
    total_credit = Invoice.objects.filter(status='credit').aggregate(
        result_credit=Sum('total')
    )
    
    total = Invoice.objects.filter(status='Pagada').aggregate(
        result=Sum('total')
    )
    #conteo de facturas pagadas y a credito
    cont_credit = Invoice.objects.filter(status='credit').count()
    cont_pay = Invoice.objects.filter(status='Pagada').count()

    # Total de facturas pagadas y a credito
    total_credit = float(total_credit.get('result_credit') or 0)
    total_payment = float(total.get('result') or 0) 

    invoice_list = []
    for invoice in invoices:
        customer = invoice.customer 
        full_name = f"{customer.name} {customer.lastname}" if customer else ''

        invoice_list.append({
            'id': invoice.id,
            'date': invoice.date.strftime('%Y-%m-%d %H:%M:%S'),
            'invoice_number': invoice.invoice_number,
            'customer_name': customer.name if customer else '',
            'customer_last_name': customer.lastname if customer else '',
            'customer_full_name': full_name,
            'total': float(invoice.total) if isinstance(invoice.total, Decimal) else invoice.total,
            'payment_method': invoice.payment_method,
            'status': invoice.status,
            'discount': float(invoice.discount) if isinstance(invoice.discount, Decimal) else invoice.discount,
            'notes': invoice.notes,
            'quotas': invoice.quotas,
        })

    return render(request, 'Invoice/Report_invoice.html', {
        'invoices': invoices,
        'invoices_json': json.dumps(invoice_list),
        'total_pagado': total_payment,
        'total_credito': total_credit,
        'cont_pay': cont_pay,
        'cont_credit': cont_credit,
    })



@login_required
def invoice_pdf(request, invoice_id):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist:
        raise Http404("Invoice not found")
    return render_to_pdf('invoice/receipt_pdf.html', {'invoice': invoice})



#method to view quotas
@login_required
def View_quota(request):
    customer_id = request.GET.get('customer')
    estado = request.GET.get('estado')  
    customer = Customer.objects.all()
    count_quota_paid = PaymentQuota.objects.filter(is_paid=1).count()
    count_quota_unpaid = PaymentQuota.objects.filter(is_paid=0).count()
    count_quota_expired = PaymentQuota.objects.filter(payment_date__lt=date.today(), is_paid=False).count()
    quotas = PaymentQuota.objects.select_related('invoice', 'invoice__customer')

    if customer_id:
        quotas = quotas.filter(invoice__customer__id=customer_id)

    if estado == "Pagadas":
        quotas = quotas.filter(is_paid=True)
    elif estado == "Pendientes":
        quotas = quotas.filter(is_paid=False)

    context = {
        'customer': customer,
        'credits': quotas,
        'count_quota_paid': count_quota_paid,
        'count_quota_unpaid': count_quota_unpaid,
        'count_quota_expired': count_quota_expired,
    }
    return render(request, 'PaymentQuota/Payment_quota.html', context)
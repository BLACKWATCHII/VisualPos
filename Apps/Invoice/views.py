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

        if TransactionType.objects.filter(iniType=iniType).exists():
            Trans = TransactionType.objects.all()
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


from django.db import transaction
from django.contrib import messages
from datetime import timedelta, date

@login_required
def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    invoice = form.save(commit=False)

                    # Datos del POST
                    items = request.POST.getlist('item_id')
                    quantities = request.POST.getlist('quantity')
                    prices = request.POST.getlist('price')

                    payment_method = request.POST.get('payment_method')
                    status = request.POST.get('status') or 'Pagada'
                    quotas = request.POST.get('quotas')
                    notes = request.POST.get('notes')
                    discount_percent = request.POST.get('discount-percent')
                    transaction_type_id = request.POST.get('transaction_type')

                    # Ajustar estado
                    if payment_method == 'credit':
                        status = 'credit'

                    invoice.payment_method = payment_method
                    invoice.status = status
                    invoice.notes = notes
                    invoice.user = request.user
                    invoice.quotas = int(quotas) if quotas else 0

                    # Calcular total
                    total = 0
                    for qty, price in zip(quantities, prices):
                        if qty and price:
                            total += int(qty) * float(price)

                    if discount_percent:
                        discount_percent = float(discount_percent)
                        total -= total * (discount_percent / 100)
                        invoice.discount = discount_percent
                    else:
                        invoice.discount = 0

                    invoice.total = total

                    # Transacción y consecutivo
                    transaction_type = get_object_or_404(TransactionType, id=transaction_type_id)
                    invoice.invoice_number = transaction_type.consecutive
                    invoice.transaction_type = transaction_type
                    transaction_type.consecutive += 1
                    transaction_type.save()

                    invoice.save()

                    # Crear cuotas
                    if payment_method == 'credit' and invoice.quotas > 1:
                        quota_amount = invoice.total / invoice.quotas
                        start_date = invoice.date or date.today()
                        for i in range(invoice.quotas):
                            PaymentQuota.objects.create(
                                invoice=invoice,
                                number=i + 1,
                                amount=quota_amount,
                                payment_date=start_date + timedelta(days=30 * i),
                                is_paid=False
                            )

                    # Crear items de factura
                    for item_id, qty, price in zip(items, quantities, prices):
                        if item_id and qty and price:
                            item = Item.objects.get(id=item_id)
                            InvoiceItem.objects.create(
                                invoice=invoice,
                                item=item,
                                quantity=int(qty),
                                price=float(price),
                            )
                            item.Stock -= int(qty)
                            item.save()

                    if request.POST.get('download') == 'pdf':
                        return render_to_pdf('invoice/receipt_pdf.html', {'invoice': invoice})

                    return redirect('home')

            except Exception as e:
                messages.error(request, f'Error al crear la factura: {str(e)}')
        else:
            messages.error(request, 'Formulario inválido.')

    else:
        form = InvoiceForm()

    items = Item.objects.all()
    transaction_types = TransactionType.objects.all()

    return render(request, 'invoice/create_invoice.html', {
        'form': form,
        'items': items,
        'transaction_types': transaction_types,
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
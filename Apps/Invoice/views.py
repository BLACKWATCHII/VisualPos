from django.shortcuts import render, redirect, get_object_or_404
from .models import Invoice,CanceledInvoice
from Invoice.Form import InvoiceForm, InvoiceItem
from item.models import Item
from customer.models import Customer
from decimal import Decimal
import json
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import Http404
from datetime import timedelta, date
from .models import PaymentQuota,Early_Payment
from .models import TransactionType
from django.contrib import messages
from django.db import transaction
from django.contrib import messages
from datetime import timedelta, date
from django.conf import settings
from django.template.loader import render_to_string
from django.http import FileResponse
import uuid
import subprocess
import os
from functools import wraps

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generando PDF')
    return response

def render_pdf_with_puppeteer(template_src, context, filename="Factura.pdf"):
    # Rutas temporales
    html_id = str(uuid.uuid4())
    html_path = os.path.join(settings.BASE_DIR, "tmp", f"{html_id}.html")
    pdf_path = os.path.join(settings.BASE_DIR, "tmp", f"{html_id}.pdf")

    os.makedirs(os.path.dirname(html_path), exist_ok=True)

    html = render_to_string(template_src, context)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    script_path = os.path.join(settings.BASE_DIR, "pdfgen", "generate_pdf.js")

    result = subprocess.run(
    ["node", script_path, html_path, pdf_path],
    capture_output=True,
    text=True
    )

    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        raise Exception(f"Error generando PDF: {result.stderr}")


    return FileResponse(open(pdf_path, "rb"), as_attachment=True, filename=filename)

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
    sub_total = 0  
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
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

                # Calcular subtotal
                sub_total = sum([
                    float(price.replace(',', '').replace('$', ''))
                    for price in prices if price
                ])

                # Ajustar estado
                if payment_method == 'Credito':
                    status = 'Credito'

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
                if payment_method == 'Credito' and invoice.quotas > 1:
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
                    return render_pdf_with_puppeteer('invoice/receipt_pdf.html', {'invoice': invoice}, filename=f"Factura_{invoice.invoice_number}.pdf")

                return redirect('home')
        else:
            pass  # puedes manejar errores aquí si deseas
    else:
        form = InvoiceForm()

    items = Item.objects.all()
    transaction_types = TransactionType.objects.all()

    return render(request, 'invoice/create_invoice.html', {
        'form': form,
        'items': items,
        'sub_total': sub_total,  # ya no dará error
        'transaction_types': transaction_types,
    })


@login_required
def invoices_report(request):
    invoices = Invoice.objects.select_related('customer').all()

    # Totales y contadores
    total_credit = Invoice.objects.filter(payment_method='Credito').aggregate(result_credit=Sum('total'))
    total = Invoice.objects.filter(status='Pagada').aggregate(result=Sum('total'))
    cont_credit = Invoice.objects.filter(payment_method='Credito').count()
    cont_pay = Invoice.objects.filter(status='Pagada').count()

    total_credit = float(total_credit.get('result_credit') or 0)
    total_payment = float(total.get('result') or 0)

    invoice_list = []
    for invoice in invoices:
        customer = invoice.customer
        full_name = f"{customer.name} {customer.lastname}" if customer else ''

        # Verificar si hay cuotas impagas
        has_unpaid_quotas = invoice.payment_quotas.filter(is_paid=False).exists()

        invoice_list.append({
            'id': invoice.id,
            'date': invoice.date.strftime('%Y-%m-%d %I:%M %p'),
            'invoice_number': invoice.invoice_number,
            'customer_name': customer.name if customer else '',
            'customer_last_name': customer.lastname if customer else '',
            'customer_full_name': full_name,
            'customer_id': customer.id if customer else '',
            'total': float(invoice.total) if isinstance(invoice.total, Decimal) else invoice.total,
            'payment_method': invoice.payment_method,
            'status': invoice.status,
            'discount': float(invoice.discount) if isinstance(invoice.discount, Decimal) else invoice.discount,
            'notes': invoice.notes,
            'quotas': invoice.quotas,
            'has_unpaid_quotas': has_unpaid_quotas,
        })

    return render(request, 'Invoice/Report_invoice.html', {
        'invoices': invoice_list,
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
    return render_pdf_with_puppeteer('invoice/receipt_pdf.html', {'invoice': invoice},filename=f"Factura_{invoice.invoice_number}.pdf")

# Permitir iframes para la vista previa de la factura
def allow_iframe(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        if isinstance(response, HttpResponse):
            response['X-Frame-Options'] = 'SAMEORIGIN'  
        return response
    return wrapped_view

@login_required
@allow_iframe
def preview_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    return render(request, 'invoice/receipt_pdf.html', {'invoice': invoice})

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



@login_required
def View_quota_customer(request):
    customer_id = request.GET.get('customer')
    estado = request.GET.get('estado')  

    customers = Customer.objects.all()
    quotas = PaymentQuota.objects.select_related('invoice', 'invoice__customer')

    if customer_id:
        quotas = quotas.filter(invoice__customer__id=customer_id)

    base_filter = {'invoice__customer__id': customer_id} if customer_id else {}

    count_quota_paid = PaymentQuota.objects.filter(is_paid=True, **base_filter).count()
    count_quota_unpaid = PaymentQuota.objects.filter(is_paid=False, **base_filter).count()
    count_quota_expired = PaymentQuota.objects.filter(payment_date__lt=date.today(), is_paid=False, **base_filter).count()
    
    if estado == "Pagadas":
        quotas = quotas.filter(is_paid=True)
    elif estado == "Pendientes":
        quotas = quotas.filter(is_paid=False)

    context = {
        'customer': customers,
        'credits': quotas,
        'count_quota_paid': count_quota_paid,
        'count_quota_unpaid': count_quota_unpaid,
        'count_quota_expired': count_quota_expired,
    }
    return render(request, 'PaymentQuota/Payment_quota_customer.html', context)


# pay quota method
@login_required
def pay_quota(request, quota_id):
    quota = get_object_or_404(PaymentQuota, id=quota_id)

    if request.method == 'POST':
        try:
            pay_amount = Decimal(request.POST.get('amount'))
        except:
            return HttpResponseBadRequest("Importe inválido")

        if pay_amount <= 0 or pay_amount > quota.balance:
            return HttpResponseBadRequest("Importe fuera del rango válido")

        payment = Early_Payment.objects.create(quota=quota, amount=pay_amount)

        if quota.balance <= 0:
            quota.is_paid = True
            quota.save()
            quota.refresh_from_db()

        context = {
            'payment': payment,
            'quota': quota,
            'invoice': quota.invoice,
            'amount_paid': pay_amount
        }
        return render_to_pdf('PaymentQuota/Receipt_ticket.html', context)

    return HttpResponseNotAllowed(['POST'])

@login_required
def payment_history(request, customer_id=None):
    qs = Early_Payment.objects.select_related('quota__invoice__customer')
    if customer_id:
        qs = qs.filter(quota__invoice__customer__id=customer_id)
    return render(request, 'PaymentQuota/History.html', {'payments': qs})

def cancel_invoice_view(request):
    invoices = Invoice.objects.select_related('customer').all()
    return render(request, 'Invoice/Cancel_invoice.html', {'invoices': invoices})


def invoice_detail_ajax(request, invoice_id):
    print("Invoice ID:", invoice_id)
    invoice = get_object_or_404(Invoice.objects.select_related('customer'), pk=invoice_id)
    items = InvoiceItem.objects.filter(invoice=invoice).select_related('item')

    item_list = []
    for i, item in enumerate(items, start=1):
        item_list.append({
            'index': i,
            'product': item.item.Name,
            'code': item.item.id,
            'price': float(item.price),
            'quantity': item.quantity,
            'subtotal': float(item.price * item.quantity),
        })

    data = {
        'id': invoice.id,
        'status': invoice.status,
        'customer': f"{invoice.customer.name} {invoice.customer.lastname}",
        'total': float(invoice.total),
        'date': invoice.date.strftime('%Y-%m-%d'),
        'items': item_list
    }
    return JsonResponse(data)

@login_required
def canceled_invoice_pdf_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    html = render_to_string('invoice/receipt_pdf_cancel.html', {'invoice': invoice})
    return HttpResponse(html)



@login_required
def cancel_invoice_ajax(request, invoice_id):
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, id=invoice_id)

        if invoice.status == 'Anulada':
            return JsonResponse({'success': False, 'message': 'La factura ya está anulada.'})

        iniType = 'AFC' if invoice.payment_method == 'Credito' else 'AFV'
        try:
            transaction_type = TransactionType.objects.get(iniType=iniType)
        except TransactionType.DoesNotExist:
            return JsonResponse({'success': False, 'message': f"No existe un tipo de transacción con inicial '{iniType}'"})

        # Crear número de anulación
        cancel_number = f"{transaction_type.iniType}{str(transaction_type.consecutive).zfill(4)}"
        transaction_type.consecutive += 1
        transaction_type.save()

        # Actualizar factura
        invoice.status = 'Anulada'
        invoice.save()

        # Crear registro de anulación
        canceled = CanceledInvoice.objects.create(
            original_invoice=invoice,
            transaction_type=transaction_type,
            cancel_number=cancel_number,
            reason=request.POST.get('reason', ''),
            user=request.user
        )

        # Generar HTML temporal
        html_id = str(uuid.uuid4())
        html_path = os.path.join(settings.BASE_DIR, "tmp", f"{html_id}.html")
        pdf_path = os.path.join(settings.MEDIA_ROOT, f"factura_cancelada_{invoice.id}.pdf")
        os.makedirs(os.path.dirname(html_path), exist_ok=True)

        # Renderizar el HTML desde plantilla
        html_content = render_to_string('invoice/receipt_pdf_cancel.html', {
            'invoice': invoice,
            'canceled': canceled,
        })
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Ejecutar Puppeteer
        script_path = os.path.join(settings.BASE_DIR, 'pdfgen', 'generate_pdf.js')
        result = subprocess.run(
            ['node', script_path, html_path, pdf_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return JsonResponse({'success': False, 'message': 'Error generando PDF'})

        # Eliminar HTML temporal
        os.remove(html_path)

        return JsonResponse({
            'success': True,
            'message': 'Factura anulada correctamente.',
            'pdf_url': f"{settings.MEDIA_URL}factura_cancelada_{invoice.id}.pdf"
        })

    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
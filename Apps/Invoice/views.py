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
from datetime import datetime, timedelta, date
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
from customer.sendEmail import send_email_with_attachment
from dateutil.relativedelta import relativedelta

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generando PDF')
    return response

def render_pdf_with_puppeteer(template_src, context, filename="Factura.pdf"):
    html_id = str(uuid.uuid4())
    tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
    html_path = os.path.join(tmp_dir, f"{html_id}.html")
    pdf_path = os.path.join(tmp_dir, f"{html_id}.pdf")

    os.makedirs(tmp_dir, exist_ok=True)

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

        if os.path.exists(html_path): os.remove(html_path)
        if os.path.exists(pdf_path): os.remove(pdf_path)

        raise Exception(f"Error generando PDF:\n{result.stderr.strip()}")

    if not os.path.exists(pdf_path):
        raise Exception("El archivo PDF no se generó correctamente.")

    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    os.remove(html_path)

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

def calcular_fechas_cuotas(start_date, cuotas, frecuencia, tiene_cuota_inicial=False):
    """
    Calcula las fechas de pago de las cuotas según la frecuencia.
    Si tiene_cuota_inicial=True, la primera cuota financiada comienza
    en el siguiente período de pago (mensual, quincenal o semanal).
    """
    fechas = []

    # Si ya se pagó una cuota inicial, mover la fecha de inicio al próximo período
    if tiene_cuota_inicial:
        if frecuencia == 'Mensual':
            start_date += relativedelta(months=1)
        elif frecuencia == 'Quincenal':
            # Si hoy es antes del 15, empezar el 15; si ya pasó, ir al fin de mes
            if start_date.day <= 15:
                start_date = start_date.replace(day=15)
            else:
                # Ir al último día del mes
                next_month = (start_date.replace(day=1) + relativedelta(months=1))
                start_date = next_month - timedelta(days=1)
        elif frecuencia == 'Semanal':
            start_date += timedelta(weeks=1)

    # Calcular fechas según frecuencia
    if frecuencia == 'Mensual':
        for i in range(cuotas):
            fechas.append(start_date + relativedelta(months=i))

    elif frecuencia == 'Quincenal':
        current = start_date
        for i in range(cuotas):
            dia = current.day
            if dia <= 15:
                quincena = current.replace(day=15)
            else:
                quincena = (current.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
            fechas.append(quincena)
            current = quincena + timedelta(days=1)

    elif frecuencia == 'Semanal':
        for i in range(cuotas):
            fechas.append(start_date + timedelta(weeks=i))

    else:
        for i in range(cuotas):
            fechas.append(start_date + relativedelta(months=i))

    return fechas


@login_required
def create_invoice(request):
    sub_total = 0
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)

                items = request.POST.getlist('item_id')
                quantities = request.POST.getlist('quantity')
                prices = request.POST.getlist('price')

                payment_method = request.POST.get('payment_method')
                payment_frequency = request.POST.get('payment_frequency')
                quotas = request.POST.get('quotas')
                discount_percent = request.POST.get('discount-percent')
                transaction_type_id = request.POST.get('transaction_type')
                notes = request.POST.get('notes')
                status = request.POST.get('status') or 'Pagada'

                print("frecuencia de pago: " + str(payment_frequency))
                
                #  Campos nuevos de domicilio
                has_delivery = request.POST.get('has_delivery')
                delivery_amount = request.POST.get('delivery_amount')
                delivery_value = float(delivery_amount) if has_delivery and delivery_amount else 0.0

                #  Campo de cuota inicial
                initial_quota_amount = request.POST.get('initial_quota_amount')
                initial_quota_value = float(initial_quota_amount) if initial_quota_amount else 0.0
                print("Valor cuota inicial: " + str(initial_quota_value))

                # Calcular subtotal (productos)
                sub_total = sum([
                    float(price.replace(',', '').replace('$', ''))
                    for price in prices if price
                ])

                if payment_method == 'Credito':
                    status = 'Credito'

                invoice.payment_method = payment_method
                invoice.status = status
                invoice.notes = notes
                invoice.user = request.user
                invoice.quotas = int(quotas) if quotas else 0
                invoice.payment_frequency = payment_frequency
                invoice.initial_fee = initial_quota_value

                # Calcular total con descuento
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

                #  Domicilio:
                # - Si es contado: se suma al total.
                # - Si es crédito: se paga con la cuota inicial, NO se financia.
                if payment_method == 'Credito':
                    invoice.delivery_amount = delivery_value
                    # No sumamos el domicilio al total a financiar
                    total_final = total + delivery_value  # El total general sí lo incluye
                else:
                    total += delivery_value
                    invoice.delivery_amount = delivery_value
                    total_final = total

                # Guardar total completo de la venta
                invoice.total = total_final
                invoice.initial_quota_amount = initial_quota_value

                # Relacionar con tipo de transacción y actualizar consecutivo
                transaction_type = get_object_or_404(TransactionType, id=transaction_type_id)
                invoice.invoice_number = transaction_type.consecutive
                invoice.transaction_type = transaction_type
                transaction_type.consecutive += 1
                transaction_type.save()

                invoice.save()

                # Crear cuotas si aplica (solo crédito)
                if payment_method == 'Credito' and invoice.quotas > 0:
                    # 💰 Monto a financiar = total - cuota inicial (sin incluir domicilio)
                    total_financiar = total - initial_quota_value
                    cuotas_restantes = invoice.quotas
                    cuota_valor = total_financiar / cuotas_restantes

                    start_date = invoice.date or date.today()
                    fechas = calcular_fechas_cuotas(start_date, cuotas_restantes, payment_frequency,tiene_cuota_inicial=(initial_quota_value > 0))

                    # Crear cuotas financiadas
                    for i, fecha in enumerate(fechas):
                        PaymentQuota.objects.create(
                            invoice=invoice,
                            number=i + 1,
                            amount=cuota_valor,
                            payment_date=fecha,
                            is_paid=False
                        )

                    #  Registrar cuota inicial (incluyendo el domicilio)
                    initial_payment_total = initial_quota_value + delivery_value
                    if initial_payment_total > 0:
                        PaymentQuota.objects.create(
                            invoice=invoice,
                            number=0,
                            amount=initial_payment_total,
                            payment_date=date.today(),
                            is_paid=True
                        )

                # Crear items y actualizar stock
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

                # Generar PDF si se pidió
                if request.POST.get('download') == 'pdf':
                    return render_pdf_with_puppeteer(
                        'invoice/receipt_pdf.html',
                        {'invoice': invoice,
                        'sub_total': sub_total,
                        'total_restante': invoice.total - (invoice.delivery_amount or 0) - (invoice.initial_fee or 0),
                         },
                        filename=f"Factura_{invoice.invoice_number}.pdf"
                    )

                return redirect('home')
        else:
            pass
    else:
        form = InvoiceForm()

    items = Item.objects.all()
    transaction_types = TransactionType.objects.all()

    return render(request, 'invoice/create_invoice.html', {
        'form': form,
        'items': items,
        'sub_total': sub_total,
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
        email = customer.email if customer else ''
        full_name = f"{customer.name} {customer.lastname}" if customer else ''

        total_factura = float(invoice.total or 0)
        delivery = float(invoice.delivery_amount or 0)
        initial_fee = float(invoice.initial_fee or 0)

        if invoice.payment_method == 'Credito':
            total_restante = total_factura - delivery - initial_fee
        else:
            total_restante = total_factura

        print(f"Factura {invoice.invoice_number} - Total: {total_factura} - Restante: {total_restante}")

        # Verificar si hay cuotas pagas
        has_unpaid_quotas = invoice.payment_quotas.filter(is_paid=False).exists()
        invoice_list.append({
            'id': invoice.id,
            'date': invoice.date.strftime('%Y-%m-%d'),
            'invoice_number': invoice.invoice_number,
            'customer_name': customer.name if customer else '',
            'customer_last_name': customer.lastname if customer else '',
            'customer_full_name': full_name,
            'customer_email': email,
            'customer_id': customer.id if customer else '',
            'total': float(invoice.total) if isinstance(invoice.total, Decimal) else invoice.total,
            'payment_method': invoice.payment_method,
            'status': invoice.status,
            'discount': float(invoice.discount) if isinstance(invoice.discount, Decimal) else invoice.discount,
            'notes': invoice.notes,
            'quotas': invoice.quotas,
            'has_unpaid_quotas': has_unpaid_quotas,
            'total_restante': total_restante,
            'delivery_amount': delivery,
            'initial_fee': initial_fee,
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
    return render(request, 'invoice/receipt_pdf.html', {'invoice': invoice, 
                                                        'total_restante': invoice.total - (invoice.delivery_amount or 0) - (invoice.initial_fee or 0),
                                                        'sub_total': invoice.total - (invoice.delivery_amount or 0)})


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
    invoice_id = request.GET.get('numero_factura')
    estado = request.GET.get('estado')

    customers = Customer.objects.all()
    quotas = PaymentQuota.objects.select_related('invoice', 'invoice__customer')

    if customer_id:
        quotas = quotas.filter(invoice__customer__id=customer_id)

    if invoice_id:
        quotas = quotas.filter(invoice__id=invoice_id)

    # Filtro base para contadores
    base_filter = {}
    if customer_id:
        base_filter['invoice__customer__id'] = customer_id
    if invoice_id:
        base_filter['invoice__id'] = invoice_id

    count_quota_paid = PaymentQuota.objects.filter(is_paid=True, **base_filter).count()
    count_quota_unpaid = PaymentQuota.objects.filter(is_paid=False, **base_filter).count()
    count_quota_expired = PaymentQuota.objects.filter(payment_date__lt=date.today(), is_paid=False, **base_filter).count()

    # Filtro por estado de la cuota
    if estado == "Pagadas":
        quotas = quotas.filter(is_paid=True)
    elif estado == "Pendientes":
        quotas = quotas.filter(is_paid=False)

    # Obtener facturas del cliente para el select
    invoices = Invoice.objects.all()
    if customer_id:
        invoices = invoices.filter(customer__id=customer_id)

    context = {
        'customer': customers,
        'credits': quotas,
        'count_quota_paid': count_quota_paid,
        'count_quota_unpaid': count_quota_unpaid,
        'count_quota_expired': count_quota_expired,
        'invoice': invoices,
    }
    return render(request, 'PaymentQuota/Payment_quota_customer.html', context)


def render_pdf_inline_with_puppeteer(template_src, context, filename="ReciboPagoCuota.pdf", return_path=False):
    html_id = str(uuid.uuid4())
    tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
    html_path = os.path.join(tmp_dir, f"{html_id}.html")
    pdf_path = os.path.join(tmp_dir, f"{html_id}.pdf")

    os.makedirs(tmp_dir, exist_ok=True)

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
        if os.path.exists(html_path): os.remove(html_path)
        if os.path.exists(pdf_path): os.remove(pdf_path)
        raise Exception(f"Error generando PDF:\n{result.stderr.strip()}")

    if not os.path.exists(pdf_path):
        raise Exception("El archivo PDF no se generó correctamente.")

    os.remove(html_path)

    if return_path:
        # Devolvemos solo la ruta para que la vista pueda enviarlo por correo
        return pdf_path

    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response

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

        context = {
            'payment': payment,
            'quota': quota,
            'invoice': quota.invoice,
            'amount_paid': pay_amount
        }

        pdf_path = render_pdf_inline_with_puppeteer(
            'PaymentQuota/Receipt_ticket.html',
            context,
            filename="ReciboPagoCuota.pdf",
            return_path=True
        )

        send_email_with_attachment(
            destinatario=quota.invoice.customer.email,
            asunto="✅ Confirmación de pago - Recibo incluido",
            contenido_texto=f"""
        Hola {quota.invoice.customer.name},

        ¡Tu pago ha sido procesado exitosamente! 

        📄 En este correo encontrarás tu recibo de pago adjunto para tus registros.

        Detalles del pago:
        • Estado: Confirmado
        • Fecha: {datetime.now().strftime('%d/%m/%Y')}
        • Referencia: #{quota.invoice.id}

        Si tienes alguna pregunta sobre tu pago, no dudes en contactarnos respondiendo a este correo.

        ¡Gracias por tu confianza!

        Saludos cordiales,
        El equipo de [Nombre de tu empresa]
            """.strip(),
            contenido_html=f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">
                        ✅ Pago Confirmado
                    </h1>
                </div>
                
                <div style="padding: 30px; background-color: white; margin: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <p style="font-size: 18px; color: #333; margin-bottom: 20px;">
                        Hola <strong style="color: #667eea;">{quota.invoice.customer.name}</strong>,
                    </p>
                    
                    <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 15px; margin: 20px 0;">
                        <p style="color: #155724; margin: 0; font-weight: 600;">
                            🎉 ¡Tu pago ha sido procesado exitosamente!
                        </p>
                    </div>
                    
                    <p style="color: #666; line-height: 1.6; margin-bottom: 25px;">
                        📄 En este correo encontrarás tu <strong>recibo de pago adjunto</strong> para tus registros.
                    </p>
                    
                    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
                        <h3 style="color: #333; margin: 0 0 15px 0; font-size: 16px;">📋 Detalles del pago</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">Estado:</td>
                                <td style="padding: 8px 0; color: #28a745; font-weight: 600;">✅ Confirmado</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">Fecha:</td>
                                <td style="padding: 8px 0; color: #333;">{datetime.now().strftime('%d/%m/%Y')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">Referencia:</td>
                                <td style="padding: 8px 0; color: #333;">#{quota.invoice.id}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #e3f2fd; border-radius: 8px; padding: 20px; margin: 25px 0;">
                        <p style="color: #1565c0; margin: 0; font-size: 14px; line-height: 1.5;">
                            💬 <strong>¿Necesitas ayuda?</strong><br>
                            Si tienes alguna pregunta sobre tu pago, no dudes en contactarnos respondiendo a este correo.
                        </p>
                    </div>
                    
                    <p style="color: #333; font-size: 16px; margin-top: 30px;">
                        ¡Gracias por tu confianza! 🙏
                    </p>
                    
                    <p style="color: #666; font-size: 14px; margin-bottom: 0;">
                        Saludos cordiales,<br>
                        <strong style="color: #667eea;">El equipo de BerserkerDev</strong>
                    </p>
                </div>
                
                <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                    <p style="margin: 0;">Este correo fue enviado automáticamente. Por favor, no respondas a esta dirección.</p>
                </div>
            </div>
            """,
            attachment_path=pdf_path,
            attachment_name="ReciboPagoCuota.pdf"
        )

        return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')

    return HttpResponseNotAllowed(['POST'])

@login_required
def download_quota_receipt(request, quota_id):
    quota = get_object_or_404(PaymentQuota, pk=quota_id)

    # Obtenemos el último pago asociado a esta cuota
    payment = quota.payments.order_by('-date').first()
    if not payment:
        return HttpResponse("No hay pagos para esta cuota.", status=404)

    context = {
        'quota': quota,
        'payment': payment
    }

    return render_pdf_with_puppeteer(
        'PaymentQuota/Receipt_ticket.html',
        context,
        filename=f"Recibo_Cuota_{quota.id}.pdf"
    )


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

        
        cancel_number = f"{transaction_type.iniType}{str(transaction_type.consecutive).zfill(4)}"
        transaction_type.consecutive += 1
        transaction_type.save()

        
        invoice.status = 'Anulada'
        invoice.save()

        for detail in invoice.items.all():
            item = detail.item
            item.Stock += detail.quantity
            item.save()

        
        canceled = CanceledInvoice.objects.create(
            original_invoice=invoice,
            transaction_type=transaction_type,
            cancel_number=cancel_number,
            reason=request.POST.get('reason', ''),
            user=request.user
        )

        
        html_id = str(uuid.uuid4())
        html_path = os.path.join(settings.BASE_DIR, "tmp", f"{html_id}.html")
        pdf_path = os.path.join(settings.MEDIA_ROOT, f"factura_cancelada_{invoice.id}.pdf")
        os.makedirs(os.path.dirname(html_path), exist_ok=True)

        
        html_content = render_to_string('invoice/receipt_pdf_cancel.html', {
            'invoice': invoice,
            'canceled': canceled,
        })
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        
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

        
        os.remove(html_path)

        return JsonResponse({
            'success': True,
            'message': 'Factura anulada correctamente.',
            'pdf_url': f"{settings.MEDIA_URL}factura_cancelada_{invoice.id}.pdf"
        })

    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)




@login_required
def send_invoice_simple(request, invoice_id):
    print(f"🎯 === INICIO ENVÍO FACTURA ID: {invoice_id} ===")
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
    
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if not invoice.customer:
            return JsonResponse({'success': False, 'message': 'La factura no tiene cliente asignado.'})
        
        if not invoice.customer.email:
            return JsonResponse({'success': False, 'message': 'El cliente no tiene un correo electrónico registrado.'})
        
        print("📄 Generando PDF...")
        pdf_path = None
        try:
            pdf_path = generate_temp_invoice_pdf_safe(invoice)
            print(f"✅ PDF generado: {pdf_path}")
        except Exception as pdf_error:
            print(f"❌ Error generando PDF: {pdf_error}")
            return JsonResponse({'success': False, 'message': f'Error generando PDF: {str(pdf_error)}'})
        
        print("📧 Enviando email...")
        try:
            email_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Factura #{invoice.invoice_number}</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; background-color: #f5f7fa;">
                <div style="max-width: 650px; margin: 0 auto; padding: 40px 20px;">
                    
                    <!-- Header con Logo -->
                    <div style="background: #ffffff; border-radius: 16px 16px 0 0; padding: 40px 30px; text-align: center; border-bottom: 3px solid #2563eb;">
                        <img src="https://raw.githubusercontent.com/Kevin25DC/celupro-assets/refs/heads/main/logo%20de%20prueba%20dos.png" alt="Logo" style="max-width: 180px; height: auto; margin-bottom: 25px;">
                        <h1 style="color: #1e293b; margin: 0; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;">
                            Factura Electrónica
                        </h1>
                        <p style="color: #64748b; margin: 10px 0 0; font-size: 16px;">
                            N° {invoice.invoice_number}
                        </p>
                    </div>
                    
                    <!-- Contenido Principal -->
                    <div style="background: #ffffff; padding: 40px 30px;">
                        
                        <!-- Saludo -->
                        <div style="margin-bottom: 30px;">
                            <p style="color: #334155; font-size: 18px; margin: 0 0 8px; font-weight: 500;">
                                Estimado/a {invoice.customer.name},
                            </p>
                            <p style="color: #64748b; font-size: 15px; line-height: 1.6; margin: 0;">
                                Le enviamos su factura correspondiente a la compra realizada. Puede encontrarla adjunta a este correo en formato PDF.
                            </p>
                        </div>
                        
                        <!-- Card de Factura -->
                        <div style="background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); border-radius: 12px; padding: 30px; margin: 30px 0; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.15);">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="text-align: center;">
                                        <div style="background: rgba(255,255,255,0.15); border-radius: 50%; width: 60px; height: 60px; margin: 0 auto 20px; display: inline-flex; align-items: center; justify-content: center;">
                                            <span style="font-size: 28px;">📄</span>
                                        </div>
                                        <h2 style="color: #ffffff; margin: 0 0 10px; font-size: 22px; font-weight: 600;">
                                            Factura Adjunta
                                        </h2>
                                        <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 15px;">
                                            Su documento está listo para descargar
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        
                        <!-- Información Adicional -->
                        <div style="background: #f8fafc; border-left: 4px solid #2563eb; border-radius: 8px; padding: 20px 24px; margin: 30px 0;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <p style="color: #334155; margin: 0 0 12px; font-size: 15px; font-weight: 600;">
                                            📌 Información Importante
                                        </p>
                                        <p style="color: #64748b; font-size: 14px; line-height: 1.6; margin: 0;">
                                            • Conserve esta factura para sus registros contables<br>
                                            • El documento adjunto tiene validez fiscal<br>
                                            • Ante cualquier consulta, estamos a su disposición
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        
                        <!-- Agradecimiento -->
                        <div style="text-align: center; margin: 35px 0 25px;">
                            <p style="color: #334155; font-size: 15px; line-height: 1.6; margin: 0;">
                                Gracias por confiar en nosotros.<br>
                                Valoramos su preferencia y quedamos a su disposición.
                                https://celuproco.com.co/
                            </p>
                        </div>
                        
                        <!-- Divisor -->
                        <div style="height: 1px; background: linear-gradient(90deg, transparent, #e2e8f0, transparent); margin: 30px 0;"></div>
                        
                        <!-- Contacto -->
                        <div style="text-align: center;">
                            <p style="color: #64748b; font-size: 14px; margin: 0 0 15px; font-weight: 500;">
                                ¿Necesita ayuda?
                            </p>
                            <p style="color: #94a3b8; font-size: 13px; line-height: 1.6; margin: 0;">
                                Contáctenos en cualquier momento<br>
                                Estamos disponibles para atenderle 
                            </p>
                        </div>
                    </div>
                    
                    <!-- Footer -->
                    <div style="background: #1e293b; border-radius: 0 0 16px 16px; padding: 30px; text-align: center;">
                        <p style="color: #94a3b8; font-size: 13px; line-height: 1.6; margin: 0 0 12px;">
                            Este correo fue generado automáticamente por nuestro sistema de facturación.<br>
                            Por favor, no responda a este mensaje.
                        </p>
                        <div style="height: 1px; background: rgba(148, 163, 184, 0.2); margin: 20px auto; max-width: 200px;"></div>
                        <p style="color: #64748b; font-size: 12px; margin: 0;">
                            © 2025 Todos los derechos reservados - BerserkerDev - http://www.berserkerdev.com/
                        </p>
                    </div>
                    
                </div>
            </body>
            </html>
            """
            
            asunto = f"Factura #{invoice.invoice_number} - {invoice.customer.name} {invoice.customer.lastname}"
            success = send_email_with_attachment(
                destinatario=invoice.customer.email,
                asunto=asunto,
                contenido_texto="Adjuntamos su factura en PDF.",
                contenido_html=email_content,
                attachment_path=pdf_path
            )
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'Factura enviada correctamente a {invoice.customer.email}'
                })
            else:
                import traceback
                print(traceback.format_exc())
                return JsonResponse({'success': False, 'message': 'Error al enviar el correo electrónico.'})
                
        except Exception as email_error:
            return JsonResponse({'success': False, 'message': f'Error enviando email: {str(email_error)}'})
        finally:
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    print(" PDF temporal eliminado")
                except:
                    print("No se pudo eliminar el PDF temporal")

    except Exception as e:
        import traceback
        print(f" Error general: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})
    finally:
        print("🏁 === FIN ENVÍO FACTURA ===")

def generate_temp_invoice_pdf_safe(invoice):
    """
    Versión segura de generación de PDF
    """
    print("📄 Iniciando generación de PDF...")
    
    # Crear directorio tmp
    tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"📁 Directorio tmp: {tmp_dir}")
    
    # Generar nombres únicos
    html_id = str(uuid.uuid4())
    html_path = os.path.join(tmp_dir, f"{html_id}.html")
    pdf_path = os.path.join(tmp_dir, f"{html_id}.pdf")
    
    print(f"📝 HTML path: {html_path}")
    print(f"📄 PDF path: {pdf_path}")
    
    try:
        html_content = render_to_string('invoice/receipt_pdf.html', {'invoice': invoice})
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        script_path = os.path.join(settings.BASE_DIR, "pdfgen", "generate_pdf.js")
        if not os.path.exists(script_path):
            raise Exception(f"Script PDF no encontrado: {script_path}")
        
        print(f" Script path: {script_path}")
        
        # Ejecutar script
        print("⚙️ Ejecutando script de PDF...")
        result = subprocess.run(
            ["node", script_path, html_path, pdf_path],
            capture_output=True,
            text=True,
            timeout=25  
        )
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f" STDOUT: {result.stdout}")
        if result.stderr:
            print(f" STDERR: {result.stderr}")
        
        if result.returncode != 0:
            raise Exception(f"Error en script PDF: {result.stderr.strip()}")
        
        if not os.path.exists(pdf_path):
            raise Exception("PDF no se generó correctamente")
        
        pdf_size = os.path.getsize(pdf_path)
        print(f" PDF generado correctamente ({pdf_size} bytes)")
        
        # Limpiar HTML
        if os.path.exists(html_path):
            os.remove(html_path)
        
        return pdf_path
        
    except subprocess.TimeoutExpired:
        # Limpieza
        if os.path.exists(html_path):
            os.remove(html_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise Exception("Timeout generando PDF")
        
    except Exception as e:
        # Limpieza en caso de error
        if os.path.exists(html_path):
            os.remove(html_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise e
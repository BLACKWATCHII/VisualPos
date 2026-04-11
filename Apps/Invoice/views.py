from django.shortcuts import render, redirect, get_object_or_404
from .models import Invoice,CanceledInvoice
from Invoice.Form import InvoiceForm, InvoiceItem
from item.models import Item
from customer.models import Customer
from decimal import Decimal
import json
from django.db.models import Sum, Q
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
import re
import unicodedata
from functools import wraps
from customer.sendEmail import send_email_with_attachment
from dateutil.relativedelta import relativedelta
from .utils import get_total_pagado, get_total_financiar, get_valor_cuota, get_saldo_pendiente, get_quotas_modified
from django.views.decorators.http import require_GET, require_POST
from django.db.models.functions import TruncDate
import threading
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme


def _norm_text(value) -> str:
    text = str(value or '')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return text.strip().lower()


def _is_credit_invoice(invoice: Invoice) -> bool:
    pm = _norm_text(getattr(invoice, 'payment_method', ''))
    st = _norm_text(getattr(invoice, 'status', ''))
    return (pm in ('credit', 'credito')) or ('credit' in pm) or ('credito' in pm) or ('credito' in st)


def _parse_decimal(value, default=Decimal('0.00')) -> Decimal:
    if value is None:
        return default
    try:
        s = str(value).strip()
        if not s:
            return default
        s = s.replace('$', '').replace(',', '').replace(' ', '')
        return Decimal(s)
    except Exception:
        return default


def _parse_int(value, default=0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


@login_required
def edit_invoice(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects
        .select_related('customer', 'transaction_type')
        .prefetch_related('items', 'payment_quotas', 'payment_quotas__payments'),
        pk=invoice_id
    )

    items = Item.objects.all()
    transaction_types = TransactionType.objects.all()

    if request.method == 'GET':
        form = InvoiceForm(instance=invoice)
        credit = _is_credit_invoice(invoice)
        quotas = list(invoice.payment_quotas.filter(number__gt=0).order_by('number')) if credit else []
        total_financiar = get_total_financiar(invoice) if credit else None
        total_pagado = get_total_pagado(invoice) if credit else None

        return render(request, 'Invoice/edit_invoice/editar_factura.html', {
            'form': form,
            'invoice': invoice,
            'items': items,
            'invoice_items': list(invoice.items.select_related('item').all()),
            'transaction_types': transaction_types,
            'is_credit': credit,
            'quotas_list': quotas,
            'total_financiar': total_financiar,
            'total_pagado': total_pagado,
        })

    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])

    # =============================
    # POST: actualizar factura
    # =============================
    with transaction.atomic():
        form = InvoiceForm(request.POST, instance=invoice)
        if not form.is_valid():
            messages.error(request, 'Formulario inve1lido. Verifique los datos del cliente.')
            return redirect('edit_invoice', invoice_id=invoice.id)

        new_payment_method = (request.POST.get('payment_method') or '').strip()
        new_notes = request.POST.get('notes') or request.POST.get('subject') or ''
        discount_percent = _parse_decimal(request.POST.get('discount-percent'), Decimal('0.00'))
        if discount_percent < 0:
            discount_percent = Decimal('0.00')
        if discount_percent > 100:
            discount_percent = Decimal('100.00')

        # Domicilio
        has_delivery = request.POST.get('has_delivery')
        delivery_value = _parse_decimal(request.POST.get('delivery_amount'), Decimal('0.00')) if has_delivery else Decimal('0.00')
        if delivery_value < 0:
            delivery_value = Decimal('0.00')

        # Cuota inicial
        initial_quota_value = _parse_decimal(request.POST.get('initial_quota_amount'), Decimal('0.00'))
        if initial_quota_value < 0:
            initial_quota_value = Decimal('0.00')

        # Transaccif3n (NO cambiar consecutivo)
        transaction_type_id = request.POST.get('transaction_type')
        if transaction_type_id:
            try:
                invoice.transaction_type = TransactionType.objects.get(id=transaction_type_id)
            except TransactionType.DoesNotExist:
                pass

        # =============================
        # Items y stock: calcular diff
        # =============================
        old_qty_by_item_id = {}
        for it in invoice.items.all():
            try:
                old_qty_by_item_id[it.item_id] = old_qty_by_item_id.get(it.item_id, 0) + int(it.quantity or 0)
            except Exception:
                continue

        posted_item_ids = request.POST.getlist('item_id')
        posted_quantities = request.POST.getlist('quantity')
        posted_prices = request.POST.getlist('price')

        new_lines = []
        new_qty_by_item_id = {}
        sub_total = Decimal('0.00')

        for item_id, qty, price in zip(posted_item_ids, posted_quantities, posted_prices):
            if not item_id:
                continue
            q = _parse_int(qty, 0)
            p = _parse_decimal(price, Decimal('0.00'))
            if q <= 0:
                continue
            if p < 0:
                p = Decimal('0.00')
            new_lines.append((int(item_id), q, p))
            new_qty_by_item_id[int(item_id)] = new_qty_by_item_id.get(int(item_id), 0) + q
            sub_total += (Decimal(q) * p)

        if not new_lines:
            messages.error(request, 'Debe incluir al menos un producto/servicio.')
            return redirect('edit_invoice', invoice_id=invoice.id)

        # Aplicar descuento sobre productos (no incluye domicilio)
        total_productos = sub_total
        if discount_percent and discount_percent > 0:
            total_productos = total_productos - (total_productos * (discount_percent / Decimal('100')))
        if total_productos < 0:
            total_productos = Decimal('0.00')

        # Determinar si la factura es/cre9dito
        next_is_credit = _norm_text(new_payment_method) in ('credito', 'credit')
        current_is_credit = _is_credit_invoice(invoice)

        # Si intenta cambiar modalidad, ser conservador si hay historial de pagos
        if current_is_credit != next_is_credit:
            has_any_payments = Early_Payment.objects.filter(quota__invoice=invoice).exists()
            has_any_quotas = invoice.payment_quotas.filter(number__gt=0).exists()
            if has_any_payments or has_any_quotas:
                messages.error(request, 'No se puede cambiar el me9todo de pago porque la factura tiene cuotas/pagos registrados.')
                return redirect('edit_invoice', invoice_id=invoice.id)

        # =============================
        # Ajustar stock segfan diferencias
        # =============================
        all_item_ids = set(old_qty_by_item_id.keys()) | set(new_qty_by_item_id.keys())
        if all_item_ids:
            stock_items = list(Item.objects.select_for_update().filter(id__in=all_item_ids))
            stock_map = {i.id: i for i in stock_items}

            for item_id in all_item_ids:
                old_q = int(old_qty_by_item_id.get(item_id, 0) or 0)
                new_q = int(new_qty_by_item_id.get(item_id, 0) or 0)
                diff = new_q - old_q
                if diff == 0:
                    continue
                item = stock_map.get(item_id)
                if not item:
                    messages.error(request, 'Producto inve1lido en la factura.')
                    return redirect('edit_invoice', invoice_id=invoice.id)
                # Si diff > 0, se necesita me1s stock; si diff < 0, se devuelve stock.
                new_stock = int(item.Stock or 0) - diff
                if new_stock < 0:
                    messages.error(request, f'Stock insuficiente para {item.Name}. Disponible: {item.Stock}')
                    return redirect('edit_invoice', invoice_id=invoice.id)
                item.Stock = new_stock
                item.save()

        # Reemplazar items
        invoice.items.all().delete()
        for item_id, q, p in new_lines:
            item = Item.objects.get(id=item_id)
            InvoiceItem.objects.create(
                invoice=invoice,
                item=item,
                quantity=q,
                price=p,
            )

        # =============================
        # Guardar encabezado factura
        # =============================
        invoice = form.save(commit=False)
        invoice.notes = new_notes
        invoice.discount = discount_percent
        invoice.delivery_amount = delivery_value
        invoice.initial_fee = initial_quota_value

        if next_is_credit:
            invoice.payment_method = 'Credito'
            invoice.status = 'Credito'
            invoice.payment_frequency = request.POST.get('payment_frequency')
            invoice.quotas = _parse_int(request.POST.get('quotas'), 0)
        else:
            # Contado
            # Guardar el valor seleccionado (Efectivo/Transferencia/etc). Cualquier valor != Credito se trata como contado.
            invoice.payment_method = new_payment_method or (invoice.payment_method or 'Contado')
            invoice.status = request.POST.get('status') or invoice.status or 'Pagada'
            invoice.payment_frequency = None
            invoice.quotas = None

        invoice.total = (total_productos + delivery_value).quantize(Decimal('0.01'))
        invoice.save()

        # =============================
        # Validaciones y actualizacif3n de cuotas (si cre9dito)
        # =============================
        if next_is_credit:
            total_financiar = get_total_financiar(invoice)
            total_pagado = get_total_pagado(invoice)

            if total_financiar < total_pagado:
                messages.error(request, 'No se puede disminuir el monto a financiar por debajo de lo ya pagado.')
                transaction.set_rollback(True)
                return redirect('edit_invoice', invoice_id=invoice.id)

            # Cuotas existentes
            financed_quotas = list(invoice.payment_quotas.filter(number__gt=0).order_by('number'))
            prev_count = len(financed_quotas)

            locked_quota_ids = set()
            for q in financed_quotas:
                if q.is_paid or (q.paid_amount and q.paid_amount > 0):
                    locked_quota_ids.add(q.id)

            desired_count = _parse_int(request.POST.get('quotas'), len(financed_quotas))
            if desired_count < 0:
                desired_count = 0

            # No permitir quedar con menos cuotas que las bloqueadas
            if desired_count < len([q for q in financed_quotas if q.id in locked_quota_ids]):
                messages.error(request, 'No puede reducir el nfamero de cuotas por debajo de las cuotas ya pagadas/parciales.')
                transaction.set_rollback(True)
                return redirect('edit_invoice', invoice_id=invoice.id)

            # Ajustar cantidad de cuotas (agregar/eliminar solo no bloqueadas, desde el final)
            if desired_count < len(financed_quotas):
                to_remove = len(financed_quotas) - desired_count
                removable = [q for q in reversed(financed_quotas) if q.id not in locked_quota_ids]
                for q in removable[:to_remove]:
                    q.delete()

            elif desired_count > len(financed_quotas):
                add_n = desired_count - len(financed_quotas)
                payment_frequency = request.POST.get('payment_frequency') or invoice.payment_frequency or 'Mensual'
                start_date = date.today()
                try:
                    last = invoice.payment_quotas.filter(number__gt=0).order_by('-number').first()
                    if last and last.payment_date:
                        start_date = last.payment_date
                except Exception:
                    pass

                # Generar fechas nuevas (a partir de la faltima fecha conocida)
                fechas = calcular_fechas_cuotas(start_date, add_n, payment_frequency, tiene_cuota_inicial=False)
                # Ojo: usar max manual para el prf3ximo nfamero.
                max_num = 0
                try:
                    max_obj = invoice.payment_quotas.filter(number__gt=0).order_by('-number').first()
                    max_num = int(max_obj.number) if max_obj else 0
                except Exception:
                    max_num = 0

                for i, fecha in enumerate(fechas, start=1):
                    PaymentQuota.objects.create(
                        invoice=invoice,
                        number=max_num + i,
                        amount=Decimal('0.00'),
                        payment_date=fecha,
                        is_paid=False
                    )

            # Ahora actualizar montos/fechas segfan POST
            quota_ids = request.POST.getlist('quota_id')
            quota_amounts = request.POST.getlist('quota_amount')
            quota_dates = request.POST.getlist('quota_date')

            # Normalizar inputs
            posted_map = {}
            for qid, amt, dt in zip(quota_ids, quota_amounts, quota_dates):
                qid_i = _parse_int(qid, 0)
                if not qid_i:
                    continue
                posted_map[qid_i] = {
                    'amount': _parse_decimal(amt, Decimal('0.00')),
                    'date': dt,
                }

            # Refrescar cuotas tras cambios de cantidad
            financed_quotas = list(invoice.payment_quotas.filter(number__gt=0).order_by('number'))

            # Auto-repartir montos cuando cambif3 el nfamero de cuotas o cuando faltan montos en el POST.
            # Regla: la suma de cuotas (number>0) debe ser EXACTAMENTE total_financiar.
            locked_total = sum((q.amount or Decimal('0.00')) for q in financed_quotas if q.id in locked_quota_ids)
            remaining = (total_financiar - locked_total)
            if remaining < 0:
                remaining = Decimal('0.00')

            unlocked = [q for q in financed_quotas if q.id not in locked_quota_ids]
            unlocked_ids = {q.id for q in unlocked}
            missing_any = any(qid not in posted_map for qid in unlocked_ids)
            if (desired_count != prev_count) or missing_any:
                if unlocked:
                    per = (remaining / Decimal(len(unlocked))).quantize(Decimal('0.01'))
                    # Ajuste por redondeo en la faltima cuota
                    running = Decimal('0.00')
                    for idx, q in enumerate(unlocked):
                        if idx < len(unlocked) - 1:
                            q.amount = per
                            running += per
                        else:
                            q.amount = (remaining - running).quantize(Decimal('0.01'))
                        if q.amount < (q.paid_amount or Decimal('0.00')):
                            messages.error(request, f'La cuota #{q.number} no puede ser menor a lo ya pagado en esa cuota.')
                            transaction.set_rollback(True)
                            return redirect('edit_invoice', invoice_id=invoice.id)
                        q.save()

            # Aplicar cambios
            for q in financed_quotas:
                data = posted_map.get(q.id)
                if not data:
                    continue

                # No permitir bajar monto por debajo de lo ya pagado en esa cuota
                if data['amount'] < (q.paid_amount or Decimal('0.00')):
                    messages.error(request, f'La cuota #{q.number} no puede ser menor a lo ya pagado en esa cuota.')
                    transaction.set_rollback(True)
                    return redirect('edit_invoice', invoice_id=invoice.id)

                if (q.id in locked_quota_ids) and (data['amount'] != q.amount):
                    messages.error(request, f'La cuota #{q.number} ya tiene pagos y no se puede modificar su monto.')
                    transaction.set_rollback(True)
                    return redirect('edit_invoice', invoice_id=invoice.id)

                if q.id not in locked_quota_ids:
                    q.amount = data['amount'].quantize(Decimal('0.01'))
                    try:
                        if data['date']:
                            q.payment_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                    except Exception:
                        pass
                    q.save()

            # Validar que las cuotas cubran exactamente el monto financiado
            sum_quotas = invoice.payment_quotas.filter(number__gt=0).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            sum_quotas = Decimal(str(sum_quotas))

            if sum_quotas.quantize(Decimal('0.01')) != total_financiar.quantize(Decimal('0.01')):
                messages.error(
                    request,
                    f'Las cuotas financiadas deben sumar exactamente {total_financiar:.2f}. Actualmente suman {sum_quotas:.2f}.'
                )
                transaction.set_rollback(True)
                return redirect('edit_invoice', invoice_id=invoice.id)

        messages.success(request, 'Factura actualizada correctamente.')
        url = reverse('edit_invoice', kwargs={'invoice_id': invoice.id})
        return HttpResponseRedirect(f"{url}?saved=1&print=1")

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
            payment_method = request.POST.get('payment_method')
            if payment_method == 'Credito':
                return create_invoice_credit(request, form)
            else: 
                return create_invoice_cash(request, form)
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


def create_invoice_credit(request, form):
    """Maneja la creación de facturas a crédito"""
    
    sub_total = Decimal('0.00')

    with transaction.atomic():
        invoice = form.save(commit=False)
        
        items = request.POST.getlist('item_id')
        quantities = request.POST.getlist('quantity')
        prices = request.POST.getlist('price')

        payment_frequency = request.POST.get('payment_frequency')
        quotas = request.POST.get('quotas')
        discount_percent = request.POST.get('discount-percent')
        transaction_type_id = request.POST.get('transaction_type')
        notes = request.POST.get('notes')

        # =============================
        # DOMICILIO
        # =============================
        has_delivery = request.POST.get('has_delivery')
        delivery_amount = request.POST.get('delivery_amount')
        delivery_value = Decimal(delivery_amount) if has_delivery and delivery_amount else Decimal('0.00')

        # =============================
        # CUOTA INICIAL
        # =============================
        initial_quota_amount = request.POST.get('initial_quota_amount')
        initial_quota_value = Decimal(initial_quota_amount) if initial_quota_amount else Decimal('0.00')

        # =============================
        # SUBTOTAL PRODUCTOS
        # =============================
        for qty, price in zip(quantities, prices):
            if qty and price:
                sub_total += Decimal(qty) * Decimal(price)

        # =============================
        # CONFIG FACTURA
        # =============================
        invoice.payment_method = 'Credito'
        invoice.status = 'Credito'
        invoice.notes = notes
        invoice.user = request.user
        invoice.quotas = int(quotas) if quotas else 0
        invoice.payment_frequency = payment_frequency
        invoice.initial_fee = initial_quota_value
        invoice.delivery_amount = delivery_value

        # =============================
        # DESCUENTO
        # =============================
        total = sub_total

        if discount_percent:
            discount_percent = Decimal(discount_percent)
            total -= total * (discount_percent / Decimal('100'))
            invoice.discount = discount_percent
        else:
            invoice.discount = Decimal('0.00')

        # =============================
        # TOTAL A FINANCIAR (REAL)
        # =============================
        # El domicilio se cobra aparte (pagado) y NO reduce el valor financiado.
        total_financiar = total - initial_quota_value

        if total_financiar < 0:
            total_financiar = Decimal('0.00')

        # Total visible de la factura (informativo)
        invoice.total = total + delivery_value

        # =============================
        # TRANSACCIÓN / CONSECUTIVO
        # =============================
        transaction_type = get_object_or_404(TransactionType, id=transaction_type_id)
        invoice.invoice_number = transaction_type.consecutive
        invoice.transaction_type = transaction_type
        transaction_type.consecutive += 1
        transaction_type.save()

        invoice.save()

        # =============================
        # CREAR CUOTAS FINANCIADAS
        # =============================
        cuota_valor = Decimal('0.00')

        if invoice.quotas > 0 and total_financiar > 0:
            cuota_valor = (total_financiar / invoice.quotas).quantize(Decimal('0.01'))

            start_date = invoice.date or date.today()
            fechas = calcular_fechas_cuotas(
                start_date,
                invoice.quotas,
                payment_frequency,
                tiene_cuota_inicial=(initial_quota_value > 0)
            )

            for i, fecha in enumerate(fechas):
                PaymentQuota.objects.create(
                    invoice=invoice,
                    number=i + 1,
                    amount=cuota_valor,
                    payment_date=fecha,
                    is_paid=False
                )

        # =============================
        # REGISTRAR PAGO INICIAL (CUOTA 0)
        # =============================
        pago_inicial_total = initial_quota_value + delivery_value

        if pago_inicial_total > 0:
            PaymentQuota.objects.create(
                invoice=invoice,
                number=0,
                amount=pago_inicial_total,
                payment_date=date.today(),
                is_paid=True
            )

        # =============================
        # ITEMS Y STOCK
        # =============================
        for item_id, qty, price in zip(items, quantities, prices):
            if item_id and qty and price:
                item = Item.objects.get(id=item_id)
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item=item,
                    quantity=int(qty),
                    price=Decimal(price),
                )
                item.Stock -= int(qty)
                item.save()

        # =============================
        # PDF
        # =============================
        if request.POST.get('download') == 'pdf':
            return render_pdf_with_puppeteer(
                'invoice/receipt_credit_pdf.html',
                {
                    'invoice': invoice,
                    'sub_total': sub_total,
                    'total_financiar': total_financiar,
                    'total_pagado_hoy': pago_inicial_total,
                    'cuota_valor': cuota_valor,
                },
                filename=f"Factura_Credito_{invoice.invoice_number}.pdf"
            )

        return redirect('report_invoice')


def create_invoice_cash(request, form):
    """Maneja la creación de facturas de contado"""
    sub_total = 0
    should_download_pdf = request.POST.get('download') == 'pdf'
    
    with transaction.atomic():
        invoice = form.save(commit=False)

        items = request.POST.getlist('item_id')
        quantities = request.POST.getlist('quantity')
        prices = request.POST.getlist('price')

        discount_percent = request.POST.get('discount-percent')
        transaction_type_id = request.POST.get('transaction_type')
        notes = request.POST.get('notes')
        status = request.POST.get('status') or 'Pagada'
        
        # Campos de domicilio
        has_delivery = request.POST.get('has_delivery')
        delivery_amount = request.POST.get('delivery_amount')
        delivery_value = float(delivery_amount) if has_delivery and delivery_amount else 0.0

        # Calcular subtotal (productos)
        sub_total = sum([
            float(price.replace(',', '').replace('$', ''))
            for price in prices if price
        ])

        invoice.payment_method = 'Contado'
        invoice.status = status
        invoice.notes = notes
        invoice.user = request.user

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

        # Para contado, el domicilio se suma al total
        total += delivery_value
        invoice.delivery_amount = delivery_value
        invoice.total = total

        # Relacionar con tipo de transacción y actualizar consecutivo
        transaction_type = get_object_or_404(TransactionType, id=transaction_type_id)
        invoice.invoice_number = transaction_type.consecutive
        invoice.transaction_type = transaction_type
        transaction_type.consecutive += 1
        transaction_type.save()

        invoice.save()

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

    # Generar PDF DESPUÉS de la transacción
    if should_download_pdf:
        return render_pdf_with_puppeteer(
            'invoice/receipt_pdf.html',
            {
                'invoice': invoice,
                'sub_total': sub_total,
                'total_restante': invoice.total - (invoice.delivery_amount or 0),
            },
            filename=f"Factura_Contado_{invoice.invoice_number}.pdf"
        )

    return redirect('report_invoice')

@login_required
def invoices_report(request):
    invoices = (
        Invoice.objects
        .select_related('customer')
        .prefetch_related('payment_quotas')
        .all()
    )

    # Totales generales
    total_credit = Invoice.objects.filter(payment_method='Credito').aggregate(
        result=Sum('total')
    )['result'] or Decimal('0')

    total_pagado = Invoice.objects.filter(status='Pagada').aggregate(
        result=Sum('total')
    )['result'] or Decimal('0')

    cont_credit = Invoice.objects.filter(payment_method='Credito').count()
    cont_pay = Invoice.objects.filter(status='Pagada').count()

    invoice_list = []

    for invoice in invoices:
        customer = invoice.customer

        total_factura = float(invoice.total or 0)

        if invoice.payment_method == 'Credito':
            total_pagado_factura = round(
                sum(float(q.amount) for q in invoice.payment_quotas.filter(is_paid=True)),
                2
            )
        else:
            # Para contado, si está marcada como pagada, consideramos el total como pagado.
            total_pagado_factura = total_factura if invoice.status == 'Pagada' else 0.0

        # ===============================
        # SALDO PENDIENTE
        # ===============================
        saldo_pendiente = round(total_factura - total_pagado_factura, 2)

        # ===============================
        # VALIDAR ESTADO
        # ===============================
        has_unpaid_quotas = invoice.payment_quotas.filter(is_paid=False).exists()

        # ===============================
        # DATA PARA LA VISTA
        # ===============================
        invoice_list.append({
            'id': invoice.id,
            'date': invoice.date.strftime('%Y-%m-%d') if invoice.date else '',
            'invoice_number': invoice.invoice_number,
            'customer_name': customer.name if customer else '',
            'customer_last_name': customer.lastname if customer else '',
            'customer_full_name': f"{customer.name} {customer.lastname}" if customer else '',
            'customer_email': customer.email if customer else '',
            'customer_id': customer.id if customer else '',

            # IMPORTANTE
            'total': total_factura,               
            'pagado': total_pagado_factura,        
            'saldo_pendiente': saldo_pendiente,     

            'payment_method': invoice.payment_method,
            'status': invoice.status,
            'discount': float(invoice.discount or 0),
            'notes': invoice.notes,
            'quotas': invoice.quotas,
            'has_unpaid_quotas': has_unpaid_quotas,

            'delivery_amount': float(invoice.delivery_amount or 0),
            'initial_fee': float(invoice.initial_fee or 0),
        })

    return render(request, 'Invoice/Report_invoice.html', {
        'invoices': invoice_list,
        'invoices_json': json.dumps(invoice_list), 
        'total_pagado': float(total_pagado),
        'total_credito': float(total_credit),
        'cont_pay': cont_pay,
        'cont_credit': cont_credit,
    })


@login_required
def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    # Subtotal de productos (sin depender de campos calculados en frontend)
    sub_total = sum(
        (item.subtotal() if callable(getattr(item, 'subtotal', None)) else item.subtotal)
        for item in invoice.items.all()
    )

    if invoice.payment_method == 'Credito':
        template = 'invoice/receipt_credit_pdf.html'
        total_financiar = get_total_financiar(invoice)
        cuota_valor = get_valor_cuota(invoice)
        saldo_pendiente = get_saldo_pendiente(invoice)
        quotas_modified = get_quotas_modified(invoice, expected_quota_amount=cuota_valor)
    else:
        template = 'invoice/receipt_pdf.html'
        total_financiar = None
        cuota_valor = None
        saldo_pendiente = invoice.total
        quotas_modified = False

    response = render_pdf_with_puppeteer(
        template,
        {
            'invoice': invoice,
            'sub_total': sub_total,
            'total_restante': saldo_pendiente,
            'total_financiar': total_financiar,
            'cuota_valor': cuota_valor,
            'saldo_pendiente': saldo_pendiente,
            'quotas_modified': quotas_modified,
        },
        filename=f"Factura_{invoice.invoice_number}.pdf"
    )

    response['Content-Disposition'] = f'attachment; filename="Factura_{invoice.invoice_number}.pdf"'
    return response



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

    # Subtotal de productos
    sub_total = round(
        sum(item.subtotal() if callable(item.subtotal) else item.subtotal
            for item in invoice.items.all()),
        2
    )

    # =============================
    # FACTURA A CRÉDITO
    # =============================
    if invoice.payment_method == 'Credito':

        total_financiar = round(
            sum(q.amount for q in invoice.payment_quotas.filter(number__gt=0)),
            2
        )

        primera_cuota = invoice.payment_quotas.filter(number__gt=0).first()
        cuota_valor = round(primera_cuota.amount, 2) if primera_cuota else 0

        quotas_modified = get_quotas_modified(invoice)

        cuotas_pagadas = invoice.payment_quotas.filter(is_paid=True).count()
        total_cuotas = invoice.payment_quotas.count()

        return render(request, 'invoice/receipt_credit_pdf.html', {
            'invoice': invoice,
            'sub_total': sub_total,
            'total_financiar': total_financiar,
            'cuota_valor': cuota_valor,
            'total_restante': total_financiar,
            'cuotas_pagadas': cuotas_pagadas,
            'total_cuotas': total_cuotas,
            'quotas_modified': quotas_modified,
        })

    # =============================
    # FACTURA DE CONTADO
    # =============================
    else:
        total_restante = round(invoice.total, 2)

        return render(request, 'invoice/receipt_pdf.html', {
            'invoice': invoice,
            'sub_total': sub_total,
            'total_restante': total_restante
        })

    
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
        return pdf_path

    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response

@login_required
def pay_quota(request, quota_id):
    quota = get_object_or_404(PaymentQuota, id=quota_id)

    if getattr(quota, 'number', None) == 0:
        return HttpResponseBadRequest("La cuota inicial no se puede pagar desde este módulo")

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

        # Enviar email en segundo plano para no demorar la respuesta al usuario.
        destinatario = getattr(quota.invoice.customer, 'email', None)
        nombre_cliente = getattr(quota.invoice.customer, 'name', '')
        referencia = f"#{quota.invoice.id}"
        fecha_hoy = datetime.now().strftime('%d/%m/%Y')
        attachment_name = f"Recibo_Cuota_{quota.id}.pdf"

        def _enviar_y_limpiar():
            try:
                if destinatario:
                    send_email_with_attachment(
                        destinatario=destinatario,
                        asunto="Confirmación de pago - Recibo incluido",
                        contenido_texto=(
                            f"Hola {nombre_cliente},\n\n"
                            "¡Tu pago ha sido procesado exitosamente!\n\n"
                            "En este correo encontrarás tu recibo de pago adjunto.\n\n"
                            f"Detalles del pago:\n"
                            f"• Estado: Confirmado\n"
                            f"• Fecha: {fecha_hoy}\n"
                            f"• Referencia: {referencia}\n\n"
                            "Gracias por tu confianza.\n"
                            "Equipo CELUPRO CO"
                        ),
                        contenido_html=(
                            f"<div style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;'>"
                            
                            f"<!-- Header -->"
                            f"<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;'>"
                            f"<h1 style='color: #ffffff; margin: 0; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;'>CELUPRO CO</h1>"
                            f"</div>"
                            
                            f"<!-- Content -->"
                            f"<div style='padding: 40px 30px;'>"
                            f"<h2 style='color: #1a202c; margin: 0 0 24px 0; font-size: 24px; font-weight: 600;'>Pago confirmado ✓</h2>"
                            
                            f"<p style='color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;'>"
                            f"Hola <strong style='color: #2d3748;'>{nombre_cliente}</strong>,</p>"
                            
                            f"<p style='color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 32px 0;'>"
                            f"Tu pago ha sido procesado exitosamente. A continuación encontrarás los detalles de tu transacción.</p>"
                            
                            f"<!-- Details Card -->"
                            f"<div style='background-color: #f7fafc; border-left: 4px solid #667eea; padding: 24px; margin: 0 0 32px 0; border-radius: 4px;'>"
                            f"<table style='width: 100%; border-collapse: collapse;'>"
                            f"<tr><td style='padding: 8px 0; color: #718096; font-size: 14px;'>Estado</td>"
                            f"<td style='padding: 8px 0; color: #2d3748; font-size: 14px; text-align: right; font-weight: 600;'>"
                            f"<span style='background-color: #c6f6d5; color: #22543d; padding: 4px 12px; border-radius: 12px; font-size: 13px;'>Confirmado</span></td></tr>"
                            f"<tr><td style='padding: 8px 0; color: #718096; font-size: 14px; border-top: 1px solid #e2e8f0;'>Fecha</td>"
                            f"<td style='padding: 8px 0; color: #2d3748; font-size: 14px; text-align: right; font-weight: 500; border-top: 1px solid #e2e8f0;'>{fecha_hoy}</td></tr>"
                            f"<tr><td style='padding: 8px 0; color: #718096; font-size: 14px; border-top: 1px solid #e2e8f0;'>Referencia</td>"
                            f"<td style='padding: 8px 0; color: #2d3748; font-size: 14px; text-align: right; font-weight: 500; border-top: 1px solid #e2e8f0;'>{referencia}</td></tr>"
                            f"</table>"
                            f"</div>"
                            
                            f"<p style='color: #4a5568; font-size: 14px; line-height: 1.6; margin: 0 0 8px 0;'>"
                            f"📎 Encontrarás el recibo detallado adjunto a este correo en formato PDF.</p>"
                            
                            f"</div>"
                            
                            f"<!-- Footer -->"
                            f"<div style='background-color: #f7fafc; padding: 30px; text-align: center; border-top: 1px solid #e2e8f0;'>"
                            f"<p style='color: #718096; font-size: 14px; margin: 0 0 8px 0;'>Gracias por tu confianza, si tienes alguna duda escríbenos.</p>"
                            f"<p style='color: #2d3748; font-size: 16px; font-weight: 600; margin: 0;'>CELUPRO CO</p>"
                            f"</div>"
                            
                            f"</div>"
                        ),
                        attachment_path=pdf_path,
                        attachment_name=attachment_name,
                    )
            finally:
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except Exception:
                    pass

        threading.Thread(target=_enviar_y_limpiar, daemon=True).start()

        # Responder con el PDF como descarga inmediata.
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
        return response

    return HttpResponseNotAllowed(['POST'])


@login_required
@require_POST
def reverse_quota(request, quota_id):
    """Revierte una cuota ya pagada: elimina los pagos asociados y deja la cuota como pendiente."""
    quota = get_object_or_404(
        PaymentQuota.objects.select_related('invoice', 'invoice__customer'),
        pk=quota_id,
    )

    if getattr(quota, 'number', None) == 0:
        return HttpResponseBadRequest("La cuota inicial no se puede anular desde este módulo")

    if not quota.is_paid:
        return HttpResponseBadRequest("La cuota no está marcada como pagada")

    reversed_amount = quota.paid_amount
    if reversed_amount <= 0:
        return HttpResponseBadRequest("No hay pagos registrados para anular")

    with transaction.atomic():
        quota.payments.all().delete()
        quota.is_paid = False
        quota.save(update_fields=['is_paid'])

    context = {
        'quota': quota,
        'invoice': quota.invoice,
        'reversed_amount': reversed_amount,
        'reversed_at': datetime.now(),
    }

    pdf_path = render_pdf_inline_with_puppeteer(
        'PaymentQuota/Receipt_ticket_cancel.html',
        context,
        filename="Comprobante_Anulacion_Cuota.pdf",
        return_path=True
    )

    # Leer bytes para responder inmediatamente (evita condiciones de carrera con el hilo).
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    # Enviar email en segundo plano.
    destinatario = getattr(quota.invoice.customer, 'email', None)
    nombre_cliente = getattr(quota.invoice.customer, 'name', '')
    referencia = f"#{quota.invoice.id}"
    fecha_hoy = datetime.now().strftime('%d/%m/%Y')
    attachment_name = f"Anulacion_Cuota_{quota.id}.pdf"

    def _enviar_y_limpiar():
        try:
            if destinatario:
                send_email_with_attachment(
                    destinatario=destinatario,
                    asunto="Anulación de cuota - Comprobante incluido",
                    contenido_texto=(
                        f"Hola {nombre_cliente},\n\n"
                        "Tu cuota ha sido anulada y la misma quedó nuevamente pendiente.\n\n"
                        "En este correo encontrarás el comprobante de anulación adjunto.\n\n"
                        f"Detalles:\n"
                        f"• Fecha: {fecha_hoy}\n"
                        f"• Referencia: {referencia}\n\n"
                        "Equipo CELUPRO CO"
                    ),
                    contenido_html=(
                        f"<div style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;'>"
                        f"<div style='background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%); padding: 30px; text-align: center;'>"
                        f"<h1 style='color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;'>CELUPRO CO</h1>"
                        f"</div>"
                        f"<div style='padding: 30px;'>"
                        f"<h2 style='color: #1a202c; margin: 0 0 18px 0; font-size: 20px; font-weight: 700;'>Anulación registrada</h2>"
                        f"<p style='color: #4a5568; font-size: 15px; line-height: 1.6; margin: 0 0 18px 0;'>Hola <strong>{nombre_cliente}</strong>,</p>"
                        f"<p style='color: #4a5568; font-size: 15px; line-height: 1.6; margin: 0 0 18px 0;'>Se registró la anulación de una cuota. La cuota quedó nuevamente en estado <strong>Pendiente</strong>.</p>"
                        f"<div style='background-color: #fff5f5; border-left: 4px solid #ef4444; padding: 16px; margin: 0 0 18px 0; border-radius: 4px;'>"
                        f"<div style='color:#4a5568; font-size: 14px;'><b>Fecha:</b> {fecha_hoy}</div>"
                        f"<div style='color:#4a5568; font-size: 14px;'><b>Referencia:</b> {referencia}</div>"
                        f"</div>"
                        f"<p style='color: #4a5568; font-size: 14px; line-height: 1.6; margin: 0;'>📎 Comprobante adjunto en PDF.</p>"
                        f"</div>"
                        f"<div style='background-color: #f7fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;'>"
                        f"<p style='color: #718096; font-size: 13px; margin: 0;'>Gracias por tu confianza.</p>"
                        f"</div>"
                        f"</div>"
                    ),
                    attachment_path=pdf_path,
                    attachment_name=attachment_name,
                )
        finally:
            try:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except Exception:
                pass

    threading.Thread(target=_enviar_y_limpiar, daemon=True).start()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
    return response

@login_required
def download_quota_receipt(request, quota_id):
    quota = get_object_or_404(PaymentQuota, pk=quota_id)

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
    customers = Customer.objects.all().order_by('name', 'lastname')

    # Mantener compatibilidad: si llega customer_id por URL (legacy), se preselecciona.
    selected_customer_id = customer_id or request.GET.get('customer_id')
    selected_invoice_id = request.GET.get('invoice_id')

    context = {
        'customers': customers,
        'selected_customer_id': int(selected_customer_id) if selected_customer_id else None,
        'selected_invoice_id': int(selected_invoice_id) if selected_invoice_id else None,
    }
    return render(request, 'PaymentQuota/History.html', context)


@login_required
@require_GET
def payment_history_invoices(request, customer_id):
    # Solo facturas a crédito: en este sistema, la fuente de verdad es que existan cuotas
    # (PaymentQuota) asociadas a la factura.
    # Además mantenemos un fallback por si hay facturas a crédito sin cuotas creadas.
    credit_method = (
        Q(payment_method__iexact='credit') |
        Q(payment_method__iexact='credito') |
        Q(payment_method__iexact='crédito') |
        Q(payment_method__iexact='Credito')
    )

    invoices = (
        Invoice.objects
        .filter(customer_id=customer_id)
        .filter(
            Q(payment_quotas__isnull=False) |
            (credit_method & Q(quotas__gt=0))
        )
        .distinct()
        .only('id', 'invoice_number', 'date', 'payment_method')
        .order_by('-date')
    )

    data = {
        'invoices': [
            {
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'date': inv.date.strftime('%Y-%m-%d'),
                'payment_method': inv.payment_method,
            }
            for inv in invoices
        ]
    }
    return JsonResponse(data)


@login_required
@require_GET
def payment_history_data(request):
    customer_id = request.GET.get('customer_id')
    invoice_id = request.GET.get('invoice_id')

    if not customer_id:
        return JsonResponse({'error': 'customer_id es requerido'}, status=400)

    payments_qs = Early_Payment.objects.select_related(
        'quota',
        'quota__invoice',
        'quota__invoice__customer'
    ).filter(quota__invoice__customer_id=customer_id)

    if invoice_id:
        payments_qs = payments_qs.filter(quota__invoice_id=invoice_id)

    payments_qs = payments_qs.order_by('-date')

    payments = []
    total_paid = Decimal('0.00')
    for p in payments_qs:
        customer = p.quota.invoice.customer
        total_paid += p.amount
        payments.append({
            'customer': f"{customer.name} {customer.lastname}",
            'invoice_number': p.quota.invoice.invoice_number,
            'quota_number': p.quota.number,
            'amount': float(p.amount),
            'date': p.date.strftime('%Y-%m-%d %H:%M'),
        })

    # Serie para gráfica: total pagado por día
    series_qs = (
        payments_qs
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    labels = []
    values = []
    for row in series_qs:
        labels.append(row['day'].strftime('%Y-%m-%d') if row['day'] else '')
        values.append(float(row['total'] or 0))

    return JsonResponse({
        'payments': payments,
        'chart': {
            'labels': labels,
            'values': values,
        },
        'summary': {
            'total_paid': float(total_paid),
            'count_payments': len(payments),
        }
    })

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

    pdf_url = None
    if invoice.status == 'Anulada':
        pdf_url = reverse('canceled_invoice_pdf', args=[invoice.id])

    data = {
        'id': invoice.id,
        'status': invoice.status,
        'customer': f"{invoice.customer.name} {invoice.customer.lastname}",
        'total': float(invoice.total),
        'date': invoice.date.strftime('%Y-%m-%d'),
        'items': item_list,
        'pdf_url': pdf_url,
    }
    return JsonResponse(data)

@login_required
def canceled_invoice_pdf_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if invoice.status != 'Anulada':
        return HttpResponse('La factura no está anulada.', status=400)

    canceled = None
    try:
        canceled = invoice.cancellation
    except Exception:
        canceled = CanceledInvoice.objects.filter(original_invoice=invoice).first()

    pdf_filename = f"factura_cancelada_{invoice.id}.pdf"
    pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_filename)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    if not os.path.exists(pdf_path):
        html_id = str(uuid.uuid4())
        html_path = os.path.join(settings.BASE_DIR, 'tmp', f"{html_id}.html")
        os.makedirs(os.path.dirname(html_path), exist_ok=True)

        html_content = render_to_string('invoice/receipt_pdf_cancel.html', {
            'invoice': invoice,
            'canceled': canceled,
            'now': datetime.now().strftime('%d/%m/%Y %H:%M'),
        })
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        script_path = os.path.join(settings.BASE_DIR, 'pdfgen', 'generate_pdf.js')
        result = subprocess.run(
            ['node', script_path, html_path, pdf_path],
            capture_output=True,
            text=True
        )

        if os.path.exists(html_path):
            os.remove(html_path)

        if result.returncode != 0 or not os.path.exists(pdf_path):
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return HttpResponse('Error generando PDF de anulación.', status=500)

    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
    return response



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

        
        # El frontend envía el motivo como JSON (application/json)
        reason = ''
        try:
            content_type = (request.headers.get('Content-Type') or '').lower()
        except Exception:
            content_type = ''

        if 'application/json' in content_type:
            try:
                payload = json.loads((request.body or b'{}').decode('utf-8'))
                reason = (payload.get('reason') or '').strip()
            except Exception:
                reason = ''
        else:
            reason = (request.POST.get('reason', '') or '').strip()

        if not reason:
            reason = 'Cancelación manual desde el sistema'

        canceled = CanceledInvoice.objects.create(
            original_invoice=invoice,
            transaction_type=transaction_type,
            cancel_number=cancel_number,
            reason=reason,
            user=request.user
        )

        
        html_id = str(uuid.uuid4())
        html_path = os.path.join(settings.BASE_DIR, "tmp", f"{html_id}.html")
        pdf_path = os.path.join(settings.MEDIA_ROOT, f"factura_cancelada_{invoice.id}.pdf")
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        
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

        if not os.path.exists(pdf_path):
            return JsonResponse({'success': False, 'message': 'El PDF no se generó correctamente.'})

        
        if os.path.exists(html_path):
            os.remove(html_path)

        return JsonResponse({
            'success': True,
            'message': 'Factura anulada correctamente.',
            'pdf_url': f"{settings.MEDIA_URL}factura_cancelada_{invoice.id}.pdf"
        })

    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)




@login_required
def send_invoice_simple(request, invoice_id):
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
    
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        if not invoice.customer:
            return JsonResponse({'success': False, 'message': 'La factura no tiene cliente asignado.'})
        
        if not invoice.customer.email:
            return JsonResponse({'success': False, 'message': 'El cliente no tiene un correo electrónico registrado.'})
        
        pdf_path = None
        try:
            pdf_path = generate_temp_invoice_pdf_safe(invoice)
            print(f"PDF generado: {pdf_path}")
        except Exception as pdf_error:
            print(f" Error generando PDF: {pdf_error}")
            return JsonResponse({'success': False, 'message': f'Error generando PDF: {str(pdf_error)}'})
        
        print("📧 Enviando email...")
        try:
            def _safe_filename_part(value: str) -> str:
                value = (value or '').strip()
                if not value:
                    return ''
                value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
                value = re.sub(r'[^A-Za-z0-9]+', '_', value).strip('_')
                return value

            customer_full_name = f"{invoice.customer.name} {invoice.customer.lastname}".strip()
            safe_customer = _safe_filename_part(customer_full_name) or f"Cliente_{invoice.customer.id}"
            attachment_name = f"Factura_{invoice.invoice_number}_{safe_customer}.pdf"

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
                attachment_path=pdf_path,
                attachment_name=attachment_name
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
        print("=== FIN ENVÍO FACTURA ===")

def generate_temp_invoice_pdf_safe(invoice):

    tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    html_path = os.path.join(tmp_dir, f"{file_id}.html")
    pdf_path = os.path.join(tmp_dir, f"{file_id}.pdf")

    try:
        template = get_invoice_pdf_template(invoice)

        # Subtotal de productos (sin domicilio)
        sub_total = sum(
            (item.subtotal() if callable(getattr(item, 'subtotal', None)) else item.subtotal)
            for item in invoice.items.all()
        )

        total_financiar = get_total_financiar(invoice)
        cuota_valor = get_valor_cuota(invoice)
        saldo_pendiente = get_saldo_pendiente(invoice)
        quotas_modified = get_quotas_modified(invoice, expected_quota_amount=cuota_valor)

        html_content = render_to_string(
            template,
            {
                'invoice': invoice,
                'is_credit': invoice.payment_method == 'Credito',
                'sub_total': sub_total,
                'total_financiar': total_financiar,
                'cuota_valor': cuota_valor,
                'saldo_pendiente': saldo_pendiente,
                'quotas_modified': quotas_modified,
            }
        )

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        script_path = os.path.join(settings.BASE_DIR, "pdfgen", "generate_pdf.js")

        result = subprocess.run(
            ["node", script_path, html_path, pdf_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise Exception(result.stderr)

        if not os.path.exists(pdf_path):
            raise Exception("El PDF no fue generado")

        return pdf_path

    finally:
        if os.path.exists(html_path):
            os.remove(html_path)


def get_invoice_pdf_template(invoice):
    if invoice.payment_method == 'Credito':
        return 'invoice/receipt_credit_pdf.html'
    return 'invoice/receipt_pdf.html'

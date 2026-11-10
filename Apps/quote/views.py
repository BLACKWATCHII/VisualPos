from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from customer.models import Customer
from item.models import Item

from .models import Quote, QuoteItem

QUOTE_TEMPLATE_PDF = 'quote/quote_pdf.html'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_decimal(value, default=Decimal('0')):
    text = str(value or '').strip().replace('$', '').replace(',', '')
    if not text:
        return default
    try:
        return Decimal(text)
    except InvalidOperation:
        return default


def _to_int(value, default=0):
    try:
        return int(str(value or '').strip())
    except (TypeError, ValueError):
        return default


def _next_number():
    """Consecutivo siguiente. Bloquea la última fila para evitar duplicados;
    el unique=True de 'number' es la red de seguridad final."""
    last = (
        Quote.objects.select_for_update()
        .order_by('-number')
        .values_list('number', flat=True)
        .first()
    )
    return (last or 0) + 1


def _read_lines(request):
    """Lee las líneas del formulario. Devuelve (lineas, errores)."""
    item_ids = request.POST.getlist('item_id')
    quantities = request.POST.getlist('quantity')
    prices = request.POST.getlist('price')

    lines, errors = [], []
    wanted_ids = {_to_int(i) for i in item_ids if _to_int(i)}
    items_by_id = Item.objects.in_bulk(wanted_ids)

    for raw_id, raw_qty, raw_price in zip(item_ids, quantities, prices):
        item_id = _to_int(raw_id)
        if not item_id:
            continue  # línea vacía
        item = items_by_id.get(item_id)
        qty = _to_int(raw_qty)
        price = _to_decimal(raw_price, default=None)
        if item is None:
            errors.append('Uno de los productos ya no existe.')
            continue
        if qty < 1:
            errors.append(f'La cantidad de "{item.Name}" debe ser mayor a 0.')
            continue
        if price is None or price < 0:
            errors.append(f'El precio de "{item.Name}" no es válido.')
            continue
        lines.append((item, qty, price))

    if not lines and not errors:
        errors.append('Agrega al menos un producto a la cotización.')
    return lines, errors


def _initial_data(quote=None, posted=None):
    """Datos con los que el JS del formulario pinta los campos y las líneas."""
    today = date.today()
    if posted is not None:
        return {
            'customer': posted.get('customer') or '',
            'quote_date': posted.get('quote_date') or today.isoformat(),
            'valid_until': posted.get('valid_until') or '',
            'has_discount': bool(posted.get('has_discount')),
            'discount': posted.get('discount_percent') or '0',
            'has_delivery': bool(posted.get('has_delivery')),
            'delivery_amount': posted.get('delivery_amount') or '0',
            'notes': posted.get('notes') or '',
            'lines': [
                {'item_id': i, 'quantity': q, 'price': p}
                for i, q, p in zip(posted.getlist('item_id'), posted.getlist('quantity'), posted.getlist('price'))
                if i
            ],
        }
    if quote is not None:
        return {
            'customer': str(quote.customer_id),
            'quote_date': quote.quote_date.isoformat() if quote.quote_date else today.isoformat(),
            'valid_until': quote.valid_until.isoformat() if quote.valid_until else '',
            'has_discount': quote.discount > 0,
            'discount': str(quote.discount),
            'has_delivery': quote.delivery_amount > 0,
            'delivery_amount': str(int(quote.delivery_amount)),
            'notes': quote.notes or '',
            'lines': [
                {'item_id': str(line.item_id), 'quantity': line.quantity, 'price': str(line.price)}
                for line in quote.items.all()
            ],
        }
    return {
        'customer': '',
        'quote_date': today.isoformat(),
        'valid_until': (today + timedelta(days=settings.QUOTE_DEFAULT_VALIDITY_DAYS)).isoformat(),
        'has_discount': False,
        'discount': '0',
        'has_delivery': False,
        'delivery_amount': '0',
        'notes': '',
        'lines': [],
    }


def _form_context(request, quote=None, posted=None):
    customers = Customer.objects.order_by('name', 'lastname')
    items = Item.objects.filter(active=True).order_by('Name')
    # Si se edita una cotización con un producto ya inactivo, igual debe verse
    if quote is not None:
        extra_ids = set(quote.items.values_list('item_id', flat=True)) - set(items.values_list('id', flat=True))
        if extra_ids:
            items = Item.objects.filter(Q(active=True) | Q(id__in=extra_ids)).order_by('Name')
    return {
        'quote': quote,
        'customers': customers,
        'items': items,
        'initial': _initial_data(quote=quote, posted=posted),
    }


def _save_from_post(request, quote=None):
    """Crea o actualiza una cotización desde el POST. Devuelve (quote, errores)."""
    errors = []
    customer = Customer.objects.filter(pk=_to_int(request.POST.get('customer'))).first()
    if customer is None:
        errors.append('Selecciona un cliente.')

    quote_date = parse_date((request.POST.get('quote_date') or '').strip()) or date.today()
    valid_until = parse_date((request.POST.get('valid_until') or '').strip())
    if valid_until and valid_until < quote_date:
        errors.append('La fecha "Válida hasta" no puede ser anterior a la fecha de la cotización.')

    discount = _to_decimal(request.POST.get('discount_percent')) if request.POST.get('has_discount') else Decimal('0')
    if discount < 0 or discount > 100:
        errors.append('El descuento debe estar entre 0 y 100%.')

    delivery = _to_decimal(request.POST.get('delivery_amount')) if request.POST.get('has_delivery') else Decimal('0')
    if delivery < 0:
        errors.append('El valor del domicilio no puede ser negativo.')

    lines, line_errors = _read_lines(request)
    errors.extend(line_errors)
    if errors:
        return None, errors

    is_new = quote is None
    for attempt in range(3):
        try:
            with transaction.atomic():
                if is_new:
                    # Objeto nuevo en cada intento: si el anterior falló por
                    # consecutivo repetido, no arrastra un pk inválido
                    quote = Quote(number=_next_number(), user=request.user)
                quote.customer = customer
                quote.quote_date = quote_date
                quote.valid_until = valid_until
                quote.discount = discount
                quote.delivery_amount = delivery
                quote.notes = (request.POST.get('notes') or '').strip() or None
                quote.save()

                quote.items.all().delete()
                QuoteItem.objects.bulk_create([
                    QuoteItem(quote=quote, item=item, quantity=qty, price=price)
                    for item, qty, price in lines
                ])
                quote.recalculate_totals()
                quote.save(update_fields=['subtotal', 'total', 'updated_at'])
            return quote, []
        except IntegrityError:
            # Choque de consecutivo con otro usuario: reintentar con el siguiente
            if not is_new or attempt == 2:
                raise
    return quote, []


# ---------------------------------------------------------------------------
# Pantallas
# ---------------------------------------------------------------------------

@login_required
def quote_list(request):
    qs = Quote.objects.select_related('customer', 'invoice', 'user')

    search = (request.GET.get('q') or '').strip()
    if search:
        filters = (
            Q(customer__name__icontains=search)
            | Q(customer__lastname__icontains=search)
            | Q(customer__cedula__icontains=search)
        )
        digits = ''.join(ch for ch in search if ch.isdigit())
        if digits:
            filters |= Q(number=int(digits))
        qs = qs.filter(filters)

    status = request.GET.get('status') or ''
    if status in dict(Quote.STATUS_CHOICES):
        qs = qs.filter(status=status)

    page = Paginator(qs, 25).get_page(request.GET.get('page'))
    return render(request, 'quote/quote_list.html', {
        'page': page,
        'search': search,
        'status': status,
        'status_choices': Quote.STATUS_CHOICES,
    })


@login_required
def quote_create(request):
    if request.method == 'POST':
        quote, errors = _save_from_post(request)
        if not errors:
            messages.success(request, f'Cotización {quote.code} creada.')
            return redirect('quote_list')
        for err in errors:
            messages.error(request, err)
        return render(request, 'quote/quote_form.html', _form_context(request, posted=request.POST))
    return render(request, 'quote/quote_form.html', _form_context(request))


@login_required
def quote_edit(request, quote_id):
    quote = get_object_or_404(Quote.objects.prefetch_related('items__item'), pk=quote_id)
    if not quote.is_editable:
        messages.error(request, f'La cotización {quote.code} está {quote.get_status_display().lower()} y no se puede editar.')
        return redirect('quote_list')

    if request.method == 'POST':
        saved, errors = _save_from_post(request, quote=quote)
        if not errors:
            messages.success(request, f'Cotización {saved.code} actualizada.')
            return redirect('quote_list')
        for err in errors:
            messages.error(request, err)
        return render(request, 'quote/quote_form.html', _form_context(request, quote=quote, posted=request.POST))
    return render(request, 'quote/quote_form.html', _form_context(request, quote=quote))


def _pdf_context(quote):
    return {'quote': quote, 'items': list(quote.items.select_related('item'))}


@login_required
def quote_preview(request, quote_id):
    quote = get_object_or_404(Quote.objects.select_related('customer', 'invoice'), pk=quote_id)
    return render(request, QUOTE_TEMPLATE_PDF, _pdf_context(quote))


@login_required
def quote_pdf(request, quote_id):
    # Import local: Invoice.views es pesado y solo se necesita aquí
    from Invoice.views import render_pdf_with_puppeteer

    quote = get_object_or_404(Quote.objects.select_related('customer', 'invoice'), pk=quote_id)
    return render_pdf_with_puppeteer(QUOTE_TEMPLATE_PDF, _pdf_context(quote), filename=f'Cotizacion_{quote.code}.pdf')


@login_required
@require_POST
def quote_cancel(request, quote_id):
    with transaction.atomic():
        quote = get_object_or_404(Quote.objects.select_for_update(), pk=quote_id)
        if quote.status != Quote.STATUS_PENDING:
            messages.error(request, f'La cotización {quote.code} ya está {quote.get_status_display().lower()}.')
        else:
            quote.status = Quote.STATUS_CANCELED
            quote.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Cotización {quote.code} anulada.')
    return redirect('quote_list')


# ---------------------------------------------------------------------------
# API para la pantalla de facturación
# ---------------------------------------------------------------------------

@login_required
@require_GET
def quote_pending_api(request):
    qs = Quote.objects.filter(status=Quote.STATUS_PENDING).select_related('customer')
    customer_id = _to_int(request.GET.get('customer'))
    if customer_id:
        qs = qs.filter(customer_id=customer_id)

    data = [{
        'id': q.id,
        'code': q.code,
        'customer_id': q.customer_id,
        'customer': f'{q.customer.name} {q.customer.lastname}'.strip(),
        'cedula': q.customer.cedula,
        'quote_date': q.quote_date.isoformat() if q.quote_date else None,
        'valid_until': q.valid_until.isoformat() if q.valid_until else None,
        'expired': q.is_expired,
        'total': str(q.total),
    } for q in qs[:200]]
    return JsonResponse({'quotes': data})


@login_required
@require_GET
def quote_detail_api(request, quote_id):
    quote = get_object_or_404(Quote.objects.select_related('customer'), pk=quote_id)
    if quote.status != Quote.STATUS_PENDING:
        return JsonResponse(
            {'error': f'La cotización {quote.code} está {quote.get_status_display().lower()}.'},
            status=409,
        )
    items = [{
        'item_id': line.item_id,
        'name': line.item.Name,
        'quantity': line.quantity,
        'price': str(line.price),
        'active': bool(line.item.active),
        'stock': line.item.Stock,
    } for line in quote.items.select_related('item')]
    return JsonResponse({
        'id': quote.id,
        'code': quote.code,
        'customer_id': quote.customer_id,
        'customer': str(quote.customer),
        'expired': quote.is_expired,
        'valid_until': quote.valid_until.isoformat() if quote.valid_until else None,
        'discount': str(quote.discount),
        'delivery_amount': str(quote.delivery_amount),
        'notes': quote.notes or '',
        'items': items,
    })

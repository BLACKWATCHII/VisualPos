from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.http import FileResponse

from datetime import datetime, timedelta, date
from decimal import Decimal
from io import BytesIO
import csv
import uuid
import subprocess
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from Invoice.models import Invoice, InvoiceItem


@login_required
def menu_reportes(request):
    """Vista principal de ventas generales"""
    return render(request, 'reports/menu_reports.html')

def reports_general(request):
    """Vista de reportes generales"""
    return render(request, 'reports/reports_general.html')


EXCLUDED_STATUSES = (
    'refunded',
    'canceled',
    'cancelled',
    'Reembolsada',
    'Reembolsado',
    'Anulada',
    'Anulado',
    'Cancelada',
    'Cancelado',
)


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        raise ValueError('Formato de fecha inválido. Usa YYYY-MM-DD.')


def _date_range_to_datetimes(inicio: date, fin: date):
    if fin < inicio:
        raise ValueError('La fecha final no puede ser menor que la inicial.')
    start_dt = timezone.make_aware(datetime.combine(inicio, datetime.min.time()))
    end_dt_exclusive = timezone.make_aware(datetime.combine(fin + timedelta(days=1), datetime.min.time()))
    return start_dt, end_dt_exclusive


def _get_trunc(periodo: str):
    if periodo == 'daily':
        return TruncDate('date')
    if periodo == 'weekly':
        return TruncWeek('date')
    if periodo == 'monthly':
        return TruncMonth('date')
    if periodo == 'yearly':
        return TruncYear('date')
    raise ValueError('Período inválido. Usa daily, weekly, monthly o yearly.')


def _build_bucket_starts(inicio: date, fin: date, periodo: str):
    if periodo == 'daily':
        cursor = inicio
        out = []
        while cursor <= fin:
            out.append(cursor)
            cursor += timedelta(days=1)
        return out

    if periodo == 'weekly':
        cursor = inicio - timedelta(days=inicio.weekday())  # lunes
        out = []
        while cursor <= fin:
            out.append(cursor)
            cursor += timedelta(days=7)
        return out

    if periodo == 'monthly':
        cursor = date(inicio.year, inicio.month, 1)
        out = []
        while cursor <= fin:
            out.append(cursor)
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
        return out

    if periodo == 'yearly':
        cursor = date(inicio.year, 1, 1)
        out = []
        while cursor <= fin:
            out.append(cursor)
            cursor = date(cursor.year + 1, 1, 1)
        return out

    raise ValueError('Período inválido. Usa daily, weekly, monthly o yearly.')


def _format_label(bucket_start: date, periodo: str) -> str:
    if periodo == 'daily':
        return bucket_start.strftime('%d/%m')
    if periodo == 'weekly':
        return bucket_start.strftime('Sem %d/%m')
    if periodo == 'monthly':
        return bucket_start.strftime('%b %Y')
    if periodo == 'yearly':
        return bucket_start.strftime('%Y')
    return str(bucket_start)


def _aggregate_sales(inicio: date, fin: date, periodo: str):
    trunc = _get_trunc(periodo)
    start_dt, end_dt_excl = _date_range_to_datetimes(inicio, fin)

    rows = (
        Invoice.objects
        .filter(date__gte=start_dt, date__lt=end_dt_excl)
        .exclude(status__in=EXCLUDED_STATUSES)
        .annotate(bucket=trunc)
        .values('bucket')
        .annotate(total=Sum('total'))
        .order_by('bucket')
    )

    by_bucket = {}
    for r in rows:
        bucket_dt = r['bucket']
        if bucket_dt is None:
            continue
        bucket_key = bucket_dt.date() if hasattr(bucket_dt, 'date') else bucket_dt
        by_bucket[bucket_key] = r['total'] or Decimal('0')

    return by_bucket


def _get_invoice_detail_rows(inicio: date, fin: date):
    start_dt, end_dt_excl = _date_range_to_datetimes(inicio, fin)
    invoices = (
        Invoice.objects
        .filter(date__gte=start_dt, date__lt=end_dt_excl)
        .exclude(status__in=EXCLUDED_STATUSES)
        .select_related('customer')
        .prefetch_related('items__item')
        .order_by('date', 'id')
    )

    rows = []
    for inv in invoices:
        customer_name = getattr(inv.customer, 'name', None) or str(inv.customer)
        inv_date = timezone.localtime(inv.date).strftime('%d/%m/%Y %H:%M') if hasattr(inv.date, 'tzinfo') else inv.date.strftime('%d/%m/%Y %H:%M')
        inv_total = float(inv.total or 0)

        payment_method = (getattr(inv, 'payment_method', '') or '').strip()
        status_value = (getattr(inv, 'status', '') or '').strip()
        es_credito = (payment_method.lower() == 'credit') or ('credito' in status_value.lower())
        tipo_pago = 'Crédito' if es_credito else 'Contado'

        items = list(inv.items.all())
        if not items:
            rows.append({
                'cliente': customer_name,
                'fecha': inv_date,
                'factura_id': inv.id,
                'total_factura': inv_total,
                'tipo_pago': tipo_pago,
                'item': '',
                'cantidad': 0,
                'precio': 0.0,
                'subtotal': 0.0,
            })
            continue

        for it in items:
            item_name = getattr(it.item, 'name', None) or getattr(it.item, 'nombre', None) or str(it.item)
            qty = int(it.quantity or 0)
            price = float(it.price or 0)
            subtotal = float(it.subtotal() if callable(getattr(it, 'subtotal', None)) else (qty * price))
            rows.append({
                'cliente': customer_name,
                'fecha': inv_date,
                'factura_id': inv.id,
                'total_factura': inv_total,
                'tipo_pago': tipo_pago,
                'item': item_name,
                'cantidad': qty,
                'precio': price,
                'subtotal': subtotal,
            })

    return rows


def _render_pdf_with_puppeteer(template_src: str, context: dict, filename: str):
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
        if os.path.exists(html_path):
            os.remove(html_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise Exception(f"Error generando PDF:\n{result.stderr.strip()}")

    if not os.path.exists(pdf_path):
        raise Exception("El archivo PDF no se generó correctamente.")

    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Limpieza
    if os.path.exists(html_path):
        os.remove(html_path)
    # Nota: no borramos el pdf antes de terminar el stream; Django cerrará el file handle.
    # Si quieres limpieza completa, se puede usar un wrapper que borre al cerrar.

    return response


@login_required
def api_ventas_datos(request):
    try:
        fecha_inicio = _parse_iso_date(request.GET.get('fecha_inicio', ''))
        fecha_fin = _parse_iso_date(request.GET.get('fecha_fin', ''))
        periodo = request.GET.get('periodo', 'monthly')

        buckets_actual = _build_bucket_starts(fecha_inicio, fecha_fin, periodo)
        if not buckets_actual:
            return JsonResponse({'labels': [], 'datasets': [], 'totales': {'actual': 0, 'anterior': 0, 'diferencia': 0, 'porcentaje_cambio': 0}})

        # Rango anterior equivalente
        days_len = (fecha_fin - fecha_inicio).days + 1
        prev_fin = fecha_inicio - timedelta(days=1)
        prev_inicio = prev_fin - timedelta(days=days_len - 1)

        buckets_anterior = _build_bucket_starts(prev_inicio, prev_fin, periodo)

        data_actual = _aggregate_sales(fecha_inicio, fecha_fin, periodo)
        data_anterior = _aggregate_sales(prev_inicio, prev_fin, periodo)

        valores_actual = [float(data_actual.get(b, Decimal('0'))) for b in buckets_actual]
        valores_anterior = []
        for idx in range(len(buckets_actual)):
            if idx < len(buckets_anterior):
                valores_anterior.append(float(data_anterior.get(buckets_anterior[idx], Decimal('0'))))
            else:
                valores_anterior.append(0.0)

        total_actual = sum(valores_actual)
        total_anterior = sum(valores_anterior)
        diferencia = total_actual - total_anterior
        if total_anterior == 0:
            porcentaje = 0.0 if total_actual == 0 else 100.0
        else:
            porcentaje = (diferencia / total_anterior) * 100.0

        payload = {
            'labels': [_format_label(b, periodo) for b in buckets_actual],
            'datasets': [
                {
                    'label': 'Período Actual',
                    'data': valores_actual,
                    'borderColor': '#10b981',
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                    'tension': 0.4,
                },
                {
                    'label': 'Período Anterior',
                    'data': valores_anterior,
                    'borderColor': '#6b7280',
                    'backgroundColor': 'rgba(107, 114, 128, 0.1)',
                    'tension': 0.4,
                },
            ],
            'totales': {
                'actual': total_actual,
                'anterior': total_anterior,
                'diferencia': diferencia,
                'porcentaje_cambio': porcentaje,
            },
        }
        return JsonResponse(payload)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Ocurrió un error generando el reporte.'}, status=500)


@login_required
def api_ventas_descargar(request):
    try:
        fecha_inicio = _parse_iso_date(request.GET.get('fecha_inicio', ''))
        fecha_fin = _parse_iso_date(request.GET.get('fecha_fin', ''))
        periodo = request.GET.get('periodo', 'monthly')
        formato = request.GET.get('formato', 'excel')

        detail_rows = _get_invoice_detail_rows(fecha_inicio, fecha_fin)
        filename_base = f"ventas_detalle_{periodo}_{fecha_inicio.isoformat()}_{fecha_fin.isoformat()}"

        if formato in ('excel', 'csv'):
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'

            # BOM para que Excel abra UTF-8 correctamente
            response.write('\ufeff')
            writer = csv.writer(response)
            writer.writerow(['Cliente', 'Fecha', 'Factura', 'Tipo de pago', 'Total Factura', 'Item', 'Cantidad', 'Precio', 'Subtotal'])
            for r in detail_rows:
                writer.writerow([
                    r['cliente'],
                    r['fecha'],
                    r['factura_id'],
                    r['tipo_pago'],
                    f"{r['total_factura']:.2f}",
                    r['item'],
                    r['cantidad'],
                    f"{r['precio']:.2f}",
                    f"{r['subtotal']:.2f}",
                ])
            return response

        if formato == 'pdf':
            # Estructura para PDF: 1 fila por factura, items listados dentro
            start_dt, end_dt_excl = _date_range_to_datetimes(fecha_inicio, fecha_fin)
            invoices = (
                Invoice.objects
                .filter(date__gte=start_dt, date__lt=end_dt_excl)
                .exclude(status__in=EXCLUDED_STATUSES)
                .select_related('customer')
                .prefetch_related('items__item')
                .order_by('date', 'id')
            )

            invoices_pdf = []
            total_contado = 0.0
            total_credito = 0.0
            for inv in invoices:
                customer_name = getattr(inv.customer, 'name', None) or str(inv.customer)
                inv_date = timezone.localtime(inv.date).strftime('%d/%m/%Y %H:%M') if hasattr(inv.date, 'tzinfo') else inv.date.strftime('%d/%m/%Y %H:%M')
                inv_total = float(inv.total or 0)
                payment_method = (getattr(inv, 'payment_method', '') or '').strip()
                status_value = (getattr(inv, 'status', '') or '').strip()
                es_credito = (payment_method.lower() == 'credit') or ('credito' in status_value.lower())
                tipo_pago = 'Crédito' if es_credito else 'Contado'

                if es_credito:
                    total_credito += inv_total
                else:
                    total_contado += inv_total

                items_pdf = []
                for it in inv.items.all():
                    item_name = getattr(it.item, 'name', None) or getattr(it.item, 'nombre', None) or str(it.item)
                    qty = int(it.quantity or 0)
                    price = float(it.price or 0)
                    subtotal = float(it.subtotal() if callable(getattr(it, 'subtotal', None)) else (qty * price))
                    items_pdf.append({
                        'name': item_name,
                        'qty': qty,
                        'price': price,
                        'subtotal': subtotal,
                    })

                invoices_pdf.append({
                    'cliente': customer_name,
                    'fecha': inv_date,
                    'factura_id': inv.id,
                    'tipo_pago': tipo_pago,
                    'total_factura': inv_total,
                    'items': items_pdf,
                })

            context = {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'periodo': periodo,
                'invoices': invoices_pdf,
                'totales': {
                    'contado': total_contado,
                    'credito': total_credito,
                    'general': total_contado + total_credito,
                },
            }

            return _render_pdf_with_puppeteer(
                'reports/reporte_pdf_ventas.html',
                context,
                filename=f"{filename_base}.pdf",
            )

        return JsonResponse({'error': 'Formato inválido. Usa pdf o excel.'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Ocurrió un error generando la descarga.'}, status=500)

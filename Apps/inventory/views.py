from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.conf import settings
from django.template.loader import render_to_string
from django.http import FileResponse
from django.urls import reverse
from .models import InventoryAdjustment, InventoryHistory
from item.models import Item

import os
import subprocess
import uuid

@login_required
def inventory_adjustment_create(request):
    items = Item.objects.all()

    download_id = request.GET.get('download')
    download_url = None
    if download_id:
        try:
            download_url = reverse('inventory_adjustment_receipt', args=[int(download_id)])
        except (TypeError, ValueError):
            download_url = None

    # Si es POST, registramos el ajuste
    if request.method == 'POST':
        item_id = request.POST.get('item')
        adjustment_type = request.POST.get('adjustment_type')
        quantity = int(request.POST.get('quantity'))
        reason = request.POST.get('reason')

        item = get_object_or_404(Item, id=item_id)
        stock_before = item.Stock

        if adjustment_type == 'OUT' and quantity > item.Stock:
            messages.error(request, "No hay suficiente stock para esta salida.")
            return redirect('inventory_adjustment_create')

        adjustment = InventoryAdjustment.objects.create(
            item=item,
            adjustment_type=adjustment_type,
            quantity=quantity,
            reason=reason,
            user=request.user
        )

        if adjustment_type == 'IN':
            item.Stock += quantity
        else:
            item.Stock -= quantity
        item.save()

        InventoryHistory.objects.create(
            adjustment=adjustment,
            stock_before=stock_before,
            stock_after=item.Stock
        )

        messages.success(request, "Ajuste de inventario registrado correctamente. Descargando comprobante...")
        return redirect(f"{reverse('inventory_adjustment_create')}?download={adjustment.id}")

    # Historial paginado
    adjustments_list = InventoryAdjustment.objects.select_related('item', 'user').order_by('-created_at')
    paginator = Paginator(adjustments_list, 10) 
    page_number = request.GET.get('page')
    adjustments = paginator.get_page(page_number)

    return render(request, 'inventory/inventory_adjustment_form.html', {
        'items': items,
        'adjustments': adjustments,
        'download_url': download_url,
    })


def _render_pdf_inline_with_puppeteer(template_src: str, context: dict, filename: str = "ReciboAjusteInventario.pdf", as_attachment: bool = True):
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

    if os.path.exists(html_path):
        os.remove(html_path)

    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    disposition = 'attachment' if as_attachment else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@login_required
def inventory_adjustment_receipt(request, adjustment_id: int):
    adjustment = get_object_or_404(
        InventoryAdjustment.objects.select_related('item', 'user'),
        id=adjustment_id
    )
    history = InventoryHistory.objects.filter(adjustment=adjustment).first()

    adjustment_code = f"AJI-{adjustment.created_at.strftime('%Y')}-{adjustment.id:04d}"

    responsable = (
        adjustment.user.get_full_name().strip()
        if hasattr(adjustment.user, 'get_full_name') and adjustment.user.get_full_name().strip()
        else adjustment.user.username
    )

    context = {
        'logo_url': 'https://raw.githubusercontent.com/Kevin25DC/celupro-assets/refs/heads/main/logo%20de%20prueba%20dos.png',
        'company_name': 'CELUPRO CO',
        'adjustment': adjustment,
        'history': history,
        'adjustment_code': adjustment_code,
        'responsable': responsable,
    }

    filename = f"Recibo_Ajuste_Inventario_{adjustment_code}.pdf"
    return _render_pdf_inline_with_puppeteer(
        'reports/reportsInventory/ajusteInventario.html',
        context,
        filename=filename
    )

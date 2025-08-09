from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import InventoryAdjustment, InventoryHistory
from item.models import Item

@login_required
def inventory_adjustment_create(request):
    items = Item.objects.all()

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

        messages.success(request, "Ajuste de inventario registrado correctamente.")
        return redirect('inventory_adjustment_create')

    # Historial paginado
    adjustments_list = InventoryAdjustment.objects.select_related('item', 'user').order_by('-created_at')
    paginator = Paginator(adjustments_list, 10)  # 10 por página
    page_number = request.GET.get('page')
    adjustments = paginator.get_page(page_number)

    return render(request, 'inventory/inventory_adjustment_form.html', {
        'items': items,
        'adjustments': adjustments
    })

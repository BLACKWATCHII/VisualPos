from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from tax.models import Tax


@login_required
def createTax(request):
    if request.method == 'POST':
        name = (request.POST.get('Name') or '').strip()
        raw_rate = (request.POST.get('Percentaje') or '').strip().replace(',', '.')
        try:
            rate = Decimal(raw_rate)
        except InvalidOperation:
            rate = None

        if not name:
            messages.error(request, 'Escribe el nombre del impuesto.')
        elif rate is None or rate <= 0 or rate > 100:
            messages.error(request, 'El porcentaje debe ser un número mayor a 0 y hasta 100.')
        elif Tax.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Ya existe un impuesto llamado "{name}".')
        else:
            Tax.objects.create(name=name, rate=rate, user=request.user)
            messages.success(request, f'Impuesto "{name}" creado.')
            return redirect('createTax')

    taxes = Tax.objects.order_by('name')
    return render(request, 'tax/createTax.html', {'taxes': taxes, 'posted': request.POST if request.method == 'POST' else None})

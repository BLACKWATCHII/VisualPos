from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from tax.models import Tax
from django.contrib import messages

@login_required
def createTax(request):  
    if request.method == 'POST':
        Name = request.POST.get('Name')
        percentaje = request.POST.get('Percentaje')
        percentajeInt = int(percentaje)

        if Tax.objects.filter(name=Name).exists():
                    messages.error(request, 'Ya existe un nombre .')
                    return render(request, 'items/createItem.html')
        if percentajeInt < 0:
            messages.error(request,'El porcentaje es mejor a 0')
            return render(request,'tax/createTax')
        Tax.objects.create(
            name=Name,
            rate=percentajeInt,
            user=request.user
        )
        messages.success(request, 'Tax creado correctamente.')
        return redirect('viewItem')
    return render(request,'tax/createTax.html')

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from item.models import Item
import os
from django.http import FileResponse, HttpResponseNotFound
from tax.models import Tax
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError

# Create item and view
@login_required
def item(request):
    items = Item.objects.all()  
    context = {
        'item': items,  
    }
    return render(request, 'items/viewItem.html', context)

def download_plant(request):
    file_path = os.path.join(settings.BASE_DIR, 'static/archived/Customers.xlsx')
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Customers.xlsx"'
        return response
    else:
        return HttpResponseNotFound("El archivo no existe.")



@login_required
def CreateItem(request):
    print("Entrando en la vista CreateItem")
    taxes = Tax.objects.all()

    if request.method == 'POST':
        print("Método POST detectado")
        name = request.POST.get('Name')
        referents = request.POST.get('Referents') 
        description = request.POST.get('Description')
        price = request.POST.get('Price')
        stock = request.POST.get('Stock')
        active = request.POST.get('active')

        if not (name and referents and description and price and stock and active):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'items/createItem.html', {'taxes': taxes})
        
        active = (active == 'True')

        try:
            price = float(price)
            stock = float(stock)
        except (ValueError, TypeError):
            messages.error(request, 'Los campos Precio y Cantidad deben ser números válidos.')
            return render(request, 'items/createItem.html', {'taxes': taxes})

        try:
            if Item.objects.filter(Referents=referents).exists():  
                print("Referencia duplicada")
                messages.error(request, 'Ya existe un ítem con esa referencia.')
                return render(request, 'items/createItem.html', {'taxes': taxes})

            Item.objects.create(
                Name=name,  
                Referents=referents,  
                Description=description, 
                Price=price,  
                Stock=stock,  
                active=active,
                user=request.user
            )
            messages.success(request, 'Ítem creado correctamente.')
            return redirect('viewItem')
        except IntegrityError as e:
            print(f"Error de integridad: {e}")
            messages.error(request, 'Hubo un problema al crear el ítem.')
            return render(request, 'items/createItem.html', {'taxes': taxes})
    return render(request, 'items/createItem.html', {'taxes': taxes})



@login_required
def DeleteItem(request,item_id):
    print(item_id)
    itemID = get_object_or_404(Item, id=item_id)
    itemID.delete()
    return redirect('viewItem')

@login_required
def UpdateItem(request,item_id):
    itemID = get_object_or_404(Item, id=item_id)
    return render(request,'item/UpdateItem.html',{'item',itemID})



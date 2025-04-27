from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from item.models import Item
import os
from django.http import FileResponse, HttpResponseNotFound
from tax.models import Tax
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
import os
import pandas as pd


@login_required
def item(request):
    items = Item.objects.all()  
    context = {
        'items': items,  
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
def UpdateItem(request, item_id):
    itemID = get_object_or_404(Item, id=item_id)
    taxes = Tax.objects.all()

    if request.method == 'POST':
        name = request.POST.get('Name')
        referents = request.POST.get('Referents')
        description = request.POST.get('Description')
        price = request.POST.get('Price')
        stock = request.POST.get('Stock')
        active = request.POST.get('active')
        tax_id = request.POST.get('Taxes')


        if not (name and referents and description and price and stock and active and tax_id):
            return JsonResponse({'error': 'Todos los campos son obligatorios.'}, status=400)

        try:
            price = float(price)
            stock = float(stock)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Precio y Cantidad deben ser números válidos.'}, status=400)

        try:
            tax = Tax.objects.get(id=tax_id)
        except Tax.DoesNotExist:
            return JsonResponse({'error': 'El impuesto seleccionado no existe.'}, status=400)
        
        itemID.Name = name
        itemID.Referents = referents
        itemID.Description = description
        itemID.Price = price
        itemID.Stock = stock
        itemID.active = (active == 'True')
        itemID.Taxes = tax
        itemID.save()

        return JsonResponse({'redirect': reverse('viewItem')})

    return render(request, 'items/UpdateItem.html', {'item': itemID, 'taxes': taxes})

@login_required
def import_datos_excel(request):
    print("entre")
    if request.method == 'POST' and request.FILES.get('archivo'):
        archived = request.FILES['archivo']
        referents_repeated = set()

        try:
            df = pd.read_excel(archived, dtype={'Referencia': str})
            print(df.columns)
            df = df.dropna(subset=['Referencia'])

            existing_referents = set(Item.objects.values_list('Referents', flat=True))

            new_items = []
            for _, row in df.iterrows():
                referents = str(row.get('Referencia', '')).strip()
                if referents in existing_referents:
                    referents_repeated.add(referents)
                    continue

                try:
                    new_items.append(
                        Item(
                            Name=safe_strip(row.get('Nombre', '')),
                            Referents=referents,
                            Description=safe_strip(row.get('Descripcion', '')),
                            Price=safe_strip(row.get('Precio', 0)),
                            Stock=safe_strip(row.get('Cantidad', 0)),
                            user=request.user
                        )
                    )
                except Exception as e:
                    print(f"Error procesando fila {row.to_dict()}: {e}")
                    continue

            if new_items:
                Item.objects.bulk_create(new_items)
                print(Item.objects.all())

            if referents_repeated:
                mensaje = f"Los siguientes registros no fueron importados porque ya existen: {', '.join(referents_repeated)}"
                return JsonResponse({'status': 'warning', 'message': mensaje, 'duplicados': list(referents_repeated)})
            else:
                return JsonResponse({'status': 'success', 'message': 'Datos cargados correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'No se recibió ningún archivo.'})

def safe_strip(value):
    return str(value).strip() if value is not None else ''



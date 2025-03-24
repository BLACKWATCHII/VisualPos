from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from .form import CustomUserCreationForm, CustomAuthenticationForm,ClienteForm
from customer.models import Cliente
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.db.models import Count
from item.models import Item
from tax.models import Tax
import os
import pandas as pd
import json
from django.contrib import messages
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings

# Login and register

def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html', {"form": CustomUserCreationForm()})
    else:
        if request.POST["password1"] == request.POST["password2"]:
            try:
                user = User.objects.create_user(
                    username=request.POST["username"], password=request.POST["password1"]
                )
                user.save()
                login(request, user)
                return redirect('Dasboard')
            except IntegrityError:
                return render(request, 'signup.html', {"form": CustomUserCreationForm(), "error": "El nombre de usuario ya existe."})
        return render(request, 'signup.html', {"form": CustomUserCreationForm(), "error": "Las contraseñas no coinciden."})


@login_required
def Dasboard(request):
    customer_count = Cliente.objects.count()
    items_count = Item.objects.filter(active=True).count()
    # Calculate new clients per day
    new_clients_per_day = (
        Cliente.objects
        .filter(record_date__isnull=False)
        .values('record_date')
        .annotate(count=Count('id'))
        .order_by('record_date')
    )

    # Prepare data for the chart
    dates = [entry['record_date'].strftime('%Y-%m-%d') for entry in new_clients_per_day]
    counts = [entry['count'] for entry in new_clients_per_day]

    context = {
        'num_clientes': customer_count,
        'num_items': items_count,
        'dates': json.dumps(dates),  # Convert list to JSON format
        'counts': json.dumps(counts),  
    }

    return render(request, 'tasks.html', context)


def home(request):
    return render(request, 'home.html')


@login_required
def signout(request):
    logout(request)
    return redirect('home')


def signin(request):
    storage = messages.get_messages(request)
    storage.used = True

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Login successful")
                return redirect('Dasboard')
            else:
                messages.error(request, "Incorrect username or password.")
        else:
            messages.error(request, "Incorrect username or password.")

    else:
        form = CustomAuthenticationForm()

    return render(request, 'signin.html', {'form': form})

################################################################################################################

## Create Customer and update customer
def cliente_create_view(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES)  
        if form.is_valid():
            form.save()
            return JsonResponse({'redirect': reverse('viewClient')})
        else:
            cedula_error = form.errors.get('cedula')
            if cedula_error:
                return JsonResponse({'error': cedula_error}, status=400)
    else:
        form = ClienteForm()
    return render(request, 'Customer/createCustomer.html', {'form': form})


@login_required
def view_Clients(request):
    clients = Cliente.objects.all()
    context = {
        'clients': clients,
    }
    print(context)
    return render(request, 'Customer/viewClient.html', context)

@login_required
def download_pdf(request, client_id):
    client = get_object_or_404(Cliente, id=client_id)
    pdf_path = client.pdf.path
    with open(pdf_path, 'rb') as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={os.path.basename(pdf_path)}'
        return response

@login_required
def preview_pdf(request, client_id):
    client = get_object_or_404(Cliente, id=client_id)
    pdf_path = client.pdf.path
    with open(pdf_path, 'rb') as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = 'inline'
        return response

@login_required
def update_cliente(request, client_id):
    client = get_object_or_404(Cliente, id=client_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            return JsonResponse({'redirect': reverse('viewClient')})
        else:
            cedula_error = form.errors.get('cedula')
            if cedula_error:
                return JsonResponse({'error': cedula_error}, status=400)
    else:
        form = ClienteForm(instance=client)
    return render(request, 'Customer/updateCustomer.html', {'form': form, 'client_id': client.id})

@login_required
def delete_cliente(request, client_id):
    client = get_object_or_404(Cliente, id=client_id)
    client.delete()
    return redirect('viewClient')   


@login_required
def export_clients_to_excel(request):
    clients = Cliente.objects.all()
    data = {
        'ID': [client.id for client in clients],
        'Cedula': [client.cedula for client in clients],
        'Nombre': [client.name for client in clients],
        'Apellido': [client.lastname for client in clients],
        'Telefono': [client.phone for client in clients]
    }

    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Clientes.xlsx'
    df.to_excel(response, index=False)
    
    return response

@login_required
def cargar_datos_excel(request):
    if request.method == 'POST' and request.FILES['archivo']:
        archivo = request.FILES['archivo']
        
        # Cargar el archivo Excel usando Pandas
        try:
            df = pd.read_excel(archivo)
            for index, row in df.iterrows():
                Cliente.objects.create(
                    cedula=row['Cedula'],
                    name=row['Nombre'],
                    lastname=row['Apellido'],
                    phone=row['Telefono']
                )
            return JsonResponse({'status': 'success', 'message': 'Datos cargados correctamente.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'No se recibió ningún archivo.'})
################################################################################################################

# Create item and view
@login_required
def item(request):
    items = Item.objects.all()  
    context = {
        'item': items,  
    }
    return render(request, 'items/viewItem.html', context)

def download_plant(request):
    file_path = os.path.join(settings.BASE_DIR, 'static/archived/Clientes.xlsx')
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Clientes.xlsx"'
        return response
    else:
        return HttpResponseNotFound("El archivo no existe.")

@login_required
def CreateItem(request):
    taxes = Tax.objects.all()
    if request.method == 'POST':
        name = request.POST.get('Name')
        referents = request.POST.get('Referents')  # Correct field name
        description = request.POST.get('Description')
        price = request.POST.get('Price')
        stock = request.POST.get('Stock')
        active = request.POST.get('active')
        # tax_id = request.POST.get('Taxes')  

        # if tax_id == None :
        #     tax_id = None

        # Validación de campos obligatorios
        if not (name and referents and description and price and stock and active):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'items/createItem.html', {'taxes': taxes})
        
        active = (active == 'True')

        try:
            price = float(price)
            stock = int(stock)
        except (ValueError, TypeError):
            messages.error(request, 'Los campos Precio y Cantidad deben ser números válidos.')
            return render(request, 'items/createItem.html', {'taxes': taxes})

        try:
            if Item.objects.filter(Referents=referents).exists():  # Correct field name
                messages.error(request, 'Ya existe un ítem con esa referencia.')
                return render(request, 'items/createItem.html', {'taxes': taxes})

            # tax = Tax.objects.get(id=tax_id) 

            Item.objects.create(
                Name=name,  
                Referents=referents,  
                Description=description, 
                Price=price,  
                Stock=stock,  
                active=active,
                # tax=tax,  
                user=request.user
            )
            messages.success(request, 'Ítem creado correctamente.')
            return redirect('viewItem')
        except IntegrityError:
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



#Create Tax
@login_required
def CreateTax(request):  
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

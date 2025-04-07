from django.shortcuts import render, redirect,get_object_or_404
from .forms import CustomerForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from customer.models import Customer
import os
import pandas as pd

## Create Customer and update customer
def Customer_create_view(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)  
        if form.is_valid():
            form.save()
            return JsonResponse({'redirect': reverse('viewClient')})
        else:
            cedula_error = form.errors.get('cedula')
            if cedula_error:
                return JsonResponse({'error': cedula_error}, status=400)
    else:
        form = CustomerForm()
    return render(request, 'Customer/createCustomer.html', {'form': form})


@login_required
def view_Clients(request):
    clients = Customer.objects.all()
    context = {
        'clients': clients,
    }
    print(context)
    return render(request, 'Customer/viewClient.html', context)

@login_required
def download_pdf(request, client_id):
    client = get_object_or_404(Customer, id=client_id)
    print(client)
    pdf_path = client.pdf.path
    with open(pdf_path, 'rb') as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={os.path.basename(pdf_path)}'
        return response


@login_required
def update_Customer(request, client_id):
    client = get_object_or_404(Customer, id=client_id)
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            return JsonResponse({'redirect': reverse('viewClient')})
        else:
            cedula_error = form.errors.get('cedula')
            if cedula_error:
                return JsonResponse({'error': cedula_error}, status=400)
    else:
        form = CustomerForm(instance=client)
    return render(request, 'Customer/updateCustomer.html', {'form': form, 'client_id': client.id})

@login_required
def delete_Customer(request, client_id):
    client = get_object_or_404(Customer, id=client_id)
    client.delete()
    return redirect('viewClient')   


@login_required
def export_clients_to_excel(request):
    clients = Customer.objects.all()
    data = {
        'ID': [client.id for client in clients],
        'Cedula': [client.cedula for client in clients],
        'Nombre': [client.name for client in clients],
        'Apellido': [client.lastname for client in clients],
        'Telefono': [client.phone for client in clients],
        'Email': [client.email for client in clients],
        'Direccion': [client.address for client in clients],
        'Ciudad': [client.city for client in clients]
    }
    
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Customers.xlsx'
    df.to_excel(response, index=False)
    
    return response

@login_required
def cargar_datos_excel(request):
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        cedulas_repetidas = []

        try:
            df = pd.read_excel(archivo, dtype={'Cedula': str})

            df = df.dropna(subset=['Cedula'])

            cedulas_existentes = set(Customer.objects.values_list('cedula', flat=True))

            customers_nuevos = []
            for _, row in df.iterrows():
                cedula = str(row.get('Cedula', '')).strip()
                if cedula in cedulas_existentes:
                    cedulas_repetidas.append(cedula)
                    continue

                try:
                    customers_nuevos.append(
                        Customer(
                            name=safe_strip(row.get('Nombre', '')),
                            lastname=safe_strip(row.get('Apellido', '')),
                            cedula=cedula,
                            phone=safe_strip(row.get('Telefono', '')),
                            neighborhood=safe_strip(row.get('Barrio', '')),
                            address=safe_strip(row.get('Direccion', '')),
                            email=safe_strip(row.get('Correo electronico', '')),
                            income=float(row.get('Ingreso mensual', 0) or 0),
                            source_of_income=safe_strip(row.get('Fuente de ingreso', '')),
                            employment_situation=safe_strip(row.get('Situacion laboral', '')),
                            producto_solicitados=safe_strip(row.get('Producto solicitado', ''))
                        )
                    )
                except Exception as e:
                    print(f"Error procesando fila {row.to_dict()}: {e}")
                    continue

            if customers_nuevos:
                Customer.objects.bulk_create(customers_nuevos)

            if cedulas_repetidas:
                mensaje = f"Los siguientes registros no fueron importados porque ya existen: {', '.join(cedulas_repetidas)}"
                return JsonResponse({'status': 'warning', 'message': mensaje, 'duplicados': cedulas_repetidas})
            else:
                return JsonResponse({'status': 'success', 'message': 'Datos cargados correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'No se recibió ningún archivo.'})

def safe_strip(value):
    return str(value).strip() if value is not None else ''
################################################################################################################


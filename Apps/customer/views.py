from django.shortcuts import render, redirect,get_object_or_404
from .forms import ClienteForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from customer.models import Cliente
import os
import pandas as pd

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
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        cedulas_repetidas = []  # Lista para almacenar cédulas duplicadas

        try:
            df = pd.read_excel(archivo, dtype={'Cedula': str})  # Asegurar que la cédula sea tratada como string
            
            # Eliminar filas con valores NaN en la columna Cedula
            df = df.dropna(subset=['Cedula'])

            cedulas_existentes = set(Cliente.objects.values_list('cedula', flat=True))  # Obtener cédulas existentes en la BD

            clientes_nuevos = []
            for _, row in df.iterrows():
                cedula = str(row['Cedula']).strip()  # Convertir a string y eliminar espacios extra
                if cedula in cedulas_existentes:
                    cedulas_repetidas.append(cedula)  # Guardar la cédula repetida
                else:
                    clientes_nuevos.append(
                        Cliente(
                            cedula=cedula,
                            name=row.get('Nombre', '').strip(),
                            lastname=row.get('Apellido', '').strip(),
                            phone=row.get('Telefono', '').strip()
                        )
                    )

            # Guardar solo los clientes nuevos
            if clientes_nuevos:
                Cliente.objects.bulk_create(clientes_nuevos)

            # Construcción de la respuesta
            if cedulas_repetidas:
                mensaje = f"Los siguientes registros no fueron importados porque ya existen: {', '.join(cedulas_repetidas)}"
                return JsonResponse({'status': 'warning', 'message': mensaje, 'duplicados': cedulas_repetidas})
            else:
                return JsonResponse({'status': 'success', 'message': 'Datos cargados correctamente.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'No se recibió ningún archivo.'})
################################################################################################################


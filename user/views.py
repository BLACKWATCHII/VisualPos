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
import os
import pandas as pd
import json


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
                return redirect('tasks')
            except IntegrityError:
                return render(request, 'signup.html', {"form": CustomUserCreationForm(), "error": "El nombre de usuario ya existe."})
        return render(request, 'signup.html', {"form": CustomUserCreationForm(), "error": "Las contraseñas no coinciden."})


@login_required
def Dasboard(request):
    customer_count = Cliente.objects.count()

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
        'dates': json.dumps(dates),  # Convert list to JSON format
        'counts': json.dumps(counts),  # Convert list to JSON format
    }

    return render(request, 'tasks.html', context)


def home(request):
    return render(request, 'home.html')


@login_required
def signout(request):
    logout(request)
    return redirect('home')


def signin(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('tasks')  
    else:
        form = CustomAuthenticationForm()
    return render(request, 'signin.html', {'form': form})

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

def item(request):
    return render(request, 'items/viewItem.html')

def createTax(request):
    return render(request,'tax/createTax.html')

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
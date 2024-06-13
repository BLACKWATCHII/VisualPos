from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from .form import CustomUserCreationForm, CustomAuthenticationForm,ClienteForm
from customer.models import Cliente
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
import os

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
def tasks(request):
    customer= Cliente.objects.count()
    context = {
        'num_clientes': customer  
    }
    return render(request, 'tasks.html',context)


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
        print(form)
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


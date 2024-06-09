from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .form import CustomUserCreationForm, CustomAuthenticationForm
from customer.models import Cliente
from customer.forms import ClienteForm

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
    # tasks = Task.objects.filter(user=request.user, datecompleted__isnull=True)
    return render(request, 'tasks.html')

@login_required
def customer(request):
    if request.method == 'GET':
        return render(request, 'Customer/createCustomer.html', {"form": ClienteForm()})

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

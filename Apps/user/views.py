from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from .form import CustomUserCreationForm, CustomAuthenticationForm,ClienteForm
from django.db.models import Count
from item.models import Item
from tax.models import Tax
import os
import pandas as pd
import json
from django.contrib import messages
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings
from customer.models import Cliente

# Login and register

def home(request):
    return render(request, 'home.html')

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




@login_required 
def signout(request): #Fixed delete cookies token crfsr
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







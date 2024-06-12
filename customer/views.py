from django.shortcuts import render, redirect
from .forms import ClienteForm
from django.contrib.auth.decorators import login_required
from models import Cliente



# def customer(request):
#     if request.method == 'GET':
#         return render(request, 'Customer/createCustomer.html', {"form": ClienteForm()})



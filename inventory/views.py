from django.shortcuts import render
from .models import Inventory

# Create your views here.

def view_inventory(request):
    views = Inventory.objects.all()
    print(views)
from django.urls import path
from . import views

urlpatterns = [
    path('ajuste/', views.inventory_adjustment_create, name='inventory_adjustment_create'),
]
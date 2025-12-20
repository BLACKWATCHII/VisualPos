from django.urls import path
from . import views

urlpatterns = [
    path('ajuste/', views.inventory_adjustment_create, name='inventory_adjustment_create'),
    path('ajuste/<int:adjustment_id>/recibo/', views.inventory_adjustment_receipt, name='inventory_adjustment_receipt'),
]
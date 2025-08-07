from django.urls import path
from . import views

urlpatterns = [
    path('adjustInventory/', views.ajustesInventario, name='adjustInventory'),
]   
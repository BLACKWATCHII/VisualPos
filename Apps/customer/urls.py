from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_items, name='lista_items'),  
    path('<int:id>/', views.detalle_item, name='detalle_item'), 
]
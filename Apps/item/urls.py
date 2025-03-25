from django.urls import path
from . import views

urlpatterns = [
    path('viewItem/', views.item, name='viewItem'),
    path('createItem/',views.CreateItem, name='createItem'),
    path('update/<int:item_id>/', views.UpdateItem, name='UpdateItem'),
    path('descargar-plantilla/', views.download_plant, name='descargar_plantilla'),
]   
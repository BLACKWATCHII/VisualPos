from django.urls import path
from . import views

urlpatterns = [
    path('viewItem/', views.item, name='viewItem'),
    path('createItem/',views.CreateItem, name='createItem'),
    path('update/<int:item_id>/', views.UpdateItem, name='updateItem'),
    path('descargar-plantilla/', views.download_plant, name='descargar_plantilla'),
    path('delete/<int:item_id>/', views.DeleteItem, name='deleteItem'),
    path('cargar-datos-excel/', views.import_datos_excel, name='import_data_excel'),
]   
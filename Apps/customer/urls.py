from django.urls import path
from . import views

urlpatterns = [
    # customer
    path('createCustomer/', views.cliente_create_view, name='createCustomer'),
    path('viewClient/', views.view_Clients, name='viewClient'),
    path('clients/<int:client_id>/preview/', views.preview_pdf, name='preview_pdf'),
    path('update_cliente/<int:client_id>/', views.update_cliente, name='update_cliente'),
    path('delete_cliente/<int:client_id>/', views.delete_cliente, name='delete_cliente'),
    path('export_clients_to_excel/', views.export_clients_to_excel, name='export_clients_to_excel'),
    path('cargar-datos-excel/', views.cargar_datos_excel, name='cargar_datos_excel'),
    path('clients/<int:client_id>/download/', views.download_pdf, name='download_pdf'),
    #################################################################################### 
]
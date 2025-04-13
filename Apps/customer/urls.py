from django.urls import path
from . import views

urlpatterns = [
    # customer
    path('createCustomer/', views.Customer_create_view, name='createCustomer'),
    path('viewClient/', views.view_Clients, name='viewClient'),
    path('update_Customer/<int:client_id>/', views.update_Customer, name='update_Customer'),
    path('delete_Customer/<int:client_id>/', views.delete_Customer, name='delete_Customer'),
    path('export_clients_to_excel/', views.export_clients_to_excel, name='export_clients_to_excel'),
    path('cargar-datos-excel/', views.cargar_datos_excel, name='cargar_datos_excel'),
    path('clients/<int:client_id>/download/', views.download_pdf, name='download_pdf'),
    #################################################################################### 
]
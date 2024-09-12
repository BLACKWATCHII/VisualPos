"""visualpos URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from user import views

urlpatterns = [

    ## login and register
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('signup/', views.signup, name='signup'),
    path('Dasboard/', views.Dasboard, name='Dasboard'),
    path('logout/', views.signout, name='logout'),
    path('signin/', views.signin, name='signin'),
    ##################################################################################

    # customer
    path('createCustomer/', views.cliente_create_view, name='createCustomer'),
    path('viewClient/', views.view_Clients, name='viewClient'),
    path('clients/<int:client_id>/preview/', views.preview_pdf, name='preview_pdf'),
    path('update_cliente/<int:client_id>/', views.update_cliente, name='update_cliente'),
    path('export_clients_to_excel/', views.export_clients_to_excel, name='export_clients_to_excel'),
    path('clients/<int:client_id>/download/', views.download_pdf, name='download_pdf'),
    ####################################################################################

    #item
    path('viewItem/', views.item, name='viewItem'),
    path('createItem/',views.CreateItem, name='createItem'),
    path('update/<int:item_id>/', views.UpdateItem, name='UpdateItem'),
    path('createTax/',views.CreateTax, name='createTax'),
    path('export/items/', views.export_items_to_excel, name='export_items_to_excel'),
    ###################################################################################



     
]
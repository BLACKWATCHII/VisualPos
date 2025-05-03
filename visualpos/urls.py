from django.contrib import admin
from django.urls import path,include
from Apps.user import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('Customer/', include('customer.urls')),  
    path('items/', include('item.urls')), 
    path('tax/', include('tax.urls')),
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('Dasboard/', views.Dashboard, name='Dasboard'),
    path('Profile/',views.profile_view,name = 'Profile'),
    path('editar-perfil/', views.edit_profile_view, name='edit_profile'),
    path('logout/', views.signout, name='logout'),
    path('signin/', views.signin, name='signin'),
    path('invoice/', include('Invoice.urls')),
]

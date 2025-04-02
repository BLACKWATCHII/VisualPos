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
    path('Dasboard/', views.Dasboard, name='Dasboard'),
    path('logout/', views.signout, name='logout'),
    path('signin/', views.signin, name='signin'),
]

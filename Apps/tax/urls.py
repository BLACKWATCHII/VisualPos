from django.urls import path
from . import views

urlpatterns = [
    path('createTax/',views.createTax, name='createTax'),
]   
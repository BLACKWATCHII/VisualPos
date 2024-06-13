from django.contrib import admin
from customer.models import Cliente
from item.models import Item

admin.site.register(Cliente)
admin.site.register(Item)
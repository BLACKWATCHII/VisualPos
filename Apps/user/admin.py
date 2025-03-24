from django.contrib import admin
from customer.models import Cliente
from item.models import Item
from tax.models import Tax
from inventory.models import Inventory

admin.site.register(Cliente)
admin.site.register(Item)
admin.site.register(Tax)
admin.site.register(Inventory)
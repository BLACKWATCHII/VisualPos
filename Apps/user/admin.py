from django.contrib import admin
from customer.models import Customer
from item.models import Item
from tax.models import Tax
from inventory.models import Inventory

admin.site.register(Customer)
admin.site.register(Item)
admin.site.register(Tax)
admin.site.register(Inventory)
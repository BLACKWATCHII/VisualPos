from django.db import models
from django.contrib.auth.models import User
from item.models import Item

class Inventory(models.Model):
    items = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='inventarios')
    quantity = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventarios')

    def __str__(self):
        return f"{self.items.Name} - {self.quantity}"

from django.db import models
from django.contrib.auth.models import User
from item.models import Item 

class InventoryAdjustment(models.Model):
    ADJUSTMENT_TYPE = [
        ('IN', 'Entrada'),
        ('OUT', 'Salida'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="adjustments")
    adjustment_type = models.CharField(max_length=3, choices=ADJUSTMENT_TYPE)
    quantity = models.IntegerField()
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.get_adjustment_type_display()} - {self.item.Name} ({self.quantity})"

class InventoryHistory(models.Model):
    adjustment = models.ForeignKey(InventoryAdjustment, on_delete=models.CASCADE, related_name="history")
    stock_before = models.IntegerField()
    stock_after = models.IntegerField()
    change_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Historial {self.adjustment.item.Name} - {self.change_date.strftime('%Y-%m-%d %H:%M')}"

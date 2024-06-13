from django.db import models

class Item(models.Model):
    Name = models.CharField(max_length=255)
    Referents = models.TextField(blank=True, null=True)
    Description = models.TextField(blank=True, null=True)
    Price = models.DecimalField(max_digits=10, decimal_places=2)
    Stock = models.IntegerField(default=0)
    create_date = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

from django.db import models

class Tax(models.Model):
    name = models.CharField(max_length=255)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text='Rate in percentage (%)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
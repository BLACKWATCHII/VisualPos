from django.db import models

class Cliente(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")
    lastname = models.CharField(max_length=100, verbose_name="Apellido")
    address = models.CharField(max_length=255, verbose_name="Dirección")
    city = models.CharField(max_length=100, verbose_name="Ciudad")
    cedula = models.CharField(max_length=20, verbose_name="Cédula")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    email = models.EmailField(max_length=100, verbose_name="Correo electrónico")
    record_date = models.DateField(verbose_name="Fecha de registro", auto_now_add=True)
    pdf = models.FileField(upload_to='pdfs/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} {self.lastname}"

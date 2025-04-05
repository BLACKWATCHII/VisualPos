from django.db import models

class Customer(models.Model):
    Name = models.CharField(max_length=100, verbose_name="Nombre")
    LastName = models.CharField(max_length=100, verbose_name="Apellido")
    Address = models.CharField(max_length=255, verbose_name="Dirección")
    City = models.CharField(max_length=100, verbose_name="Ciudad")
    Neighborhood = models.TextField(max_length=100, verbose_name="Vecindario")
    Cedula = models.CharField(max_length=20, verbose_name="Cédula")
    Phone = models.CharField(max_length=20, verbose_name="Teléfono")
    Email = models.EmailField(max_length=100, verbose_name="Correo electrónico")
    Income = models.DecimalField(max_digits=60,decimal_places=2, verbose_name="Ingresos")
    SourceOfIncome = models.TextField(max_length=100, verbose_name="Ocupacion del Cliente")
    EmploymentSituation = models.TextField(max_length=100,verbose_name="Situacion laboral del Cliente")
    ProductoSolicitados = models.TextField(max_length=100,verbose_name="Producto solicitado")
    Record_date = models.DateField(verbose_name="Fecha de registro", auto_now_add=True)
    Pdf = models.FileField(upload_to='pdfs/', blank=True, null=True)

    def __str__(self):
        return f"{self.Name} {self.LastName}"

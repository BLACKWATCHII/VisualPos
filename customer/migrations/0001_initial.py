# Generated by Django 4.1 on 2024-06-14 02:30

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nombre')),
                ('lastname', models.CharField(max_length=100, verbose_name='Apellido')),
                ('address', models.CharField(max_length=255, verbose_name='Dirección')),
                ('city', models.CharField(max_length=100, verbose_name='Ciudad')),
                ('cedula', models.CharField(max_length=20, verbose_name='Cédula')),
                ('phone', models.CharField(max_length=20, verbose_name='Teléfono')),
                ('email', models.EmailField(max_length=100, verbose_name='Correo electrónico')),
                ('record_date', models.DateField(auto_now_add=True, verbose_name='Fecha de registro')),
                ('pdf', models.FileField(blank=True, null=True, upload_to='pdfs/')),
            ],
        ),
    ]

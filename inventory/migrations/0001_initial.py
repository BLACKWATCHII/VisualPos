# Generated by Django 4.1 on 2025-03-17 19:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('item', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Inventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('items', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventarios', to='item.item')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventarios', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

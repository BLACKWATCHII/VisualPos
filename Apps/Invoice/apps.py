from django.apps import AppConfig

class InvoiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Invoice'

    def ready(self):
        try:
            from Invoice.models import TransactionType
            obj, created = TransactionType.objects.get_or_create(
                tra_type="Factura de venta",
                defaults={
                    'consecutive': 1,
                    'iniType': 'FV',
                    'user_id': 1
                }
            )
            if created:
                print("Tipo de transacción 'Factura de venta' creado.")
        except Exception as e:
            print(f"Error al crear el tipo de transacción 'Factura': {e}")
from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'  # ajusta esto al nombre real de tu app

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.utils import OperationalError, ProgrammingError

        User = get_user_model()
        try:
            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser(
                    username="admin",
                    email="admin@example.com",
                    password="1030",
                    
                )
                print("Superusuario creado: admin / 1030")
        except (OperationalError, ProgrammingError):
            # Esto evita errores si la BD aún no está lista (por ejemplo, en migrate)
            pass

from django.urls import path
from . import views

urlpatterns = [

    path('ventas-generales/', views.menu_reportes, name='menu_reportes'),
    path('reportes-generales/', views.reports_general, name='reports_general'),

    # API (JSON + descargas)
    path('api/ventas/datos/', views.api_ventas_datos, name='api_ventas_datos'),
    path('api/ventas/descargar/', views.api_ventas_descargar, name='api_ventas_descargar'),
]
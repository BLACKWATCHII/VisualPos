from django.urls import path
from . import views

urlpatterns = [

    path('ventas-generales/', views.menu_reportes, name='menu_reportes'),
    path('reportes-generales/', views.reports_general, name='reports_general'),
    path('reportes-productos/', views.reports_productos, name='reports_productos'),

    # API (JSON + descargas)
    path('api/ventas/datos/', views.api_ventas_datos, name='api_ventas_datos'),
    path('api/ventas/descargar/', views.api_ventas_descargar, name='api_ventas_descargar'),

    # API productos
    path('api/ventas-productos/datos/', views.api_ventas_productos_datos, name='api_ventas_productos_datos'),
    path('api/ventas-productos/descargar/', views.api_ventas_productos_descargar, name='api_ventas_productos_descargar'),
]
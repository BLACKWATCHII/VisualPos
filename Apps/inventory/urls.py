from django.urls import path
from . import views

urlpatterns = [
    path('ajuste/', views.inventory_adjustment_create, name='inventory_adjustment_create'),
    path('ajuste/<int:adjustment_id>/recibo/', views.inventory_adjustment_receipt, name='inventory_adjustment_receipt'),

    # Exportaciones por rango de fechas
    path('ajuste/exportar/pdf/', views.exportar_ajustes_inventario_pdf, name='exportar_ajustes_inventario_pdf'),
    path('ajuste/exportar/excel/', views.exportar_ajustes_inventario_excel, name='exportar_ajustes_inventario_excel'),
]
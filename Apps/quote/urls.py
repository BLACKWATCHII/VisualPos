from django.urls import path

from . import views

urlpatterns = [
    path('', views.quote_list, name='quote_list'),
    path('nueva/', views.quote_create, name='quote_create'),
    path('<int:quote_id>/editar/', views.quote_edit, name='quote_edit'),
    path('<int:quote_id>/ver/', views.quote_preview, name='quote_preview'),
    path('<int:quote_id>/pdf/', views.quote_pdf, name='quote_pdf'),
    path('<int:quote_id>/anular/', views.quote_cancel, name='quote_cancel'),
    # API usada por la pantalla de facturación (botón "Traer cotización")
    path('api/pendientes/', views.quote_pending_api, name='quote_pending_api'),
    path('api/<int:quote_id>/', views.quote_detail_api, name='quote_detail_api'),
]

from django.urls import path

from . import views


urlpatterns = [
	path('connect/', views.conexion_whatsapp, name='conexion_whatsapp'),
	path('api/qr/', views.whatsapp_qr_status, name='whatsapp_qr_status'),
	path('api/logout/', views.whatsapp_logout, name='whatsapp_logout'),
	path('api/send-file/', views.send_file_whatsapp, name='send_file_whatsapp'),
	path('send-invoice/<int:invoice_id>/', views.send_invoice_whatsapp, name='send_invoice_whatsapp'),
	path('ping-evolution/', views.ping_evolution, name='ping_evolution'),
]


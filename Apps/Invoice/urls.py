from django.urls import path
from . import views

urlpatterns = [
    path('create-invoice/', views.create_invoice, name='create_invoice'),
    path('report-invoice/',views.invoices_report,name='report_invoice'),
    path('invoice/pdf/<int:invoice_id>/', views.invoice_pdf, name='invoice_pdf'),
    path('payment-quota',views.View_quota, name = 'payment_quota'),
    path('create-transaction', views.create_type_transaction, name ='create_transaction')
]
from django.urls import path
from . import views

urlpatterns = [
    path('create-invoice/', views.create_invoice, name='create_invoice'),
    path('report-invoice/',views.invoices_report,name='report_invoice'),
    path('invoice/pdf/<int:invoice_id>/', views.invoice_pdf, name='invoice_pdf'),
    path('payment-quota',views.View_quota, name = 'payment_quota'),
    path('create-transaction', views.create_type_transaction, name ='create_transaction'),
    path('edit-transaction/<int:transaction_id>/', views.edit_type_transaction, name ='edit_transaction'),
    path('delete-transaction/<int:transaction_id>/', views.delete_type_transaction, name ='delete_transaction'),
    path('quota/pay/<int:quota_id>/', views.pay_quota, name='pay_quota'),
    path('payment/history/', views.payment_history, name='payment_history'),
    path('invoice/quota/',views.View_quota, name='view_quota'),
    path('quotaCustomer/', views.View_quota_customer, name='payment_quota_customer'),
    path('factura-preview/<int:invoice_id>/', views.preview_invoice, name='preview_invoice'),
    path('anular-factura', views.cancel_invoice_view, name='cancel_factura'),
]
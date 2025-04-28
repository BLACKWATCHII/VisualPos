from django.urls import path
from . import views

urlpatterns = [
    path('create-invoice/', views.create_invoice, name='create_invoice'),
    path('report-invoice/',views.invoices_report,name='report_invoice'),
]
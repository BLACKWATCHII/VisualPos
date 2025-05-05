
    function showInvoiceDetails(id) {
        const invoice = invoices.find(inv => inv.id === id);
        if (invoice) {
            document.getElementById('detailInvoiceNumber').innerText = `Factura #${invoice.invoice_number}`;
            document.getElementById('detailCustomer').innerText = invoice.customer_name;
            document.getElementById('detailTotal').innerText = invoice.total;
            document.getElementById('detailDiscount').innerText = invoice.discount;
            document.getElementById('detailPayment').innerText = invoice.payment_method;
            document.getElementById('detailStatus').innerText = invoice.status;
            document.getElementById('detailNotes').innerText = invoice.notes || 'Sin notas';
            document.getElementById('invoiceDetails').style.display = 'block';
        }
    }

    function filterStatus(status) {
        const rows = document.querySelectorAll('#invoiceTable tbody tr');
        rows.forEach(row => {
            if (status === '' || row.getAttribute('data-status') === status) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }


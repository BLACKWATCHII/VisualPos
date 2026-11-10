// Pago y anulación de cuotas (compartido por "Pagar cuota" y "Deudas por cliente").
document.addEventListener('DOMContentLoaded', function () {
  const payModal = document.getElementById('payModal');
  const confirmPayButton = document.getElementById('confirmPayButton');
  const inputAmount = document.getElementById('modalPayAmount');
  let currentActionUrl = '';

  const money = (value) => new Intl.NumberFormat('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(value);
  const getCSRFToken = () => document.querySelector('[name=csrfmiddlewaretoken]').value;

  function parseFilename(cd, fallback) {
    if (!cd) return fallback;
    const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(cd);
    const name = match && (match[1] || match[2]);
    return name ? decodeURIComponent(name) : fallback;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  if (payModal) {
    payModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const balance = parseFloat(button.getAttribute('data-balance'));
      currentActionUrl = button.getAttribute('data-url');
      document.getElementById('modalInvoice').textContent = '#' + button.getAttribute('data-invoice');
      document.getElementById('modalDate').textContent = button.getAttribute('data-date');
      document.getElementById('modalBalance').textContent = money(balance);
      inputAmount.max = balance.toFixed(2);
      inputAmount.value = balance.toFixed(2);
      setTimeout(() => inputAmount.select(), 300);
    });

    confirmPayButton.addEventListener('click', function () {
      const payValue = parseFloat(inputAmount.value);
      if (isNaN(payValue) || payValue <= 0 || payValue > parseFloat(inputAmount.max)) {
        Swal.fire({ icon: 'warning', title: 'Importe inválido', text: 'Ingrese un valor mayor a 0 y que no supere el saldo de la cuota.' });
        return;
      }
      const originalHTML = confirmPayButton.innerHTML;
      confirmPayButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando…';
      confirmPayButton.disabled = true;

      fetch(currentActionUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCSRFToken() },
        body: new URLSearchParams({ amount: payValue })
      })
        .then(async (response) => {
          if (!response.ok) throw new Error('Error al procesar el pago');
          return { blob: await response.blob(), cd: response.headers.get('content-disposition') };
        })
        .then(({ blob, cd }) => {
          downloadBlob(blob, parseFilename(cd, 'ReciboPagoCuota.pdf'));
          bootstrap.Modal.getInstance(payModal).hide();
          Swal.fire({ icon: 'success', title: 'Pago registrado', text: 'Se descargó el recibo.', timer: 900, showConfirmButton: false })
            .then(() => location.reload());
        })
        .catch(() => {
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo procesar el pago. Intente nuevamente.' });
        })
        .finally(() => {
          confirmPayButton.innerHTML = originalHTML;
          confirmPayButton.disabled = false;
        });
    });
  }

  // Anular cuota pagada
  document.querySelectorAll('form.js-reverse-quota').forEach((form) => {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const invoice = form.getAttribute('data-invoice') || '';
      const dueDate = form.getAttribute('data-date') || '';
      Swal.fire({
        title: '¿Anular esta cuota?',
        html: `${invoice ? `<b>Factura:</b> ${invoice}<br>` : ''}${dueDate ? `<b>Vencimiento:</b> ${dueDate}<br>` : ''}Se eliminarán los pagos registrados y la cuota volverá a quedar pendiente.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc2626',
        confirmButtonText: 'Sí, anular',
        cancelButtonText: 'Cancelar'
      }).then((result) => {
        if (!result.isConfirmed) return;
        const btn = form.querySelector('button[type="submit"]');
        const originalBtnHtml = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }

        fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { 'X-CSRFToken': getCSRFToken(), 'X-Requested-With': 'XMLHttpRequest' }
        })
          .then(async (response) => {
            if (!response.ok) throw new Error((await response.text()) || 'Error al anular la cuota');
            return { blob: await response.blob(), cd: response.headers.get('content-disposition') };
          })
          .then(({ blob, cd }) => {
            downloadBlob(blob, parseFilename(cd, 'Comprobante_Anulacion_Cuota.pdf'));
            Swal.fire({ icon: 'success', title: 'Cuota anulada', text: 'Se generó el comprobante de anulación.', timer: 1100, showConfirmButton: false })
              .then(() => location.reload());
          })
          .catch((err) => {
            Swal.fire({ icon: 'error', title: 'Error', text: (err && err.message) || 'No se pudo anular la cuota' });
          })
          .finally(() => {
            if (btn) { btn.disabled = false; btn.innerHTML = originalBtnHtml; }
          });
      });
    });
  });
});

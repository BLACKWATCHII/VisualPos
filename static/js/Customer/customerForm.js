// Formulario de cliente (crear y editar): envío por fetch, validación y mensajes.
document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('customerForm');
  if (!form) return;
  var btn = document.getElementById('submitBtn');
  var spinner = document.getElementById('spinner');
  var text = document.getElementById('submitText');
  var label = text.textContent;

  var cedula = document.getElementById('id_cedula');
  if (cedula) {
    cedula.setAttribute('maxlength', '10');
    cedula.setAttribute('inputmode', 'numeric');
    cedula.addEventListener('input', function () { this.value = this.value.replace(/\D/g, '').slice(0, 10); });
  }

  function setBusy(busy) {
    btn.disabled = busy;
    spinner.classList.toggle('d-none', !busy);
    text.textContent = busy ? 'Guardando…' : label;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    form.querySelectorAll('.is-invalid').forEach(function (el) { el.classList.remove('is-invalid'); });

    var missing = Array.prototype.filter.call(form.querySelectorAll('[required]'), function (f) {
      return f.type !== 'file' && !String(f.value || '').trim();
    });
    if (missing.length) {
      missing.forEach(function (f) { f.classList.add('is-invalid'); });
      missing[0].focus();
      return;
    }

    setBusy(true);
    fetch(form.action || window.location.pathname, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
      .then(function (res) {
        if (res.ok && res.data.redirect) {
          Swal.fire({ icon: 'success', title: 'Cliente guardado', showConfirmButton: false, timer: 700 })
            .then(function () { window.location.href = res.data.redirect; });
          return;
        }
        setBusy(false);
        var errors = res.data.errors || {};
        Object.keys(errors).forEach(function (field) {
          var input = document.getElementById('id_' + field);
          if (input) input.classList.add('is-invalid');
        });
        var msg = Array.isArray(res.data.error) ? res.data.error[0] : (res.data.error || 'Revisa los datos del formulario.');
        Swal.fire({ icon: 'error', title: 'No se pudo guardar', text: msg });
      })
      .catch(function () {
        setBusy(false);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo procesar la solicitud. Intenta de nuevo.' });
      });
  });
});

// Comportamiento del shell: abrir/cerrar la barra lateral en pantallas pequeñas.
(function () {
  var body = document.body;
  document.querySelectorAll('[data-sidebar-toggle]').forEach(function (el) {
    el.addEventListener('click', function () { body.classList.toggle('sidebar-open'); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') body.classList.remove('sidebar-open');
  });

  // Selectores con búsqueda: cualquier <select class="js-select2">
  if (window.jQuery && jQuery.fn.select2) {
    jQuery('select.js-select2').each(function () {
      jQuery(this).select2({ width: '100%', placeholder: jQuery(this).find('option:first').text() });
    });
  }
})();

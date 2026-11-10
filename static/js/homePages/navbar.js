// Confirmación al cerrar sesión. El botón solo existe con sesión iniciada.
document.addEventListener('DOMContentLoaded', function () {
  var logout = document.getElementById('logoutButton');
  if (!logout) return;
  logout.addEventListener('click', function (event) {
    event.preventDefault();
    Swal.fire({
      title: 'Cerrando sesión',
      text: 'Por favor, espere...',
      icon: 'info',
      timer: 1200,
      showConfirmButton: false,
      allowOutsideClick: false,
      allowEscapeKey: false,
      didOpen: function () { Swal.showLoading(); },
      willClose: function () { window.location.href = logout.getAttribute('href'); }
    });
  });
});

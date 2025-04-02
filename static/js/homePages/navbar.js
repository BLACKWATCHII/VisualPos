document.getElementById('logoutButton').addEventListener('click', function(event) {
    event.preventDefault();  

    Swal.fire({
      title: 'Cerrando sesión',
      text: 'Por favor, espere...',
      icon: 'info',
      timer: 2000,
      background: '#fff',
      showConfirmButton: false,
      iconColor: '#2f855a',
      allowOutsideClick:false,
      allowEscapeKey:false,
      
      onOpen: () => {
        Swal.showLoading();  
      },
      willClose: () => {
        window.location.href = '/logout';  
      }
    });
  });
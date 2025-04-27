$(document).ready(function() {
    $('#create-item-form').submit(function(event) {
        event.preventDefault();
        var formData = new FormData(this);

        Swal.fire({
            title: 'Actualizando...',
            text: 'Por favor espera',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        $.ajax({
            type: 'POST',
            url: window.location.pathname,
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                Swal.fire({
                    icon: 'success',
                    title: '¡Producto actualizado!',
                    showConfirmButton: false,
                    timer: 1500
                }).then(function() {
                    window.location.href = response.redirect;
                });
            },
            error: function(response) {
                Swal.close(); 
                if (response.status === 400) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error al actualizar',
                        text: response.responseJSON.error,
                    });
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error inesperado',
                        text: 'Intenta nuevamente más tarde.',
                    });
                }
            }
        });
    });
});

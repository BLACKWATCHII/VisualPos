$(document).ready(function() {

    $('#create-item-form').submit(function(event) {
        event.preventDefault();
        var formData = new FormData(this);

        Swal.fire({
            title: 'Guardando producto...',
            text: 'Por favor espera',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                Swal.fire({
                    icon: 'success',
                    title: '¡Producto creado!',
                    showConfirmButton: false,
                    timer: 1500
                }).then(function() {
                    window.location.href = '/items/viewItem/'; 
                });
            },
            error: function(response) {
                Swal.close();
                if (response.status === 400) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error en el formulario',
                        text: response.responseJSON.error,
                    });
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error inesperado',
                        text: 'Ocurrió un error, intenta más tarde.',
                    });
                }
            }
        });
    });
});

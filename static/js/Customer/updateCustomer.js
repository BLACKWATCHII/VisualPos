$(document).ready(function(){
    $('form').submit(function(event){
        event.preventDefault();
        var formData = new FormData(this);
        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: formData,
            processData: false,
            contentType: false,
            success: function(response){
                Swal.fire({
                    icon: 'success',
                    title: 'Actualizado exitosamente',
                    showConfirmButton: false,
                    timer: 1500
                }).then(function() {
                    window.location.href = response.redirect;
                });
            },
            error: function(response){
                if (response.status === 400) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: response.responseJSON.error,
                    });
                }
            }
        });
    });
});
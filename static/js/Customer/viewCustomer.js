
$(document).ready(function () {
    if ($.fn.DataTable) {
        setTimeout(() => {
            $('#clientsTable').DataTable({
                paging: true,
                searching: true,
                ordering: true,
                lengthChange: true,
                pageLength: 10,
                deferRender: true,
                language: {
                    search: "Buscar:",
                    lengthMenu: "Mostrar _MENU_ registros",
                    info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
                    paginate: {
                        previous: "Anterior",
                        next: "Siguiente"
                    }
                }
            });
        }, 500);
    } else {
        console.error('DataTable plugin no está cargado correctamente.');
    }

    $('#exportButton').on('click', function (event) {
        event.preventDefault(); // solo si es necesario
        const exportUrl = $(this).data('url');
        if (exportUrl) {
            window.location.href = exportUrl;
        } else {
            console.error("La URL de exportación no está definida.");
        }
    });
    

    // Manejar envío del formulario de carga de archivo Excel
    $('#formCargarArchivo').on('submit', function (event) {
        console.log("Interceptando submit de importación...");
        event.preventDefault();

        const fileInput = $('#archivoExcel')[0];
        if (fileInput.files.length === 0) {
            Swal.fire("Error", "Por favor, selecciona un archivo antes de cargar.", "error");
            return;
        }

        const formData = new FormData(this);
        const importUrl = $(this).data('url');

        if (!importUrl) {
            console.error("La URL de importación no está definida.");
            return;
        }

        $('#progresoCarga').show();

        const xhr = new XMLHttpRequest();
        xhr.open('POST', importUrl, true);

        xhr.upload.onprogress = function (event) {
            if (event.lengthComputable) {
                const porcentaje = (event.loaded / event.total) * 100;
                $('#progresoBarra').css('width', porcentaje + '%');
                $('#progresoPorcentaje').text(Math.round(porcentaje) + '%');
            }
        };

        xhr.onload = function () {
            console.log(xhr.responseText); 
            if (xhr.status == 200) {
                const respuesta = JSON.parse(xhr.responseText);

                if (respuesta.status === 'success') {
                    Swal.fire("Éxito", "Datos importados correctamente.", "success").then(() => location.reload());
                } else if (respuesta.status === 'warning') {
                    Swal.fire("Advertencia", respuesta.message, "warning").then(() => location.reload());
                } else {
                    Swal.fire("Error", respuesta.message, "error").then(() => location.reload());
                }
            } else {
                Swal.fire("Error", "Error al cargar el archivo", "error").then(() => location.reload());
            }
        };

        xhr.onerror = function () {
            Swal.fire("Error", "No se pudo conectar con el servidor.", "error");
        };

        xhr.send(formData);
    });

    // Manejar descarga de plantilla
    $(document).on('click', '#descargarPlantilla', function (event) {
        console.log("Descargando plantilla...");
        event.preventDefault();
        const archivo = '/static/archived/Customers.xlsx';
        const a = document.createElement("a");
        a.href = archivo;
        a.download = "Customers.xlsx";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });

    // Manejar eliminación de cliente (delegado)
    $(document).on('click', '.delete-btn', function (event) {
        event.preventDefault();

        const url = $(this).data('url');

        Swal.fire({
            title: `¿Estás seguro que quieres eliminar a este Cliente?`,
            text: "¡No podrás revertir esta acción!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed && url) {
                window.location.href = url;
            }
        });
    });
});

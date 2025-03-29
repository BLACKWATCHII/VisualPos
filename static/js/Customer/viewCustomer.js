$(document).ready(function() {
    $.noConflict(); 

    if ($.fn.DataTable) {
        setTimeout(() => {
            $('#clientsTable').DataTable({
                "paging": true,
                "searching": true,
                "ordering": true,
                "lengthChange": true,
                "pageLength": 10,
                "deferRender": true,  // Evita errores al renderizar
                "language": {
                    "search": "Buscar:",
                    "lengthMenu": "Mostrar _MENU_ registros",
                    "info": "Mostrando _START_ a _END_ de _TOTAL_ registros",
                    "paginate": {
                        "previous": "Anterior",
                        "next": "Siguiente"
                    }
                }
            });
        }, 500); // Espera un poco antes de inicializar
    } else {
        console.error('DataTable plugin no está cargado correctamente.');
    }

    document.getElementById('exportButton').addEventListener('click', function() {
        const exportUrl = this.getAttribute('data-url');
        window.location.href = exportUrl;
    });


// IMPORTACIÓN DE DATOS DESDE EXCEL
document.getElementById('formCargarArchivo').addEventListener('submit', function(event) {
    event.preventDefault();

    var fileInput = document.getElementById('archivoExcel');
    if (fileInput.files.length === 0) {
        Swal.fire("Error", "Por favor, selecciona un archivo antes de cargar.", "error");
        return;
    }

    var formData = new FormData(this);
    var importUrl = this.getAttribute('data-url');  // Obtener la URL desde el form

    if (!importUrl) {
        console.error("La URL de importación no está definida.");
        return;
    }

    console.log("Enviando archivo a:", importUrl);

    // Mostrar la barra de progreso
    document.getElementById('progresoCarga').style.display = 'block';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', importUrl, true);

    xhr.upload.onprogress = function(event) {
        if (event.lengthComputable) {
            var porcentaje = (event.loaded / event.total) * 100;
            document.getElementById('progresoBarra').style.width = porcentaje + '%';
            document.getElementById('progresoPorcentaje').textContent = Math.round(porcentaje) + '%';
        }
    };

    xhr.onload = function() {
        if (xhr.status == 200) {
            var respuesta = JSON.parse(xhr.responseText);
            if (respuesta.status == 'success') {
                document.getElementById('resultadoCarga').style.display = 'block';
                location.reload();
                document.getElementById('descargarPlantilla').href = '/static/Customers.xlsx';
            } else {
                Swal.fire("Error", respuesta.message, "error");
            }
        } else {
            Swal.fire("Error", "Error al cargar el archivo", "error");
        }
    };

    xhr.send(formData);
});


// Enviar el archivo
xhr.send(formData);
});
        document.getElementById("descargarPlantilla").addEventListener("click", function(event) {
            event.preventDefault();
            const archivo = '/static/archived/Customers.xlsx';  // Ruta estática del archivo

            const a = document.createElement("a");
            a.href = archivo;
            a.download = "Clientes.xlsx";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });

    const deleteButtons = document.querySelectorAll('.delete-btn');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function (event) {
            event.preventDefault(); 
            
            const url = this.getAttribute('data-url');
            
            Swal.fire({
                title: `¿Estás seguro que quieres eliminar a este cliente?`,
                text: "¡No podrás revertir esta acción!",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: 'Sí, eliminar',
                cancelButtonText: 'Cancelar'
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = url;
                }
            });
        });
    });

document.addEventListener("DOMContentLoaded", function () {
    $('#clientsTable').DataTable({
        paging: true,
        ordering: true,
        info: true,
        searching: true,
        lengthChange: true,
        autoWidth: false,
        pageLength: 10,
        language: {
            processing: "Procesando...",
            search: "Buscar:",
            lengthMenu: "Mostrar _MENU_ registros",
            info: "Mostrando de _START_ a _END_ de _TOTAL_ registros",
            infoEmpty: "Mostrando 0 a 0 de 0 registros",
            infoFiltered: "(filtrado de _MAX_ registros en total)",
            loadingRecords: "Cargando...",
            zeroRecords: "No se encontraron resultados",
            emptyTable: "No hay datos disponibles en la tabla",
            paginate: {
                first: "Primero",
                previous: "Anterior",
                next: "Siguiente",
                last: "Último"
            },
            aria: {
                sortAscending: ": activar para ordenar columna ascendente",
                sortDescending: ": activar para ordenar columna descendente"
            }
        }
    });
});

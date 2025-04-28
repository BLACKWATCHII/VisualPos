const datesClients = JSON.parse('{{ dates_clients|escapejs }}');
const countsClients = JSON.parse('{{ counts_clients|escapejs }}');
const datesSales = JSON.parse('{{ dates_sales|escapejs }}');
const totalsSales = JSON.parse('{{ totals_sales|escapejs }}');

// Gráfico de Clientes Nuevos (ya lo tenías)
const ctx2 = document.getElementById('chart2').getContext('2d');
new Chart(ctx2, {
    type: 'bar',
    data: {
        labels: datesClients,
        datasets: [{
            label: 'Clientes Nuevos',
            data: countsClients,
            backgroundColor: 'rgba(54, 176, 9)',
            borderColor: 'rgba(0, 0, 0)',
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            y: { beginAtZero: true }
        }
    }
});

// Gráfico de Ventas Diarias (tipo Donut)
const ctx1 = document.getElementById('chart1').getContext('2d');
new Chart(ctx1, {
    type: 'doughnut',
    data: {
        labels: datesSales,
        datasets: [{
            label: 'Ventas Diarias',
            data: totalsSales,
            backgroundColor: [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'
            ],
            hoverOffset: 4
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'top',
            },
            title: {
                display: true,
                text: 'Ventas Diarias'
            }
        }
    }
});

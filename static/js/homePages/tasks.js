   const dates = JSON.parse('{{ dates|escapejs }}');
   const counts = JSON.parse('{{ counts|escapejs }}');

   const ctx2 = document.getElementById('chart2').getContext('2d');
   new Chart(ctx2, {
       type: 'bar',
       data: {
           labels: dates,
           datasets: [{
               label: 'Clientes Nuevos',
               data: counts,
               backgroundColor: 'rgba(54, 176, 9)',
               borderColor: 'rgba(0, 0, 0)',
               borderWidth: 1
           }]
       },
       options: {
           scales: {
               y: {
                   beginAtZero: true
               }
           }
       }
   });
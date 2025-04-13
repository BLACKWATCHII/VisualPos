document.addEventListener('DOMContentLoaded', function () {
    const djangoMessages = JSON.parse(document.getElementById('django-messages-json')?.textContent || '[]');

    djangoMessages.forEach(msg => {
        Swal.fire({
            icon: msg.level === 'success' ? 'success' :
                  msg.level === 'error' ? 'error' :
                  msg.level === 'warning' ? 'warning' : 'info',
            title: msg.message,
            confirmButtonColor: '#3085d6',
            confirmButtonText: 'OK'
        });
    });
});

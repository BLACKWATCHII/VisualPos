document.addEventListener("DOMContentLoaded", function () {
    const messagesElement = document.getElementById("django-messages");
    if (messagesElement) {
        const messages = JSON.parse(messagesElement.textContent);
        messages.forEach((msg) => {
            Swal.fire({
                icon: msg.tags === "success" ? "success" : "error",
                title: msg.message,
                confirmButtonText: "OK",
                timer: 3000,
                timerProgressBar: true
            });
        });
    }
});

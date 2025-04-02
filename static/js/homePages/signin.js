document.addEventListener("DOMContentLoaded", function () {
    const successMessages = document.querySelectorAll(".success-message");
    const errorMessages = document.querySelectorAll(".error-message");

  
    successMessages.forEach(element => {
      Swal.fire({
        icon: "success",
        title: "Success",
        text: element.textContent,
        timer: 3000, 
        showConfirmButton: false
      }).then(() => {
        element.remove();
      });
    });

   
    errorMessages.forEach(element => {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: element.textContent
      }).then(() => {
        element.remove();
      });
    });
  });
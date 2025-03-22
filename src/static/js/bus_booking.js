document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    const inputs = [
        document.getElementById("id_pickup_point"),
        document.getElementById("id_drop_point")
    ];

    form.addEventListener("submit", function (event) {
        let isValid = true;

        inputs.forEach(input => {
            if (input && !input.value.trim()) {
                isValid = false;
                input.classList.add("is-invalid");
                const errorMessage = input.nextElementSibling || document.createElement("div");
                errorMessage.className = "invalid-feedback";
                errorMessage.textContent = "This field is required.";
                if (!input.nextElementSibling) {
                    input.parentNode.appendChild(errorMessage);
                }
            } else if (input) {
                input.classList.remove("is-invalid");
                if (input.nextElementSibling) {
                    input.nextElementSibling.remove();
                }
            }
        });

        if (!isValid) {
            event.preventDefault();
        }
    });

    inputs.forEach(input => {
        if (input) {
            input.addEventListener("input", function () {
                if (input.value.trim()) {
                    input.classList.remove("is-invalid");
                    if (input.nextElementSibling) {
                        input.nextElementSibling.remove();
                    }
                }
            });
        }
    });
});

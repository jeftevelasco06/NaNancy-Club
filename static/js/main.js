document.addEventListener("DOMContentLoaded", () => {
    const open = document.getElementById("openModal");
    const close = document.getElementById("closeModal");
    const modal = document.getElementById("bookingModal");
    const form = document.getElementById("bookingForm");

    open.addEventListener("click", () => {
        if (!window.CURRENT_USER_EMAIL) {
            alert("Debes iniciar sesión para agendar una cita.");
            return;
        }
        modal.classList.remove("hidden");
    });

    close.addEventListener("click", () => {
        modal.classList.add("hidden");
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload = {
            parent_name: document.getElementById("parent_name").value,
            child_name: document.getElementById("child_name").value,
            child_age: document.getElementById("child_age").value,
            date: document.getElementById("date").value,
            time: document.getElementById("time").value,
            comments: document.getElementById("comments").value
        };

        const res = await fetch("/api/book", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            document.getElementById("successMsg").classList.remove("hidden");
            form.reset();
        }
    });
});

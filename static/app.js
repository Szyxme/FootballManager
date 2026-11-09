"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const feedback = document.getElementById("form-feedback");

    document.querySelectorAll("form[data-api-url]").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();

            const method = form.dataset.apiMethod || "POST";
            if (method === "DELETE" && !window.confirm("Usunąć tego zawodnika?")) {
                return;
            }

            const button = form.querySelector('button[type="submit"]');
            const csrfToken = form.querySelector('[name="_csrf_token"]')?.value;
            const payload = Object.fromEntries(new FormData(form).entries());
            delete payload._csrf_token;

            for (const field of ["age", "club_id"]) {
                if (field in payload) {
                    payload[field] = Number(payload[field]);
                }
            }

            if (button) {
                button.disabled = true;
            }
            form.setAttribute("aria-busy", "true");
            feedback.textContent = "Zapisywanie…";
            feedback.classList.remove("is-error");

            try {
                const response = await fetch(form.dataset.apiUrl, {
                    method,
                    headers: {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-CSRF-Token": csrfToken || ""
                    },
                    body: method === "DELETE" ? undefined : JSON.stringify(payload)
                });
                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || "Nie udało się zapisać zmian.");
                }

                feedback.textContent = result.message || "Zapisano.";
                window.setTimeout(() => window.location.reload(), 700);
            } catch (error) {
                feedback.textContent = error.message || "Wystąpił błąd połączenia.";
                feedback.classList.add("is-error");
                if (button) {
                    button.disabled = false;
                }
                form.removeAttribute("aria-busy");
            }
        });
    });
});

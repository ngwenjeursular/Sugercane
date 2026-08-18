const form = document.getElementById("authForm");
const message = document.getElementById("formMessage");
const button = document.getElementById("loginButton");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    message.textContent = "";
    message.className = "form-message";

    const phoneNumber = document
        .getElementById("phoneNumber")
        .value
        .trim();

    const password = document
        .getElementById("password")
        .value;

    if (!phoneNumber || !password) {
        message.textContent = "Please enter your phone number and password.";
        message.classList.add("error");
        return;
    }

    button.disabled = true;
    button.textContent = "Signing in...";

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/api/auth/login",
            {
                method: "POST",

                credentials: "include",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    phone_number: phoneNumber,
                    password: password
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Unable to sign in."
            );
        }

        message.textContent = "Signed in successfully!";
        message.classList.add("success");

        /*
         * Give the browser a moment to store the
         * session cookie before navigating.
         */
        setTimeout(() => {
            window.location.href = "dashboard.html";
        }, 500);

    } catch (error) {

        console.error("Login error:", error);

        message.textContent =
            error.message || "Something went wrong.";

        message.classList.add("error");

    } finally {

        button.disabled = false;
        button.textContent = "Sign in";

    }
});
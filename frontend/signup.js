"use strict";

const form = document.getElementById("signupForm");
const message = document.getElementById("formMessage");
const button = document.getElementById("signupButton");

function showMessage(text, type) {
    message.textContent = text;
    message.className = "form-message";

    if (type) {
        message.classList.add(type);
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    showMessage("", "");

    const fullName = document
        .getElementById("fullName")
        .value
        .trim();

    const phoneNumber = document
        .getElementById("phoneNumber")
        .value
        .trim();

    const password = document
        .getElementById("password")
        .value;

    const confirmPassword = document
        .getElementById("confirmPassword")
        .value;

    const referralCode = document
        .getElementById("referralCode")
        .value
        .trim();

    /*
     * Client-side validation is for user experience.
     * The backend MUST perform the actual validation.
     */

    if (!fullName) {
        showMessage("Please enter your full name.", "error");
        return;
    }

    if (!/^\+254\d{9}$/.test(phoneNumber)) {
        showMessage(
            "Please enter a valid Kenyan phone number beginning with +254.",
            "error"
        );
        return;
    }

    if (password !== confirmPassword) {
        showMessage("Passwords do not match.", "error");
        return;
    }

    if (password.length < 8) {
        showMessage(
            "Your password must be at least 8 characters.",
            "error"
        );
        return;
    }

    button.disabled = true;
    button.textContent = "Creating account...";

    try {
        const response = await fetch(
            "http://127.0.0.1:8000/api/auth/register",
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    full_name: fullName,
                    phone_number: phoneNumber,
                    password: password,
                    referral_code: referralCode || null
                })
            }
        );

        let data;

        try {
            data = await response.json();
        } catch {
            data = {};
        }

        if (!response.ok) {
            let errorMessage = "Unable to create your account.";

            if (typeof data.detail === "string") {
                errorMessage = data.detail;
            }

            throw new Error(errorMessage);
        }

        showMessage(
            "Account created successfully.",
            "success"
        );

        /*
         * Give the user a moment to see the success message.
         */
        setTimeout(() => {
            window.location.href = "dashboard.html";
        }, 800);

    } catch (error) {
        showMessage(
            error.message || "Something went wrong. Please try again.",
            "error"
        );

    } finally {
        button.disabled = false;
        button.textContent = "Create account";
    }
});
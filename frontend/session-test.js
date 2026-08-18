const button = document.getElementById("testButton");
const result = document.getElementById("result");

button.addEventListener("click", async () => {
    result.textContent = "Checking session...";

    try {
        const response = await fetch(
            "http://127.0.0.1:8000/api/auth/me",
            {
                method: "GET",
                credentials: "include"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Session check failed."
            );
        }

        result.textContent =
            "Authenticated successfully!\n\n" +
            JSON.stringify(data, null, 2);

    } catch (error) {
        result.textContent =
            "ERROR:\n" + error.message;
    }
});
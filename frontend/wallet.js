const API_BASE = "http://127.0.0.1:8000/api";
const CSRF_COOKIE = "sugercane_csrf";

const userName = document.getElementById("userName");
const walletBalance = document.getElementById("walletBalance");
const walletCurrency = document.getElementById("walletCurrency");
const walletCurrencyBottom = document.getElementById("walletCurrencyBottom");
const walletStatus = document.getElementById("walletStatus");

const menuButton = document.getElementById("menuButton");
const closeMenu = document.getElementById("closeMenu");
const sideMenu = document.getElementById("sideMenu");
const menuOverlay = document.getElementById("menuOverlay");
const logoutButton = document.getElementById("logoutButton");

function getCsrfToken() {
    const prefix = `${encodeURIComponent(CSRF_COOKIE)}=`;
    const cookie = document.cookie
        .split("; ")
        .find(row => row.startsWith(prefix));
    return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

async function apiFetch(endpoint, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            throw new Error("Your security session has expired. Please log in again.");
        }
        headers["X-CSRF-Token"] = csrfToken;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        credentials: "include",
        ...options,
        headers
    });

    if (!response.ok) {
        let message = "Something went wrong.";

        try {
            const data = await response.json();
            message = data.detail || message;
        } catch {
            // Ignore invalid response
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

async function loadWallet() {
    try {
        const [user, wallet] = await Promise.all([
            apiFetch("/users/me"),
            apiFetch("/users/wallet")
        ]);

        userName.textContent = user.full_name;
        walletBalance.textContent = wallet.balance;

        walletCurrency.textContent =
            wallet.currency === "KES"
                ? "KSh"
                : wallet.currency;

        walletCurrencyBottom.textContent = wallet.currency;

        walletStatus.textContent =
            wallet.status.charAt(0).toUpperCase()
            + wallet.status.slice(1);

    } catch (error) {
        console.error("Wallet error:", error);

        if (
            error.message.toLowerCase().includes("unauthorized") ||
            error.message.toLowerCase().includes("credentials") ||
            error.message.toLowerCase().includes("session")
        ) {
            window.location.href = "auth.html";
            return;
        }

        walletBalance.textContent = "—";
        walletStatus.textContent = "Unavailable";
    }
}

function openMenu() {
    sideMenu.classList.add("open");
    menuOverlay.classList.add("visible");
    menuButton.setAttribute("aria-expanded", "true");
}

function closeSideMenu() {
    sideMenu.classList.remove("open");
    menuOverlay.classList.remove("visible");
    menuButton.setAttribute("aria-expanded", "false");
}

menuButton.addEventListener("click", openMenu);
closeMenu.addEventListener("click", closeSideMenu);
menuOverlay.addEventListener("click", closeSideMenu);

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    logoutButton.textContent = "Logging out...";

    try {
        await apiFetch("/auth/logout", {
            method: "POST"
        });

        window.location.href = "auth.html";

    } catch (error) {
        console.error("Logout failed:", error);

        logoutButton.disabled = false;
        logoutButton.textContent = "Log out";

        alert("Unable to log out. Please try again.");
    }
});

window.addEventListener("sugercane:deposit-started", () => {
    window.setTimeout(loadWallet, 1500);
});

loadWallet();
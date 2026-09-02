const API_BASE = "http://127.0.0.1:8000/api";
const CSRF_COOKIE = "sugercane_csrf";

const userName = document.getElementById("userName");
const welcomeName = document.getElementById("welcomeName");

const walletBalance = document.getElementById("walletBalance");
const walletStatus = document.getElementById("walletStatus");

const referralCode = document.getElementById("referralCode");
const referralCount = document.getElementById("referralCount");
const referralEarnings = document.getElementById("referralEarnings");

const transactionsList = document.getElementById("transactionsList");

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
            // Ignore invalid/non-JSON response
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

async function loadDashboard() {
    try {
        const [user, wallet, referrals, transactions] = await Promise.all([
            apiFetch("/users/me"),
            apiFetch("/users/wallet"),
            apiFetch("/users/referrals"),
            apiFetch("/users/transactions")
        ]);

        userName.textContent = user.full_name;
        welcomeName.textContent = user.full_name.split(" ")[0];

        walletBalance.textContent =
            `${wallet.currency === "KES" ? "KSh" : wallet.currency} ${wallet.balance}`;

        walletStatus.textContent =
            wallet.status.charAt(0).toUpperCase() + wallet.status.slice(1);

        referralCode.textContent = referrals.referral_code;
        referralCount.textContent = referrals.total_referrals;

        referralEarnings.textContent =
            `${referrals.currency === "KES" ? "KSh" : referrals.currency} ${referrals.earnings}`;

        renderTransactions(transactions);

    } catch (error) {
        console.error("Dashboard error:", error);

        if (
            error.message.toLowerCase().includes("unauthorized") ||
            error.message.toLowerCase().includes("credentials") ||
            error.message.toLowerCase().includes("session")
        ) {
            window.location.href = "auth.html";
            return;
        }

        transactionsList.innerHTML = `
            <div class="empty-state">
                Unable to load your account information.
            </div>
        `;
    }
}

function renderTransactions(transactions) {
    if (!transactions || transactions.length === 0) {
        transactionsList.innerHTML = `
            <div class="empty-state">
                No transactions yet.
            </div>
        `;
        return;
    }

    transactionsList.innerHTML = transactions.map(transaction => {
        const date = new Date(transaction.created_at);

        const formattedDate = date.toLocaleDateString("en-KE", {
            day: "numeric",
            month: "short",
            year: "numeric"
        });

        const sign = transaction.type === "deposit" ? "+" : "-";

        return `
            <div class="transaction-row">
                <div>
                    <strong>${escapeHtml(transaction.type)}</strong>
                    <span>${formattedDate}</span>
                </div>

                <div class="transaction-amount">
                    <strong>
                        ${sign}${transaction.currency === "KES" ? "KSh" : transaction.currency}
                        ${transaction.amount}
                    </strong>

                    <small>${escapeHtml(transaction.status)}</small>
                </div>
            </div>
        `;
    }).join("");
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
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
    window.setTimeout(loadDashboard, 1500);
});

loadDashboard();
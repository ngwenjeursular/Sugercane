const API_BASE = "http://127.0.0.1:8000/api";
const CSRF_COOKIE = "sugercane_csrf";

function getCookie(name) {
    const prefix = `${encodeURIComponent(name)}=`;
    const cookie = document.cookie
        .split("; ")
        .find(row => row.startsWith(prefix));

    return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

function getCsrfToken() {
    return getCookie(CSRF_COOKIE);
}

async function depositFetch(endpoint, options = {}) {
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
            // Ignore invalid/non-JSON response.
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

function createDepositModal() {
    const modal = document.createElement("div");
    modal.id = "depositModal";
    modal.className = "deposit-modal";
    modal.hidden = true;
    modal.innerHTML = `
        <div class="deposit-modal-backdrop" data-deposit-close></div>
        <section class="deposit-dialog" role="dialog" aria-modal="true" aria-labelledby="depositTitle">
            <button type="button" class="deposit-close" aria-label="Close deposit form" data-deposit-close>×</button>
            <p class="eyebrow">Deposit</p>
            <h2 id="depositTitle">Add money to your wallet.</h2>
            <p class="deposit-description">Enter the amount you want to deposit. Safaricom will send an M-Pesa prompt to your registered phone.</p>
            <form id="depositForm" class="deposit-form">
                <label for="depositAmount">Amount</label>
                <div class="deposit-input-wrap">
                    <span>KSh</span>
                    <input id="depositAmount" name="amount" type="number" min="1" step="1" inputmode="numeric" autocomplete="off" required>
                </div>
                <p id="depositMessage" class="deposit-message" role="status" aria-live="polite"></p>
                <button id="depositSubmit" class="primary-action deposit-submit" type="submit">Continue to M-Pesa</button>
            </form>
        </section>
    `;

    document.body.appendChild(modal);
    return modal;
}

function setDepositMessage(message, type = "") {
    const messageElement = document.getElementById("depositMessage");
    if (!messageElement) return;
    messageElement.textContent = message;
    messageElement.className = `deposit-message ${type}`.trim();
}

function openDepositModal() {
    const modal = document.getElementById("depositModal");
    const amount = document.getElementById("depositAmount");
    if (!modal) return;

    modal.hidden = false;
    document.body.classList.add("deposit-modal-open");
    setDepositMessage("");
    if (amount) {
        amount.value = "";
        window.setTimeout(() => amount.focus(), 0);
    }
}

function closeDepositModal() {
    const modal = document.getElementById("depositModal");
    if (!modal) return;

    modal.hidden = true;
    document.body.classList.remove("deposit-modal-open");
}

async function submitDeposit(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const submitButton = document.getElementById("depositSubmit");
    const amountInput = document.getElementById("depositAmount");
    const amount = Number(amountInput.value);

    if (!Number.isInteger(amount) || amount < 1) {
        setDepositMessage("Enter a valid whole amount of at least KSh 1.", "error");
        amountInput.focus();
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Sending M-Pesa prompt...";
    setDepositMessage("Check your phone and enter your M-Pesa PIN when prompted.", "pending");

    try {
        const result = await depositFetch("/mpesa/stkpush", {
            method: "POST",
            body: JSON.stringify({ amount })
        });

        setDepositMessage(
            result.message || "M-Pesa prompt sent. Complete the payment on your phone.",
            "success"
        );
        form.reset();
        submitButton.textContent = "Prompt sent";

        window.dispatchEvent(new CustomEvent("sugercane:deposit-started", {
            detail: result
        }));
    } catch (error) {
        console.error("Deposit failed:", error);
        setDepositMessage(error.message, "error");
        submitButton.disabled = false;
        submitButton.textContent = "Try again";
    }
}

function initDeposit() {
    const depositButtons = document.querySelectorAll("[data-deposit-button]");
    if (!depositButtons.length) return;

    createDepositModal();

    depositButtons.forEach(button => {
        button.addEventListener("click", openDepositModal);
    });

    document.getElementById("depositForm").addEventListener("submit", submitDeposit);

    document.querySelectorAll("[data-deposit-close]").forEach(element => {
        element.addEventListener("click", closeDepositModal);
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") closeDepositModal();
    });
}

document.addEventListener("DOMContentLoaded", initDeposit);

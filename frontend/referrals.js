const API = "http://127.0.0.1:8000/api";

const userName = document.getElementById("userName");
const referralCode = document.getElementById("referralCode");
const directReferrals = document.getElementById("directReferrals");
const totalReferrals = document.getElementById("totalReferrals");
const referralEarnings = document.getElementById("referralEarnings");

const copyReferral = document.getElementById("copyReferral");
const copyMessage = document.getElementById("copyMessage");

const menuButton = document.getElementById("menuButton");
const closeMenu = document.getElementById("closeMenu");
const sideMenu = document.getElementById("sideMenu");
const menuOverlay = document.getElementById("menuOverlay");
const logoutButton = document.getElementById("logoutButton");


async function apiFetch(endpoint, options = {}) {

    const response = await fetch(API + endpoint, {
        credentials: "include",
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    if (!response.ok) {

        if (response.status === 401) {
            window.location.href = "auth.html";
        }

        throw new Error("Request failed");
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}


async function loadReferralData() {

    try {

        const [user, referrals] = await Promise.all([
            apiFetch("/users/me"),
            apiFetch("/users/referrals")
        ]);

        userName.textContent = user.full_name;

        referralCode.textContent = referrals.referral_code;

        directReferrals.textContent =
            referrals.direct_referrals;

        totalReferrals.textContent =
            referrals.total_referrals;

        referralEarnings.textContent =
            `${referrals.currency} ${referrals.earnings}`;

    } catch (error) {

        console.error("Failed to load referral data:", error);

    }
}


/* COPY REFERRAL CODE */

copyReferral.addEventListener("click", async () => {

    try {

        await navigator.clipboard.writeText(
            referralCode.textContent
        );

        copyMessage.textContent =
            "Referral code copied.";

        copyReferral.textContent = "Copied";

        setTimeout(() => {

            copyMessage.textContent = "";
            copyReferral.textContent = "Copy";

        }, 1800);

    } catch (error) {

        copyMessage.textContent =
            "Unable to copy the code.";

    }

});


/* MENU */

menuButton.addEventListener("click", () => {

    sideMenu.classList.add("open");
    menuOverlay.classList.add("visible");

    menuButton.setAttribute(
        "aria-expanded",
        "true"
    );

});


function closeSideMenu() {

    sideMenu.classList.remove("open");
    menuOverlay.classList.remove("visible");

    menuButton.setAttribute(
        "aria-expanded",
        "false"
    );

}


closeMenu.addEventListener("click", closeSideMenu);

menuOverlay.addEventListener("click", closeSideMenu);


/* LOGOUT */

logoutButton.addEventListener("click", async () => {

    try {

        await apiFetch("/auth/logout", {
            method: "POST"
        });

    } finally {

        window.location.href = "auth.html";

    }

});


loadReferralData();
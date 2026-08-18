const API="http://127.0.0.1:8000/api";

const userName=document.getElementById("userName");
const list=document.getElementById("transactionsList");
const count=document.getElementById("transactionCount");

const menuButton=document.getElementById("menuButton");
const closeMenu=document.getElementById("closeMenu");
const sideMenu=document.getElementById("sideMenu");
const menuOverlay=document.getElementById("menuOverlay");
const logoutButton=document.getElementById("logoutButton");

async function apiFetch(endpoint,options={}){

    const response=await fetch(API+endpoint,{
        credentials:"include",
        headers:{
            "Content-Type":"application/json"
        },
        ...options
    });

    if(!response.ok){

        if(response.status===401){
            location.href="auth.html";
        }

        throw new Error("Request failed");
    }

    if(response.status===204){
        return null;
    }

    return response.json();
}

async function loadPage(){

    const [user,transactions]=await Promise.all([
        apiFetch("/users/me"),
        apiFetch("/users/transactions")
    ]);

    userName.textContent=user.full_name;

    count.textContent=`${transactions.length} transaction${transactions.length===1?"":"s"}`;

    renderTransactions(transactions);
}

function renderTransactions(items){

    if(items.length===0){

        list.innerHTML=`
        <div class="empty-state">
            No transactions yet.
        </div>`;

        return;
    }

    list.innerHTML=items.map(tx=>{

        const icon=
            tx.type==="deposit"?"💰":
            tx.type==="withdrawal"?"📤":
            tx.type==="referral_bonus"?"🌱":
            "💳";

        const amount=
            (tx.type==="deposit"||tx.type==="referral_bonus"?"+":"-")
            +tx.currency+" "+tx.amount;

        const date=new Date(tx.created_at)
            .toLocaleDateString("en-KE",{
                day:"numeric",
                month:"short",
                year:"numeric"
            });

        return `
        <div class="transaction-item">

            <div class="transaction-left">

                <div class="transaction-icon">
                    ${icon}
                </div>

                <div class="transaction-info">

                    <strong>${tx.type.replaceAll("_"," ")}</strong>

                    <span>${tx.reference} • ${date}</span>

                </div>

            </div>

            <div class="transaction-right">

                <strong>${amount}</strong>

                <span class="status ${tx.status}">
                    ${tx.status}
                </span>

            </div>

        </div>`;
    }).join("");
}


/* MENU */

menuButton.onclick=()=>{
    sideMenu.classList.add("open");
    menuOverlay.classList.add("visible");
};

closeMenu.onclick=()=>{
    sideMenu.classList.remove("open");
    menuOverlay.classList.remove("visible");
};

menuOverlay.onclick=closeMenu.onclick;


/* LOGOUT */

logoutButton.onclick=async()=>{

    await apiFetch("/auth/logout",{
        method:"POST"
    });

    location.href="auth.html";
};

loadPage();
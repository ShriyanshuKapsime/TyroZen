const loginModal = document.getElementById("loginModal");
const registerModal = document.getElementById("registerModal");

document.getElementById("openLogin").onclick = () => {
    loginModal.style.display = "flex";
};

document.getElementById("closeLogin").onclick = () =>
    loginModal.style.display = "none";

document.getElementById("closeRegister").onclick = () =>
    registerModal.style.display = "none";

// Switch modals
document.getElementById("openRegisterFromLogin").onclick = () => {
    loginModal.style.display = "none";
    registerModal.style.display = "flex";
};

document.getElementById("openLoginFromRegister").onclick = () => {
    registerModal.style.display = "none";
    loginModal.style.display = "flex";
};

// AJAX LOGIN
document.getElementById("loginForm").onsubmit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);

    const res = await fetch("/login", { method: "POST", body: form });
    const data = await res.json();

    if (data.success) {
        window.location.href = data.redirect;
    } else {
        document.getElementById("loginMsg").textContent = data.message;
        document.getElementById("loginMsg").style.color = "red";
    }
};

// AJAX REGISTER
document.getElementById("registerForm").onsubmit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);

    const res = await fetch("/register", { method: "POST", body: form });
    const data = await res.json();

    if (data.success) {
        registerModal.style.display = "none";
        loginModal.style.display = "flex";
        document.getElementById("loginMsg").textContent = data.message;
        document.getElementById("loginMsg").style.color = "green";
    } else {
        document.getElementById("registerMsg").textContent = data.message;
        document.getElementById("registerMsg").style.color = "red";
    }
};

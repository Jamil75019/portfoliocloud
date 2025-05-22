const domainsPerPage = 6;
let currentPage = 1;
let domains = [];

async function loadDomains() {
    const response = await fetch("phishing_like_domains.json?ts=" + Date.now());
    domains = await response.json();
    renderPage(currentPage);
}

function renderPage(page) {
    const container = document.getElementById("domain-list");
    container.innerHTML = "";

    const start = (page - 1) * domainsPerPage;
    const end = start + domainsPerPage;
    const currentDomains = domains.slice(start, end);

    currentDomains.forEach(d => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            <h3>${d.domain}</h3>
            <p>💥 Score : ${d.score}%</p>
            <p>🎯 Marque détectée : <strong>${d.matched_brand}</strong></p>
        `;
        container.appendChild(card);
    });

    document.getElementById("page-info").textContent = `Page ${currentPage} / ${Math.ceil(domains.length / domainsPerPage)}`;
    document.getElementById("prev").disabled = currentPage === 1;
    document.getElementById("next").disabled = currentPage === Math.ceil(domains.length / domainsPerPage);
}

document.addEventListener("DOMContentLoaded", () => {
    loadDomains();

    document.getElementById("prev").addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            renderPage(currentPage);
        }
    });

    document.getElementById("next").addEventListener("click", () => {
        if (currentPage < Math.ceil(domains.length / domainsPerPage)) {
            currentPage++;
            renderPage(currentPage);
        }
    });

    document.getElementById("last").addEventListener("click", () => {
        currentPage = Math.ceil(domains.length / domainsPerPage);
        renderPage(currentPage);
    });

    // ♻️ Recharge auto toutes les 60 secondes
    setInterval(() => {
        loadDomains();
    }, 60000);
});

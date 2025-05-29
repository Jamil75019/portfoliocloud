const domainsPerPage = 6;
let currentPage = 1;
let domains = [];

async function loadDomains() {
    try {
    const response = await fetch("phishing_like_domains.json?ts=" + Date.now());
    domains = await response.json();
    renderPage(currentPage);
    } catch (error) {
        console.error("Erreur lors du chargement des domaines:", error);
    }
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
    document.getElementById("first").disabled = currentPage === 1;
    document.getElementById("prev").disabled = currentPage === 1;
    document.getElementById("next").disabled = currentPage === Math.ceil(domains.length / domainsPerPage);
    document.getElementById("last").disabled = currentPage === Math.ceil(domains.length / domainsPerPage);
}

function setupEventListeners() {
    console.log("Configuration des event listeners");
    
    const firstButton = document.getElementById("first");
    const prevButton = document.getElementById("prev");
    const nextButton = document.getElementById("next");
    const lastButton = document.getElementById("last");
    
    if (firstButton) {
        firstButton.addEventListener("click", () => {
            console.log("Bouton première page cliqué");
            currentPage = 1;
            renderPage(currentPage);
        });
    } else {
        console.error("Le bouton 'first' n'a pas été trouvé");
    }
    
    if (prevButton) {
        prevButton.addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            renderPage(currentPage);
        }
    });
    }

    if (nextButton) {
        nextButton.addEventListener("click", () => {
        if (currentPage < Math.ceil(domains.length / domainsPerPage)) {
            currentPage++;
            renderPage(currentPage);
        }
    });
    }

    if (lastButton) {
        lastButton.addEventListener("click", () => {
        currentPage = Math.ceil(domains.length / domainsPerPage);
        renderPage(currentPage);
    });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM chargé");
    // Attendre un court instant pour s'assurer que tous les éléments sont chargés
    setTimeout(() => {
        setupEventListeners();
        loadDomains();
    }, 100);

    // ♻️ Recharge auto toutes les 60 secondes
    setInterval(() => {
        loadDomains();
    }, 60000);
});

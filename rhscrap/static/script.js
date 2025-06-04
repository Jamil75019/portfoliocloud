document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search');
    const enterpriseInput = document.getElementById('enterprise');
    const locationInput = document.getElementById('location');
    const startButton = document.getElementById('startSearch');
    const progressContainer = document.getElementById('progress');
    const progressBar = progressContainer.querySelector('.progress-fill');
    const resultsContainer = document.getElementById('results');

    // Animation des inputs
    [searchInput, enterpriseInput, locationInput].forEach(input => {
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('focused');
        });
        input.addEventListener('blur', () => {
            input.parentElement.classList.remove('focused');
        });
    });

    // Fonction pour mettre à jour la barre de progression
    function updateProgress(percent) {
        progressBar.style.width = `${percent}%`;
    }

    // Fonction pour afficher un message d'erreur
    function showError(message) {
        resultsContainer.innerHTML = `
            <div class="error-message">
                <p>❌ Erreur: ${message}</p>
            </div>
        `;
    }

    // Fonction pour afficher les résultats
    function displayResults(data) {
        const { profiles, resultUrl } = data;
        
        let html = `
            <div class="success-message">
                <p>✅ Recherche terminée !</p>
                <p>${profiles.length} profils trouvés</p>
            </div>
        `;

        profiles.forEach(profile => {
            html += `
                <div class="result-card">
                    <h3>${profile.name}</h3>
                    ${profile.position ? `<p class="position">${profile.position}</p>` : ''}
                    ${profile.company ? `<p class="company">${profile.company}</p>` : ''}
                    <a href="${profile.url}" target="_blank" class="profile-link">Voir le profil LinkedIn</a>
                    ${profile.emails.length > 0 ? `
                        <div class="emails">
                            <h4>Emails probables :</h4>
                            <ul>
                                ${profile.emails.map(email => `
                                    <li>${email.address} (${Math.round(email.probability * 100)}% de probabilité)</li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        });

        if (resultUrl) {
            html += `
                <a href="${resultUrl}" class="download-button" download>
                    📥 Télécharger les résultats complets
                </a>
            `;
        }

        resultsContainer.innerHTML = html;
    }

    // Gestionnaire de clic pour le bouton de recherche
    startButton.addEventListener('click', async () => {
        const query = searchInput.value.trim();
        if (!query) {
            showError('Veuillez entrer une recherche');
            return;
        }

        // Réinitialiser l'interface
        progressContainer.classList.remove('hidden');
        resultsContainer.innerHTML = '';
        startButton.disabled = true;
        updateProgress(0);

        try {
            const apiUrl = window.location.pathname.includes('rhscrap') ? '/rhscrap/search' : '/api/rhscrap/search';
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    query,
                    enterprise: enterpriseInput.value.trim(),
                    location: locationInput.value.trim()
                })
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la recherche');
            }

            const data = await response.json();
            updateProgress(100);
            displayResults(data);

        } catch (error) {
            showError(error.message);
        } finally {
            progressContainer.classList.add('hidden');
            startButton.disabled = false;
        }
    });

    // Permettre l'utilisation de la touche Entrée pour lancer la recherche
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            startButton.click();
        }
    });
}); 

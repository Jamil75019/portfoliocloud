document.addEventListener('DOMContentLoaded', function() {
    // Animation des barres de progression
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        setTimeout(() => {
            const width = bar.getAttribute('data-width');
            bar.style.width = width + '%';
        }, 300);
    });
    
    // Gestion des onglets de projets
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const category = btn.getAttribute('data-category');
            
            // Désactiver tous les boutons et contenus
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Activer le bouton cliqué et le contenu correspondant
            btn.classList.add('active');
            document.getElementById(`${category}-content`).classList.add('active');
        });
    });
});

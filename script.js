document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si on revient après un envoi réussi
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('success') === '1') {
        const submitBtn = document.querySelector('.btn-submit');
        if (submitBtn) {
            submitBtn.innerHTML = '<span>Envoyé !</span> <i class="fas fa-check"></i>';
            setTimeout(() => {
                submitBtn.innerHTML = '<span>Envoyer</span> <i class="fas fa-paper-plane"></i>';
            }, 2000);
        }
    }

    // Initialiser AOS (Animate On Scroll)
    try {
        AOS.init({
            duration: 800,
            easing: 'ease',
            once: true,
            offset: 100
        });
    } catch (error) {
        console.error('Erreur lors de l\'initialisation de AOS:', error);
    }
    
    // Animation des barres de progression
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        setTimeout(() => {
            const width = bar.getAttribute('data-width');
            bar.style.width = width + '%';
        }, 500);
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

    // Système de curseur personnalisé
    const cursor = document.querySelector('.cursor');
    const cursorFollower = document.querySelector('.cursor-follower');
    
    document.addEventListener('mousemove', e => {
        cursor.style.left = `${e.clientX}px`;
        cursor.style.top = `${e.clientY}px`;
        
        setTimeout(() => {
            cursorFollower.style.left = `${e.clientX}px`;
            cursorFollower.style.top = `${e.clientY}px`;
        }, 50);
    });
    
    // Effet survol sur les éléments interactifs
    const interactiveElements = document.querySelectorAll('a, button, .card, .tab-btn');
    interactiveElements.forEach(el => {
        el.addEventListener('mouseenter', () => {
            cursor.style.transform = 'translate(-50%, -50%) scale(1.5)';
            cursorFollower.style.transform = 'translate(-50%, -50%) scale(1.5)';
            cursorFollower.style.backgroundColor = 'rgba(255, 0, 127, 0.1)';
        });
        
        el.addEventListener('mouseleave', () => {
            cursor.style.transform = 'translate(-50%, -50%) scale(1)';
            cursorFollower.style.transform = 'translate(-50%, -50%) scale(1)';
            cursorFollower.style.backgroundColor = 'transparent';
        });
    });
    
    // Initialiser Particles.js
    particlesJS('particles-js', {
        particles: {
            number: {
                value: 50,
                density: {
                    enable: true,
                    value_area: 800
                }
            },
            color: {
                value: '#ff007f'
            },
            shape: {
                type: 'circle',
                stroke: {
                    width: 0,
                    color: '#000000'
                }
            },
            opacity: {
                value: 0.5,
                random: true
            },
            size: {
                value: 3,
                random: true
            },
            line_linked: {
                enable: true,
                distance: 150,
                color: '#4c1d95',
                opacity: 0.3,
                width: 1
            },
            move: {
                enable: true,
                speed: 1,
                direction: 'none',
                random: true,
                straight: false,
                out_mode: 'out',
                bounce: false
            }
        },
        interactivity: {
            detect_on: 'canvas',
            events: {
                onhover: {
                    enable: true,
                    mode: 'grab'
                },
                onclick: {
                    enable: true,
                    mode: 'push'
                },
                resize: true
            },
            modes: {
                grab: {
                    distance: 140,
                    line_linked: {
                        opacity: 0.8
                    }
                },
                push: {
                    particles_nb: 3
                }
            }
        },
        retina_detect: true
    });
    
    // Toggle thème sombre/clair
    const themeToggle = document.querySelector('.theme-toggle');
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        
        // Sauvegarder la préférence dans localStorage
        if (document.body.classList.contains('light-theme')) {
            localStorage.setItem('theme', 'light');
        } else {
            localStorage.setItem('theme', 'dark');
        }
    });
    
    // Vérifier le thème sauvegardé
    if (localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light-theme');
    }
    
    // Animation de défilement fluide
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Gestion du formulaire de contact
    console.log('Recherche du formulaire de contact...'); // Debug log
    const contactForm = document.getElementById('contact-form');
    console.log('Formulaire trouvé:', contactForm); 

    if (contactForm) {
        console.log('Ajout du gestionnaire d\'événement submit...'); // Debug log
        
        contactForm.addEventListener('submit', async function(e) {
            console.log('Formulaire soumis!'); // Debug log
            e.preventDefault();
            console.log('Événement par défaut empêché'); // Debug log
            
            const submitBtn = this.querySelector('.btn-submit');
            const originalText = submitBtn.innerHTML;
            
            submitBtn.innerHTML = '<span>Envoi en cours...</span> <i class="fas fa-spinner fa-spin"></i>';
            submitBtn.disabled = true;
            console.log('Bouton désactivé et texte mis à jour'); // Debug log
            
            const formData = new FormData(this);
            console.log('FormData créé:', formData); // Debug log
            
            try {
                console.log('Début de l\'envoi de la requête à send_mail.php'); // Debug log
                const response = await fetch('send_mail.php', {
                    method: 'POST',
                    body: formData
                });
                
                console.log('Réponse reçue:', response); // Debug log
                console.log('Status:', response.status); // Debug log
                
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }
                
                const responseText = await response.text();
                console.log('Réponse brute:', responseText); // Debug log
                
                let result;
                try {
                    result = JSON.parse(responseText);
                    console.log('Réponse parsée:', result); // Debug log
                } catch (parseError) {
                    console.error('Erreur de parsing JSON:', parseError);
                    console.error('Contenu reçu:', responseText);
                    throw new Error('Réponse invalide du serveur');
                }
                
                if (result.success) {
                    console.log('Email envoyé avec succès'); // Debug log
                    submitBtn.innerHTML = '<span>Envoyé !</span> <i class="fas fa-check"></i>';
                    contactForm.reset();
                    
                    // Afficher un message de succès
                    const successMessage = document.createElement('div');
                    successMessage.className = 'alert alert-success';
                    successMessage.textContent = result.message || 'Message envoyé avec succès !';
                    contactForm.insertBefore(successMessage, contactForm.firstChild);
                    
                    // Supprimer le message après 5 secondes
                    setTimeout(() => {
                        successMessage.remove();
                    }, 5000);
                } else {
                    console.error('Erreur retournée par le serveur:', result.error); // Debug log
                    throw new Error(result.error || 'Erreur lors de l\'envoi');
                }
            } catch (error) {
                console.error('Erreur lors de l\'envoi:', error);
                submitBtn.innerHTML = '<span>Erreur !</span> <i class="fas fa-exclamation-triangle"></i>';
                
                // Afficher un message d'erreur
                const errorMessage = document.createElement('div');
                errorMessage.className = 'alert alert-error';
                errorMessage.textContent = error.message || 'Une erreur est survenue lors de l\'envoi du message.';
                contactForm.insertBefore(errorMessage, contactForm.firstChild);
                
                // Supprimer le message après 5 secondes
                setTimeout(() => {
                    errorMessage.remove();
                }, 5000);
            }
            
            // Réinitialiser le bouton après un délai
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                console.log('Bouton réinitialisé'); // Debug log
            }, 2000);
        });
        
        console.log('Gestionnaire d\'événement submit ajouté avec succès'); // Debug log
    } else {
        console.error('Formulaire de contact non trouvé!'); // Debug log
    }
    
    // Animation de l'indicateur de défilement
    const scrollIndicator = document.querySelector('.scroll-indicator');
    if (scrollIndicator) {
        scrollIndicator.addEventListener('click', () => {
            window.scrollTo({
                top: window.innerHeight,
                behavior: 'smooth'
            });
        });
    }
    
    // Effet de parallaxe légère sur le header
    window.addEventListener('scroll', () => {
        const header = document.querySelector('header');
        const scrollPosition = window.scrollY;
        
        if (header && scrollPosition < window.innerHeight) {
            header.style.backgroundPositionY = `${scrollPosition * 0.5}px`;
        }
    });
});

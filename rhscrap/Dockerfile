# Utiliser une image Python officielle avec support pour les navigateurs
FROM python:3.11-slim

# Installer les dépendances système nécessaires pour Playwright et autres packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    procps \
    libxss1 \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcb1 \
    libxss1 \
    libxtst6 \
    libxshmfence1 \
    libglu1-mesa \
    libgles2-mesa \
    libegl1-mesa \
    libdbus-1-3 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcb1 \
    libxss1 \
    libxtst6 \
    libxshmfence1 \
    libglu1-mesa \
    libgles2-mesa \
    libegl1-mesa \
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances Python
COPY api/requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer Playwright et ses navigateurs
RUN playwright install chromium
RUN playwright install-deps chromium

# Copier le code de l'application
COPY api/ ./api/
COPY static/ ./static/
COPY templates/ ./templates/
COPY index.html .

# Créer le répertoire pour les résultats
RUN mkdir -p /tmp/rhscrap_results

# Exposer le port
EXPOSE 5000

# Variable d'environnement pour Flask
ENV FLASK_APP=api/app.py
ENV FLASK_ENV=production

# Commande pour démarrer l'application
CMD ["python", "api/app.py"] 
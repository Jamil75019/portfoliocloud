# 🚀 Guide de déploiement RHScrap sur une nouvelle VM

## 📋 Prérequis sur la nouvelle VM

### 1. Système d'exploitation
- **Linux** (Ubuntu 20.04+, CentOS 7+, Debian 10+)
- **Windows** (Windows 10/11 avec WSL2 ou Docker Desktop)
- **macOS** (avec Docker Desktop)

### 2. Installation de Docker

#### Sur Ubuntu/Debian :
```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer les dépendances
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Ajouter la clé GPG Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Ajouter le repository Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installer Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Redémarrer la session ou exécuter
newgrp docker
```

#### Sur CentOS/RHEL :
```bash
# Installer Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Démarrer et activer Docker
sudo systemctl start docker
sudo systemctl enable docker

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
newgrp docker
```

## 📦 Transfert du projet

### Option 1 : Via Git (Recommandé)
```bash
# Sur la nouvelle VM, cloner le projet
git clone <URL_DE_VOTRE_REPO> rhscrap
cd rhscrap
```

### Option 2 : Via SCP/SFTP
```bash
# Depuis votre machine actuelle
scp -r /chemin/vers/rhscrap user@nouvelle-vm:/home/user/

# Ou avec rsync (plus efficace)
rsync -avz --exclude='.git' --exclude='venv' /chemin/vers/rhscrap/ user@nouvelle-vm:/home/user/rhscrap/
```

### Option 3 : Via archive
```bash
# Sur votre machine actuelle
tar -czf rhscrap.tar.gz --exclude='.git' --exclude='venv' --exclude='results' rhscrap/

# Transférer l'archive
scp rhscrap.tar.gz user@nouvelle-vm:/home/user/

# Sur la nouvelle VM
cd /home/user
tar -xzf rhscrap.tar.gz
cd rhscrap
```

## 🐳 Déploiement Docker

### 1. Vérification de la structure
```bash
# Vérifier que tous les fichiers sont présents
ls -la
# Vous devriez voir :
# - Dockerfile
# - docker-compose.yml
# - api/
# - static/
# - templates/
# - index.html
```

### 2. Construction et démarrage
```bash
# Construire l'image Docker
docker-compose build

# Démarrer l'application
docker-compose up -d

# Vérifier que ça fonctionne
docker-compose ps
```

### 3. Vérification de l'application
```bash
# Tester l'accès local
curl http://localhost:5000

# Voir les logs si nécessaire
docker-compose logs -f
```

## 🌐 Configuration réseau

### Accès local uniquement
L'application est accessible sur `http://localhost:5000`

### Accès depuis l'extérieur
Si vous voulez accéder depuis d'autres machines :

#### 1. Ouvrir le port dans le firewall
```bash
# Ubuntu/Debian
sudo ufw allow 5000

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

#### 2. Modifier docker-compose.yml (optionnel)
```yaml
ports:
  - "0.0.0.0:5000:5000"  # Accès depuis n'importe quelle IP
```

### Accès via domaine/IP publique
```bash
# Remplacer localhost par l'IP de votre VM
http://VOTRE_IP_VM:5000
```

## 🔧 Configuration avancée

### 1. Variables d'environnement
Créer un fichier `.env` :
```bash
# .env
FLASK_ENV=production
FLASK_DEBUG=false
PORT=5000
```

### 2. Configuration avec reverse proxy (Nginx)
```bash
# Installer Nginx
sudo apt install nginx

# Configuration Nginx
sudo nano /etc/nginx/sites-available/rhscrap
```

Contenu du fichier Nginx :
```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/rhscrap /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 📊 Monitoring et maintenance

### 1. Vérifier le statut
```bash
# Statut des conteneurs
docker-compose ps

# Utilisation des ressources
docker stats

# Logs en temps réel
docker-compose logs -f
```

### 2. Mise à jour de l'application
```bash
# Arrêter l'application
docker-compose down

# Récupérer les dernières modifications
git pull

# Reconstruire et redémarrer
docker-compose up -d --build
```

### 3. Sauvegarde des données
```bash
# Sauvegarder les résultats
tar -czf backup_results_$(date +%Y%m%d).tar.gz results/

# Sauvegarder l'image Docker
docker save rhscrap_rhscrap > rhscrap_backup.tar
```

## 🚨 Dépannage

### Problèmes courants

#### 1. Port déjà utilisé
```bash
# Vérifier les ports utilisés
sudo netstat -tulpn | grep 5000

# Changer le port dans docker-compose.yml
ports:
  - "8080:5000"
```

#### 2. Problèmes de permissions
```bash
# Vérifier les permissions Docker
sudo chmod 666 /var/run/docker.sock

# Ou ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
```

#### 3. Problèmes de mémoire
```bash
# Augmenter la mémoire dans docker-compose.yml
shm_size: '4gb'
```

#### 4. Problèmes de réseau
```bash
# Vérifier la connectivité
ping google.com

# Vérifier les ports ouverts
sudo ss -tulpn
```

## 🔄 Script de déploiement automatique

Créer un script `deploy.sh` :
```bash
#!/bin/bash

echo "🚀 Déploiement automatique RHScrap"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non installé"
    exit 1
fi

# Arrêter l'ancienne version
docker-compose down

# Récupérer les mises à jour
git pull

# Reconstruire et démarrer
docker-compose up -d --build

# Vérifier le statut
sleep 10
if curl -s http://localhost:5000 > /dev/null; then
    echo "✅ Déploiement réussi"
else
    echo "❌ Problème de déploiement"
    docker-compose logs
fi
```

## 📝 Checklist de déploiement

- [ ] Docker installé sur la nouvelle VM
- [ ] Projet transféré sur la nouvelle VM
- [ ] Structure des fichiers vérifiée
- [ ] Image Docker construite
- [ ] Application démarrée
- [ ] Accès local testé
- [ ] Firewall configuré (si nécessaire)
- [ ] Monitoring configuré
- [ ] Sauvegarde planifiée

## 🎯 Avantages de cette approche

✅ **Déploiement en 5 minutes** : Plus besoin de configurer Python, venv, etc.
✅ **Reproductible** : Même environnement partout
✅ **Isolé** : Pas de conflits avec d'autres applications
✅ **Scalable** : Facile à déployer sur plusieurs serveurs
✅ **Maintenable** : Mise à jour simple avec un seul commande

---

**Temps estimé pour un déploiement complet : 10-15 minutes** 
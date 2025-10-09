# RHScrap - Guide de déploiement Docker

## 🐳 Déploiement avec Docker

Ce guide vous explique comment déployer RHScrap partout facilement avec Docker, sans avoir besoin de configurer un environnement Python complexe.

## Prérequis

- Docker installé sur votre machine
- Docker Compose installé (inclus avec Docker Desktop)

## 🚀 Démarrage rapide

### 1. Construction et lancement

```bash
# Construire l'image et démarrer l'application
docker-compose up --build

# Ou en arrière-plan
docker-compose up -d --build
```

### 2. Accès à l'application

Une fois démarrée, l'application sera accessible sur :
- **Interface web** : http://localhost:5000
- **API** : http://localhost:5000/rhscrap/search

### 3. Arrêt de l'application

```bash
# Arrêter l'application
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v
```

## 📁 Structure des fichiers

```
rhscrap/
├── Dockerfile              # Configuration de l'image Docker
├── docker-compose.yml      # Orchestration des services
├── .dockerignore          # Fichiers ignorés par Docker
├── api/                   # Code backend Python
├── static/                # Fichiers statiques (CSS, JS)
├── templates/             # Templates HTML
├── index.html            # Page principale
└── results/              # Dossier monté pour les résultats
```

## 🔧 Configuration

### Variables d'environnement

Vous pouvez modifier le fichier `docker-compose.yml` pour ajuster :

- **Port** : Changez `5000:5000` pour utiliser un autre port
- **Mémoire** : Ajustez `shm_size: '2gb'` selon vos besoins
- **Redémarrage** : Modifiez `restart: unless-stopped`

### Volume des résultats

Les résultats de recherche sont sauvegardés dans le dossier `./results/` qui est monté dans le conteneur. Cela permet de conserver les données même après redémarrage du conteneur.

## 🐛 Dépannage

### Problèmes courants

1. **Port déjà utilisé**
   ```bash
   # Vérifier les ports utilisés
   netstat -tulpn | grep 5000
   
   # Changer le port dans docker-compose.yml
   ports:
     - "8080:5000"  # Utilise le port 8080 au lieu de 5000
   ```

2. **Problèmes de mémoire**
   ```bash
   # Augmenter la mémoire partagée
   shm_size: '4gb'
   ```

3. **Logs de l'application**
   ```bash
   # Voir les logs en temps réel
   docker-compose logs -f
   
   # Voir les logs d'un service spécifique
   docker-compose logs rhscrap
   ```

### Nettoyage

```bash
# Supprimer les images non utilisées
docker image prune

# Supprimer tous les conteneurs et images
docker system prune -a

# Supprimer les volumes
docker volume prune
```

## 🌐 Déploiement en production

### Avec Docker Compose

```bash
# Démarrer en mode production
docker-compose -f docker-compose.yml up -d

# Vérifier le statut
docker-compose ps
```

### Avec Docker Swarm

```bash
# Initialiser Swarm
docker swarm init

# Déployer le stack
docker stack deploy -c docker-compose.yml rhscrap
```

### Avec Kubernetes

Créez un fichier `k8s-deployment.yaml` :

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rhscrap
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rhscrap
  template:
    metadata:
      labels:
        app: rhscrap
    spec:
      containers:
      - name: rhscrap
        image: rhscrap:latest
        ports:
        - containerPort: 5000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: rhscrap-service
spec:
  selector:
    app: rhscrap
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
```

## 🔒 Sécurité

- L'application tourne en mode headless dans le conteneur
- Les permissions sont limitées
- Pas d'accès root nécessaire
- Isolation complète de l'environnement

## 📊 Monitoring

```bash
# Voir l'utilisation des ressources
docker stats

# Voir les processus dans le conteneur
docker exec -it rhscrap_rhscrap_1 ps aux
```

## 🎯 Avantages du déploiement Docker

✅ **Simplicité** : Plus besoin de configurer Python, venv, etc.
✅ **Portabilité** : Fonctionne sur n'importe quel système avec Docker
✅ **Isolation** : Environnement propre et sécurisé
✅ **Scalabilité** : Facile à déployer sur plusieurs serveurs
✅ **Maintenance** : Mise à jour simple avec `docker-compose up --build`
✅ **Persistance** : Les résultats sont conservés via les volumes

---

**Note** : Cette configuration Docker inclut toutes les dépendances nécessaires pour Playwright et le web scraping, y compris les navigateurs headless. 
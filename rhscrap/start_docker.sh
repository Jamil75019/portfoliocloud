#!/bin/bash

echo "🐳 RHScrap - Démarrage avec Docker"
echo "=================================="

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi

# Vérifier si Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Veuillez installer Docker Compose d'abord."
    exit 1
fi

# Créer le dossier results s'il n'existe pas
mkdir -p results

echo "🔨 Construction de l'image Docker..."
docker-compose build

echo "🚀 Démarrage de l'application..."
docker-compose up -d

echo "⏳ Attente du démarrage..."
sleep 5

# Vérifier si l'application est démarrée
if curl -s http://localhost:5000 > /dev/null; then
    echo "✅ RHScrap est maintenant accessible sur :"
    echo "   🌐 Interface web : http://localhost:5000"
    echo "   🔌 API : http://localhost:5000/rhscrap/search"
    echo ""
    echo "📊 Pour voir les logs : docker-compose logs -f"
    echo "🛑 Pour arrêter : docker-compose down"
else
    echo "⚠️  L'application prend du temps à démarrer..."
    echo "📊 Vérifiez les logs avec : docker-compose logs -f"
fi 
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import json
from datetime import datetime
from rhscrap_server import search_bing, SearchFilters, save_results, filter_profile

app = Flask(__name__)
CORS(app)

@app.route('/rhscrap/search', methods=['POST'])
def search():
    try:
        print("=== DEBUT RECHERCHE ===")
        data = request.json
        print(f"Data reçue: {data}")
        
        query = data.get('query')
        enterprise = data.get('enterprise')
        location = data.get('location')
        print(f"Query: {query}, Enterprise: {enterprise}, Location: {location}")

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Créer les filtres
        print("Création des filtres...")
        filters = SearchFilters(
            entreprise=enterprise if enterprise else None,
            localisation=location if location else None
        )
        print(f"Filtres créés: {filters}")

        # Lancer la recherche
        print("Lancement de la recherche Bing...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        profiles = loop.run_until_complete(search_bing(query, max_pages=5))
        loop.close()
        print(f"Recherche terminée, {len(profiles)} profils trouvés")

        # Filtrer les résultats si nécessaire
        if enterprise or location:
            print("Filtrage des profils...")
            profiles = [p for p in profiles if filter_profile(p, filters)]
            print(f"Après filtrage: {len(profiles)} profils")

        # Sauvegarder les résultats
        print("Sauvegarde des résultats...")
        results_dir = os.path.join('results')
        os.makedirs(results_dir, exist_ok=True)
        filename = save_results(profiles, query, results_dir)
        print(f"Résultats sauvegardés dans: {filename}")

        # Préparer la réponse
        print("Préparation de la réponse...")
        response_data = {
            'profiles': [profile.to_dict() for profile in profiles],
            'resultUrl': f'/rhscrap/results/{os.path.basename(filename)}',
            'count': len(profiles)
        }
        print(f"Réponse préparée: {len(response_data['profiles'])} profils")

        return jsonify(response_data)

    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_msg = traceback.format_exc()
        print(f"=== ERREUR FLASK ===")
        print(f"ERREUR: {error_msg}")
        print(f"TRACEBACK: {traceback_msg}")
        print("=== FIN ERREUR ===")
        return jsonify({'error': error_msg, 'traceback': traceback_msg}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

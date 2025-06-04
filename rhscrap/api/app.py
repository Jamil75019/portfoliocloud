from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import json
from datetime import datetime
from rhscrap_server import search_bing, SearchFilters, save_results, filter_profile

app = Flask(__name__)
CORS(app)

@app.route('/rhscrap/search', methods=['POST'])  # Modifié ici !
def search():  # Retiré async pour le moment
    try:
        data = request.json
        query = data.get('query')
        enterprise = data.get('enterprise')
        location = data.get('location')

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Créer les filtres
        filters = SearchFilters(
            entreprise=enterprise if enterprise else None,
            localisation=location if location else None
        )

        # Lancer la recherche (on va devoir ajuster ça)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        profiles = loop.run_until_complete(search_bing(query, max_pages=5))
        loop.close()

        # Filtrer les résultats si nécessaire
        if enterprise or location:
            profiles = [p for p in profiles if filter_profile(p, filters)]

        # Sauvegarder les résultats
        results_dir = os.path.join('results')
        os.makedirs(results_dir, exist_ok=True)
        filename = save_results(profiles, query, results_dir)

        # Préparer la réponse
        response_data = {
            'profiles': [profile.to_dict() for profile in profiles],
            'resultUrl': f'/rhscrap/results/{os.path.basename(filename)}',
            'count': len(profiles)
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

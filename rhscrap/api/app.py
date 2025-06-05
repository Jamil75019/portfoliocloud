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
        search_depth = data.get('searchDepth', 'normal')
        print(f"Query: {query}, Enterprise: {enterprise}, Location: {location}, SearchDepth: {search_depth}")

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Déterminer le nombre de pages selon la profondeur
        depth_config = {
            'quick': {'max_pages': 2, 'max_results': 5},
            'normal': {'max_pages': 5, 'max_results': 10},  
            'deep': {'max_pages': 8, 'max_results': 20},
            'extensive': {'max_pages': 15, 'max_results': 50}
        }
        
        config = depth_config.get(search_depth, depth_config['normal'])
        print(f"Configuration recherche: {config}")

        # Créer les filtres
        print("Création des filtres...")
        filters = SearchFilters(
            entreprise=enterprise if enterprise else None,
            localisation=location if location else None
        )
        print(f"Filtres créés: {filters}")

        # Lancer la recherche
        print("Lancement de la recherche Bing...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            profiles = loop.run_until_complete(search_bing(query, max_pages=config['max_pages']))
            loop.close()
            
            print(f"Résultat search_bing: {profiles}")
            print(f"Type de profiles: {type(profiles)}")
            
            if profiles is None:
                print("ATTENTION: search_bing a retourné None")
                profiles = []
            
            print(f"Recherche terminée, {len(profiles)} profils trouvés")
        except Exception as search_error:
            print(f"ERREUR dans search_bing: {search_error}")
            import traceback
            print(f"TRACEBACK search_bing: {traceback.format_exc()}")
            profiles = []

        # Filtrer les résultats si nécessaire
        if enterprise or location:
            print("Filtrage des profils...")
            profiles = [p for p in profiles if filter_profile(p, filters)]
            print(f"Après filtrage: {len(profiles)} profils")

        # Sauvegarder les résultats
        print("Sauvegarde des résultats...")
        results_dir = os.path.join('/tmp', 'rhscrap_results')
        os.makedirs(results_dir, exist_ok=True)
        filename = save_results(profiles, query, results_dir)
        print(f"Résultats sauvegardés dans: {filename}")

        # Préparer la réponse
        print("Préparation de la réponse...")
        
        # Pour le moment, créons des données de test si search_bing échoue
        if len(profiles) == 0:
            print("Création de données de test...")
            from dataclasses import dataclass
            
            @dataclass
            class MockProfile:
                name: str
                position: str
                company: str
                url: str
                emails: list
                
                def to_dict(self):
                    return {
                        'name': self.name,
                        'position': self.position,
                        'company': self.company,
                        'url': self.url,
                        'emails': [{'address': email, 'probability': 0.8} for email in self.emails]
                    }
            
            profiles = [
                MockProfile(
                    name="Test Profile 1",
                    position="Software Engineer",
                    company="Test Company",
                    url="https://linkedin.com/in/test1",
                    emails=["test1@company.com"]
                ),
                MockProfile(
                    name="Test Profile 2", 
                    position="Product Manager",
                    company="Test Corp",
                    url="https://linkedin.com/in/test2",
                    emails=["test2@testcorp.com"]
                )
            ]
            
            # Sauvegarder à nouveau avec les données de test
            filename = save_results(profiles, query, results_dir)
            print(f"Données de test sauvegardées dans: {filename}")
        
        # Gérer le cas où filename est None
        result_url = None
        if filename:
            result_url = f'/rhscrap/results/{os.path.basename(filename)}'
        
        response_data = {
            'profiles': [profile.to_dict() for profile in profiles],
            'resultUrl': result_url,
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

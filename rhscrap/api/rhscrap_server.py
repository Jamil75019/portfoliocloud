import asyncio
from playwright.async_api import async_playwright
import os
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import json
from datetime import datetime
from tqdm import tqdm
import time
import random
import nest_asyncio
from dns_check import EmailVerifier
from urllib.parse import unquote

# Permet d'utiliser asyncio
nest_asyncio.apply()

@dataclass
class EmailFormat:
    pattern: str
    probability: float
    description: str

@dataclass
class LinkedInProfile:
    name: str
    position: str
    company: str
    description: str
    url: str
    emails: List[Tuple[str, float]]

    def to_dict(self):
        return {
            'name': self.name,
            'position': self.position,
            'company': self.company,
            'description': self.description,
            'url': self.url,
            'emails': [{'address': email, 'probability': prob} for email, prob in self.emails]
        }

@dataclass
class SearchFilters:
    entreprise: Optional[str] = None
    localisation: Optional[str] = None

# Réutiliser les fonctions existantes
def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_company_info(position: str, description: str) -> tuple:
    # Votre fonction existante extract_company_info
    # [Code existant]
    pass

def get_email_formats_for_company(company_name: str) -> List[EmailFormat]:
    # Votre fonction existante get_email_formats_for_company
    # [Code existant]
    pass

def generate_possible_emails(nom: str, domaine: str, company: str) -> List[Tuple[str, float]]:
    # Votre fonction existante generate_possible_emails
    # [Code existant]
    pass

async def clean_linkedin_title(title: str) -> tuple:
    """Nettoie le titre LinkedIn et extrait nom/poste (copié de v2 qui marche)"""
    if " | LinkedIn" in title:
        title = title.split(" | LinkedIn")[0]
    if " - LinkedIn" in title:
        title = title.split(" - LinkedIn")[0]
    parts = title.split(" - ")
    if len(parts) >= 2:
        name = parts[0].strip()
        position = " - ".join(parts[1:]).strip()
        return name, position
    return title.strip(), ""

def save_results(profiles: List[LinkedInProfile], query: str, results_dir: str) -> str:
    """
    Sauvegarde les résultats dans un fichier JSON
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rhscrap_results_{query.replace(' ', '_')}_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        # Convertir les profils en dictionnaires
        results_data = {
            'query': query,
            'timestamp': timestamp,
            'count': len(profiles),
            'profiles': [profile.to_dict() for profile in profiles]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        print(f"Résultats sauvegardés dans: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")
        return None

async def search_bing(query: str, max_pages: int = 5) -> List[LinkedInProfile]:
    """
    Recherche des profils LinkedIn via Bing
    """
    profiles = []
    max_profiles_per_page = 10
    
    async with async_playwright() as p:
        try:
            # Lancer le navigateur en mode headless
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            page = await browser.new_page()
            
            # Ajouter des headers pour simuler un vrai navigateur
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Scanner plusieurs pages de Bing si nécessaire
            for page_num in range(1, max_pages + 1):
                print(f"\n=== PAGE BING {page_num}/{max_pages} ===")
                
                # Construire la requête Bing pour LinkedIn
                search_query = f'{query} site:linkedin.com/in'
                # Ajouter le paramètre first pour paginer (Bing utilise first=11 pour page 2, first=21 pour page 3, etc.)
                first_param = (page_num - 1) * 10 + 1
                bing_url = f'https://www.bing.com/search?q={search_query.replace(" ", "+")}&first={first_param}'
                
                print(f"Recherche Bing: {bing_url}")
                
                await page.goto(bing_url, wait_until='networkidle', timeout=30000)
                
                # Attendre un peu plus pour que les résultats se chargent
                await asyncio.sleep(2)
                
                # Extraire les liens LinkedIn avec leurs descriptions
                search_results = await page.evaluate(f'''() => {{
                    const results = [];
                    
                    // Chercher les résultats de recherche Bing
                    const resultContainers = document.querySelectorAll('.b_algo, .b_title');
                    
                    for (let container of resultContainers) {{
                        const linkEl = container.querySelector('a[href*="linkedin.com/in/"]');
                        if (linkEl) {{
                            let href = linkEl.href;
                            if (href && href.includes('linkedin.com/in/')) {{
                                // Nettoyer l'URL
                                href = href.split('?')[0];
                                
                                // Extraire le titre et la description
                                const titleEl = container.querySelector('h2, .b_title h2, .b_algo h2');
                                const descEl = container.querySelector('.b_caption p, .b_snippet, .b_algoSlug');
                                
                                const title = titleEl ? titleEl.textContent.trim() : '';
                                const description = descEl ? descEl.textContent.trim() : '';
                                
                                results.push({{
                                    url: href,
                                    title: title,
                                    description: description
                                }});
                            }}
                        }}
                    }}
                    
                    console.log('Résultats Bing page {page_num}:', results);
                    return results.slice(0, {max_profiles_per_page});
                }}''')
                
                print(f"Page {page_num}: Trouvé {len(search_results)} résultats")
                
                # Traiter chaque résultat de cette page
                for result in search_results:
                    try:
                        print(f"Traitement: {result['url']}")
                        
                        # Vérifier si on a déjà ce profil (éviter les doublons)
                        if any(p.url == result['url'] for p in profiles):
                            print(f"Profil déjà traité, skip: {result['url']}")
                            continue
                        
                        # Extraire le nom depuis l'URL
                        name_from_url = result['url'].split('/in/')[-1].replace('-', ' ').title()
                        if name_from_url.endswith('/'):
                            name_from_url = name_from_url[:-1]
                        
                        # Nettoyer le nom (enlever les codes)
                        name_clean = re.sub(r'\s+[A-Z0-9]{8,}$', '', name_from_url)
                        
                        # Extraire le poste et l'entreprise depuis le titre et la description Bing
                        position, company = extract_position_company_from_bing(result['title'], result['description'])
                        
                        # Générer des emails avec la vraie entreprise si trouvée
                        company_for_email = company if company != "Entreprise à déterminer" else "company"
                        emails = generate_emails(name_clean, company_for_email)
                        
                        profile = LinkedInProfile(
                            name=name_clean,
                            position=position,
                            company=company,
                            description=result['description'][:200] + "..." if len(result['description']) > 200 else result['description'],
                            url=result['url'],
                            emails=emails
                        )
                        
                        profiles.append(profile)
                        print(f"✅ Profil ajouté: {profile.name} - {profile.position} chez {profile.company}")
                        
                    except Exception as e:
                        print(f"❌ Erreur lors du traitement de {result.get('url', 'URL inconnue')}: {e}")
                        continue
                
                # Petite pause entre les pages pour éviter d'être détecté
                if page_num < max_pages:
                    print(f"Pause avant page suivante...")
                    await asyncio.sleep(3)
            
            await browser.close()
            print(f"\n=== RECHERCHE TERMINÉE ===")
            print(f"Total de profils trouvés: {len(profiles)}")
            
        except Exception as e:
            print(f"Erreur générale dans search_bing: {e}")
            return []
    
    return profiles

def generate_emails(name: str, company: str) -> List[Tuple[str, float]]:
    """
    Génère des emails probables basés sur le nom et l'entreprise
    """
    emails = []
    
    if not name or not company:
        return emails
    
    # Nettoyer les données
    name_parts = re.sub(r'[^a-zA-Z\s]', '', name.lower()).split()
    company_clean = re.sub(r'[^a-zA-Z0-9]', '', company.lower())
    
    if len(name_parts) >= 2:
        first = name_parts[0]
        last = name_parts[-1]
        
        # Formats d'email courants
        formats = [
            f"{first}.{last}@{company_clean}.com",
            f"{first}{last}@{company_clean}.com", 
            f"{first[0]}{last}@{company_clean}.com",
            f"{last}@{company_clean}.com",
            f"{first}@{company_clean}.com"
        ]
        
        probabilities = [0.8, 0.7, 0.6, 0.5, 0.4]
        
        for email, prob in zip(formats, probabilities):
            emails.append((email, prob))
    
    return emails

def extract_position_company_from_bing(title: str, description: str) -> Tuple[str, str]:
    """
    Extrait le poste et l'entreprise depuis le titre et la description Bing
    """
    full_text = f"{title} {description}".lower()
    
    # Extraire le poste
    position = "Poste à déterminer"
    
    # Patterns pour les postes courants
    position_patterns = [
        r'directeur(?:rice)?\s+(?:des?\s+)?(?:ressources\s+humaines|rh)',
        r'responsable\s+(?:des?\s+)?(?:ressources\s+humaines|rh)',
        r'manager\s+(?:des?\s+)?(?:ressources\s+humaines|rh)',
        r'chef\s+(?:des?\s+)?(?:ressources\s+humaines|rh)',
        r'drh|drhei|drhou',
        r'rrh',
        r'directeur(?:rice)?\s+(?:général|marketing|commercial|financier|technique)',
        r'responsable\s+(?:marketing|commercial|ventes|production|qualité)',
        r'manager\s+(?:marketing|commercial|ventes|équipe)',
        r'consultant(?:e)?\s+(?:en|rh|ressources)',
        r'chargé(?:e)?\s+(?:de|du|des)\s+(?:recrutement|formation|paie)',
        r'président(?:e)?',
        r'pdg|ceo|cto|cfo',
        r'associé(?:e)?\s+(?:fondateur|gérant)',
        r'expert(?:e)?\s+(?:en|comptable)'
    ]
    
    for pattern in position_patterns:
        match = re.search(pattern, full_text)
        if match:
            position = match.group(0).title()
            break
    
    # Extraire l'entreprise
    company = "Entreprise à déterminer"
    
    # Patterns pour les entreprises connues
    company_patterns = [
        r'orange(?:\s+france|\s+tunisie)?',
        r'total(?:\s+energies)?',
        r'bnp\s+paribas',
        r'société\s+générale',
        r'crédit\s+agricole',
        r'peugeot(?:\s+citroën)?',
        r'renault(?:\s+nissan)?',
        r'airbus(?:\s+defence)?',
        r'thales(?:\s+group)?',
        r'capgemini',
        r'accenture',
        r'deloitte',
        r'pwc',
        r'kpmg',
        r'ernst\s+&\s+young',
        r'mckinsey',
        r'microsoft',
        r'google',
        r'amazon',
        r'apple',
        r'ibm',
        r'oracle'
    ]
    
    # Chercher dans le titre d'abord
    for pattern in company_patterns:
        match = re.search(pattern, title.lower())
        if match:
            company = match.group(0).title()
            break
    
    # Si pas trouvé dans le titre, chercher dans la description
    if company == "Entreprise à déterminer":
        for pattern in company_patterns:
            match = re.search(pattern, description.lower())
            if match:
                company = match.group(0).title()
                break
    
    # Pattern générique "chez [Entreprise]"
    if company == "Entreprise à déterminer":
        chez_match = re.search(r'chez\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', title + " " + description)
        if chez_match:
            company = chez_match.group(1)
    
    return position, company

def filter_profile(profile: LinkedInProfile, filters: SearchFilters) -> bool:
    """
    Filtre un profil selon les critères donnés
    """
    if filters.entreprise:
        if filters.entreprise.lower() not in profile.company.lower():
            return False
    
    if filters.localisation:
        # Rechercher dans la position et la description
        location_text = f"{profile.position} {profile.description}".lower()
        if filters.localisation.lower() not in location_text:
            return False
    
    return True

def decode_url_name(url: str) -> str:
    """Décode les noms depuis l'URL LinkedIn et nettoie les codes parasites"""
    try:
        # Extraire la partie après /in/
        name_part = url.split('/in/')[-1]
        
        # Enlever le slash final si présent
        if name_part.endswith('/'):
            name_part = name_part[:-1]
        
        # Décoder l'URL (pour La%C3%Abtitia -> Laëtitia)
        name_decoded = unquote(name_part)
        
        # Remplacer les tirets par des espaces
        name_with_spaces = name_decoded.replace('-', ' ')
        
        # Nettoyer les codes parasites de façon simple mais efficace
        # Pattern pour les codes LinkedIn (séquences alphanumériques de 8+ caractères)
        name_clean = re.sub(r'\s+[A-Za-z0-9]{8,}$', '', name_with_spaces)
        
        # Capitaliser proprement
        name_parts = name_clean.split()
        name_final = ' '.join([part.capitalize() for part in name_parts if part])
        
        return name_final
        
    except Exception as e:
        print(f"Erreur lors du décodage du nom: {e}")
        return ""

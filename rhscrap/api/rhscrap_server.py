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
    # Votre fonction existante clean_linkedin_title
    # [Code existant]
    pass

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
            
            # Construire la requête Bing pour LinkedIn (recherche plus simple)
            search_query = f'{query} site:linkedin.com/in'
            bing_url = f'https://www.bing.com/search?q={search_query.replace(" ", "+")}'
            
            print(f"Recherche Bing: {bing_url}")
            
            await page.goto(bing_url, wait_until='networkidle', timeout=30000)
            
            # Attendre un peu plus pour que les résultats se chargent
            await asyncio.sleep(3)
            
            # Extraire les liens LinkedIn
            linkedin_links = await page.evaluate('''() => {
                const links = [];
                
                // Plusieurs sélecteurs pour trouver les liens LinkedIn
                const selectors = [
                    'a[href*="linkedin.com/in/"]',
                    'a[href*="linkedin.com"]',
                    'h2 a[href*="linkedin.com"]',
                    '.b_algo h2 a[href*="linkedin.com"]',
                    '.b_title a[href*="linkedin.com"]'
                ];
                
                for (let selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    for (let el of elements) {
                        let href = el.href;
                        if (href && href.includes('linkedin.com/in/') && !links.includes(href)) {
                            // Nettoyer l'URL (enlever les paramètres Bing)
                            href = href.split('?')[0];
                            links.push(href);
                        }
                    }
                }
                
                console.log('Liens trouvés:', links);
                return links.slice(0, 10); // Max 10 liens par page
            }''')
            
            print(f"Trouvé {len(linkedin_links)} liens LinkedIn")
            
            # Si pas de liens trouvés, debugger la page
            if len(linkedin_links) == 0:
                print("Aucun lien trouvé, debug de la page...")
                page_content = await page.evaluate('''() => {
                    return {
                        title: document.title,
                        url: window.location.href,
                        allLinks: Array.from(document.querySelectorAll('a')).slice(0, 5).map(a => a.href),
                        hasResults: !!document.querySelector('.b_algo, .b_title')
                    };
                }''')
                print(f"Debug page: {page_content}")
            
            # Visiter chaque profil LinkedIn
            for link in linkedin_links[:5]:  # Limiter à 5 profils pour le test
                try:
                    print(f"Visite du profil: {link}")
                    await page.goto(link, wait_until='networkidle', timeout=10000)
                    
                    # Extraire les infos du profil
                    profile_data = await page.evaluate('''() => {
                        const getName = () => {
                            return document.querySelector('h1')?.textContent?.trim() || 'Nom non trouvé';
                        };
                        
                        const getPosition = () => {
                            const selectors = [
                                '.text-body-medium.break-words',
                                '.top-card-layout__headline',
                                '[data-generated-suggestion-target]'
                            ];
                            for (let selector of selectors) {
                                const el = document.querySelector(selector);
                                if (el && el.textContent) return el.textContent.trim();
                            }
                            return 'Poste non trouvé';
                        };
                        
                        const getCompany = () => {
                            const text = getPosition();
                            const match = text.match(/(?:at|chez|@)\\s+(.+?)(?:$|\\||,)/i);
                            return match ? match[1].trim() : 'Entreprise non trouvée';
                        };
                        
                        return {
                            name: getName(),
                            position: getPosition(),
                            company: getCompany(),
                            url: window.location.href
                        };
                    }''')
                    
                    # Générer des emails probables
                    emails = generate_emails(profile_data['name'], profile_data['company'])
                    
                    profile = LinkedInProfile(
                        name=profile_data['name'],
                        position=profile_data['position'],
                        company=profile_data['company'],
                        description=profile_data['position'],
                        url=profile_data['url'],
                        emails=emails
                    )
                    
                    profiles.append(profile)
                    print(f"Profil ajouté: {profile.name}")
                    
                    # Pause pour éviter de se faire bloquer
                    await asyncio.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    print(f"Erreur lors du scraping de {link}: {e}")
                    continue
            
            await browser.close()
            
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

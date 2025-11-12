import asyncio
from playwright.async_api import async_playwright
import os
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import sys
import csv
import json
import urllib.parse
from datetime import datetime
from tqdm import tqdm
import time
import random
import customtkinter as ctk
import threading
from tkinter import ttk
import tkinter as tk
from tkinter import messagebox
import nest_asyncio
import asyncio.events
from dns_check import EmailVerifier
import webbrowser
import queue
from tkinter import filedialog

# Permet d'utiliser asyncio avec tkinter
nest_asyncio.apply()

# Configuration de l'apparence
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Version de l'application
APP_VERSION = "2.0.0"

# Constantes pour les tooltips
TOOLTIPS = {
    "search": "Entrez vos mots-clés de recherche (poste, entreprise, localisation...)",
    "enterprise_filter": "Filtrer les résultats pour une entreprise spécifique",
    "location_filter": "Filtrer les résultats par région ou ville",
    "pages": "Nombre de pages de résultats à analyser (plus de pages = plus de résultats mais plus long)",
    "verify_emails": "Vérifie la validité des emails via DNS et SMTP (recommandé mais plus lent)",
    "start": "Lancer la recherche avec les paramètres configurés",
    "stop": "Arrêter la recherche en cours",
    "help": "Afficher l'aide et la documentation"
}

# Texte d'aide
HELP_TEXT = """
ðŸ” LinkedIn Profile Scraper - Guide d'utilisation

1. Recherche
   - Entrez vos mots-clés (poste, entreprise, localisation)
   - Exemple : "RH France Orange" ou "Recruteur Paris"

2. Filtres
   - Entreprise : Limite les résultats à une entreprise spécifique
   - Localisation : Filtre par région ou ville en France

3. Options
   - Pages : Plus de pages = plus de résultats mais plus long
   - Vérification emails : Validation technique des emails trouvés

4. Résultats
   - Sauvegardés automatiquement dans le dossier 'resultatsv2'
   - Format : TXT avec horodatage

5. Conseils
   - Commencez par une recherche large puis affinez
   - La vérification d'emails peut ralentir le processus
   - Utilisez les filtres pour des résultats plus précis

Pour plus d'informations ou support :
support@linkedinscraper.pro
"""

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
    emails: List[Tuple[str, float]]  # (email, probabilité)

    def to_dict(self):
        return {
            'name': self.name,
            'position': self.position,
            'company': self.company,
            'description': self.description,
            'url': self.url,
            'emails': '; '.join([f"{email} ({prob:.0%})" for email, prob in self.emails])
        }

@dataclass
class SearchFilters:
    entreprise: Optional[str] = None
    localisation: Optional[str] = None

@dataclass
class SearchHistoryItem:
    query: str
    timestamp: str
    filters: SearchFilters
    results_count: int = 0
    file_path: str = ""
    
    def to_dict(self):
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "filters": {
                "entreprise": self.filters.entreprise,
                "localisation": self.filters.localisation
            },
            "results_count": self.results_count,
            "file_path": self.file_path
        }
    
    @classmethod
    def from_dict(cls, data):
        filters = SearchFilters(
            entreprise=data["filters"].get("entreprise"),
            localisation=data["filters"].get("localisation")
        )
        return cls(
            query=data["query"],
            timestamp=data["timestamp"],
            filters=filters,
            results_count=data.get("results_count", 0),
            file_path=data.get("file_path", "")
        )

class SearchHistory:
    def __init__(self, max_items=20):
        self.max_items = max_items
        self.items = []
        self.history_file = os.path.join("resultatsv2", "search_history.json")
        self.load_history()
    
    def add_search(self, item: SearchHistoryItem):
        # Ajouter la recherche en tête de liste
        self.items.insert(0, item)
        
        # Limiter le nombre d'éléments dans l'historique
        if len(self.items) > self.max_items:
            self.items = self.items[:self.max_items]
            
        # Sauvegarder l'historique
        self.save_history()
    
    def load_history(self):
        try:
            # Créer le répertoire resultatsv2 s'il n'existe pas
            os.makedirs("resultatsv2", exist_ok=True)
            
            # Vérifier si le fichier existe
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.items = [SearchHistoryItem.from_dict(item) for item in data]
        except Exception as e:
            print(f"Erreur lors du chargement de l'historique: {str(e)}")
            self.items = []
    
    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json_data = [item.to_dict() for item in self.items]
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de l'historique: {str(e)}")
    
    def get_items(self):
        return self.items
    
    def clear_history(self):
        self.items = []
        self.save_history()

def clean_text(text: str) -> str:
    # Nettoie le texte des caractères spéciaux et des espaces multiples
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_company_info(position: str, description: str) -> tuple:
    # Base de données enrichie des entreprises et leurs domaines
    company_domains = {
        # Grandes entreprises françaises
        "Orange": ("Orange", "orange.com"),
        "Société Générale": ("Société Générale", "socgen.com"),
        "BNP Paribas": ("BNP Paribas", "bnpparibas.com"),
        "Total": ("TotalEnergies", "totalenergies.com"),
        "Carrefour": ("Carrefour", "carrefour.com"),
        "Auchan": ("Auchan", "auchan.fr"),
        "Leclerc": ("E.Leclerc", "e-leclerc.com"),
        "Renault": ("Renault Group", "renault.com"),
        "Peugeot": ("Peugeot", "peugeot.com"),
        "CitroÃ«n": ("CitroÃ«n", "citroen.com"),
        "Air France": ("Air France", "airfrance.com"),
        "SNCF": ("SNCF", "sncf.com"),
        "EDF": ("EDF", "edf.fr"),
        "Engie": ("Engie", "engie.com"),
        "Veolia": ("Veolia", "veolia.com"),
        "Vinci": ("Vinci", "vinci.com"),
        "Bouygues": ("Bouygues", "bouygues.com"),
        "Capgemini": ("Capgemini", "capgemini.com"),
        "Atos": ("Atos", "atos.net"),
        "Sopra Steria": ("Sopra Steria", "soprasteria.com"),
        
        # Entreprises tech internationales
        "Google": ("Google", "google.com"),
        "Microsoft": ("Microsoft", "microsoft.com"),
        "Apple": ("Apple", "apple.com"),
        "Amazon": ("Amazon", "amazon.com"),
        "Meta": ("Meta", "meta.com"),
        "Facebook": ("Meta", "meta.com"),
        "LinkedIn": ("LinkedIn", "linkedin.com"),
        "Twitter": ("Twitter", "twitter.com"),
        "IBM": ("IBM", "ibm.com"),
        "Intel": ("Intel", "intel.com"),
        "Oracle": ("Oracle", "oracle.com"),
        "SAP": ("SAP", "sap.com"),
        
        # Cabinets de conseil
        "McKinsey": ("McKinsey & Company", "mckinsey.com"),
        "BCG": ("Boston Consulting Group", "bcg.com"),
        "Bain": ("Bain & Company", "bain.com"),
        "Accenture": ("Accenture", "accenture.com"),
        "Deloitte": ("Deloitte", "deloitte.com"),
        "KPMG": ("KPMG", "kpmg.com"),
        "EY": ("EY", "ey.com"),
        "PwC": ("PwC", "pwc.com")
    }
    
    text = f"{position} {description}".lower()
    
    # Patterns améliorés pour trouver l'entreprise
    patterns = [
        r'(?:chez|at|-)\s+([A-Za-z][A-Za-z\s&\.]+?)(?:\s|$)',
        r'(?:[@]|[à])\s+([A-Za-z][A-Za-z\s&\.]+?)(?:\s|$)',
        r'(?:pour|for)\s+([A-Za-z][A-Za-z\s&\.]+?)(?:\s|$)',
        r'(?:^|\s)([A-Za-z][A-Za-z\s&\.]+?)\s+(?:group|groupe|sa|sas|inc|corp|corporation)(?:\s|$)',
        r'(?:^|\s)([A-Za-z][A-Za-z\s&\.]+?)\s+(?:france|europe|asia|americas)(?:\s|$)'
    ]
    
    # Chercher d'abord dans les entreprises connues
    for company, (name, domain) in company_domains.items():
        if company.lower() in text:
            return name, domain
    
    # Sinon chercher avec les patterns
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            company = matches[0].strip()
            company = company.strip().title()
            # Nettoyage du nom d'entreprise
            company = re.sub(r'\s+', ' ', company)
            company = re.sub(r'[^\w\s&\.-]', '', company)
            domain = company.lower().replace(' ', '').replace('&', '').replace('.', '') + ".com"
            return company, domain
    
    return "Entreprise inconnue", "unknown-company.com"

def get_email_formats_for_company(company_name: str) -> List[EmailFormat]:
    """Retourne les formats d'emails probables pour une entreprise donnée."""
    
    # Formats par défaut avec leurs probabilités
    default_formats = [
        EmailFormat("{prenom}.{nom}", 0.7, "Format standard international"),
        EmailFormat("{prenom[0]}{nom}", 0.4, "Format court"),
        EmailFormat("{nom}.{prenom}", 0.3, "Format inversé"),
        EmailFormat("{prenom}{nom}", 0.2, "Format sans séparateur"),
        EmailFormat("{prenom}-{nom}", 0.1, "Format avec tiret")
    ]
    
    # Formats spécifiques par entreprise
    company_specific_formats = {
        "Orange": [
            EmailFormat("{prenom}.{nom}", 0.9, "Format standard Orange"),
            EmailFormat("{prenom[0]}{nom}", 0.6, "Format court Orange"),
            EmailFormat("{nom}.{prenom}", 0.1, "Rare chez Orange")
        ],
        "Amazon": [
            EmailFormat("{prenom}.{nom}", 0.9, "Format standard Amazon"),
            EmailFormat("{prenom[0]}{nom}", 0.7, "Format court Amazon"),
            EmailFormat("{nom}.{prenom}", 0.1, "Rare chez Amazon")
        ],
        "Google": [
            EmailFormat("{prenom}{nom}", 0.9, "Format Google standard"),
            EmailFormat("{prenom}.{nom}", 0.5, "Format alternatif Google"),
            EmailFormat("{prenom}", 0.3, "Format prénom uniquement")
        ],
        "Microsoft": [
            EmailFormat("{prenom}.{nom}", 0.9, "Format standard Microsoft"),
            EmailFormat("{prenom}{nom}", 0.6, "Format sans point Microsoft"),
            EmailFormat("{prenom[0]}{nom}", 0.4, "Format court Microsoft")
        ],
        "Apple": [
            EmailFormat("{prenom[0]}{nom}", 0.8, "Format court Apple"),
            EmailFormat("{prenom}.{nom}", 0.6, "Format standard Apple")
        ],
        "Meta": [
            EmailFormat("{prenom}.{nom}", 0.9, "Format Meta standard"),
            EmailFormat("{prenom}", 0.5, "Format prénom uniquement Meta")
        ],
        "Société Générale": [
            EmailFormat("{prenom}.{nom}", 0.9, "Format SG standard"),
            EmailFormat("{prenom[0]}.{nom}", 0.5, "Format court SG")
        ],
        "BNP Paribas": [
            EmailFormat("{prenom}.{nom}", 0.9, "Format BNP standard"),
            EmailFormat("{prenom[0]}{nom}", 0.4, "Format court BNP")
        ]
    }
    
    return company_specific_formats.get(company_name, default_formats)

def generate_possible_emails(nom: str, domaine: str, company: str) -> List[Tuple[str, float]]:
    """Génère les emails possibles avec leurs probabilités."""
    # Nettoyage du nom
    nom = nom.lower()
    nom = re.sub(r'[Ã©Ã¨ÃªÃ«áº½]', 'e', nom)
    nom = re.sub(r'[àÃ¢Ã¤Ã£Ã¥]', 'a', nom)
    nom = re.sub(r'[Ã¯Ã®Ã¬Ã­]', 'i', nom)
    nom = re.sub(r'[Ã´Ã¶Ã²Ã³]', 'o', nom)
    nom = re.sub(r'[Ã¹Ã»Ã¼Ãº]', 'u', nom)
    nom = re.sub(r'[Ã¿Ã½]', 'y', nom)
    nom = re.sub(r'[Ã§]', 'c', nom)
    nom = re.sub(r'[Ã±]', 'n', nom)
    nom = re.sub(r'[^a-z\s\-]', '', nom)
    
    parts = nom.split()
    if len(parts) >= 2:
        prenom, nom = parts[0], parts[-1]
        
        # Obtenir les formats d'emails pour cette entreprise
        email_formats = get_email_formats_for_company(company)
        
        # Générer les emails avec leurs probabilités
        emails_with_prob = []
        for fmt in email_formats:
            email = fmt.pattern.format(
                prenom=prenom,
                nom=nom,
                p=prenom[0] if prenom else '',
                n=nom[0] if nom else ''
            )
            email = f"{email}@{domaine}"
            emails_with_prob.append((email, fmt.probability))
        
        # Trier par probabilité décroissante
        return sorted(emails_with_prob, key=lambda x: x[1], reverse=True)
    
    return []

async def clean_linkedin_title(title: str) -> tuple:
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

def clean_filename(query: str) -> str:
    """Nettoie la requête pour en faire un nom de fichier valide."""
    # Remplacer les caractères non autorisés par des underscores
    filename = re.sub(r'[\\/*?:"<>|]', '_', query)
    # Remplacer les espaces par des tirets
    filename = filename.replace(' ', '-')
    # Enlever les caractères accentués
    filename = re.sub(r'[Ã©Ã¨ÃªÃ«]', 'e', filename)
    filename = re.sub(r'[àÃ¢Ã¤]', 'a', filename)
    filename = re.sub(r'[Ã¯Ã®]', 'i', filename)
    filename = re.sub(r'[Ã´Ã¶]', 'o', filename)
    filename = re.sub(r'[Ã¹Ã»Ã¼]', 'u', filename)
    filename = re.sub(r'[Ã¿]', 'y', filename)
    filename = re.sub(r'[Ã§]', 'c', filename)
    return filename.lower()

def save_results(profiles: List[LinkedInProfile], query: str, custom_path=None):
    """Sauvegarde les résultats en TXT.
    
    Args:
        profiles: Liste des profils LinkedIn
        query: RequÃªte de recherche
        custom_path: Chemin personnalisé pour l'enregistrement (optionnel)
    """
    # Créer un nom de fichier basé sur la requête
    clean_query = clean_filename(query)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if custom_path:
        # Utiliser le chemin personnalisé
        txt_filename = os.path.join(custom_path, f"{clean_query}_{timestamp}.txt")
        # S'assurer que le répertoire existe (pas besoin d'utiliser dirname ici)
        os.makedirs(custom_path, exist_ok=True)
    else:
        # Créer le répertoire par défaut s'il n'existe pas
        os.makedirs("resultatsv2", exist_ok=True)
        txt_filename = os.path.join("resultatsv2", f"{clean_query}_{timestamp}.txt")
    
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write(f"Résultats de recherche LinkedIn pour : {query}\n")
        f.write(f"Date de recherche : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Nombre de profils trouvés : {len(profiles)}\n\n")
        
        for profile in profiles:
            f.write(f"ðŸ‘¤ {profile.name}\n")
            if profile.position:
                f.write(f"ðŸ’¼ Poste : {profile.position}\n")
            if profile.company != "Entreprise inconnue":
                f.write(f"ðŸ¢ Entreprise : {profile.company}\n")
            f.write(f"ðŸ”— {profile.url}\n")
            if profile.emails:
                f.write("ðŸ“§ Emails professionnels par probabilité :\n")
                for email, prob in profile.emails[:3]:
                    f.write(f"   âž” {email} ({prob:.0%} de probabilité)\n")
            f.write("\n" + "-"*50 + "\n\n")
    
    print(f"\nðŸ’¾ Résultats sauvegardés dans : {txt_filename}")
    return txt_filename

def is_plausible_full_name(name: str) -> bool:
    """Vérifie si la chaîne ressemble à un nom prénom exploitable."""
    if not name:
        return False
    name = name.strip()
    if any(ch.isdigit() for ch in name) or '@' in name:
        return False
    lower = name.lower()
    for k in ['talent', 'acquisition', 'recruit', 'recruteur', 'recrutement', 'hr', 'hrbp',
              'manager', 'head', 'lead', 'leader', 'director', 'directeur', 'directrice',
              'responsable', 'consultant', 'consultante', 'partner', 'owner', 'founder',
              'freelance', 'alternant', 'stagiaire', 'assistant', 'assistante', 'intern',
              'coach', 'sourcing', 'chargé', 'chargée', 'specialist', 'spécialiste',
              'développeur', 'engineer', 'ingénieur', 'product', 'marketing', 'sales',
              'cloud', 'data', 'avocat', 'juriste']:
        if k in lower:
            return False
    tokens = [t for t in re.split(r"\s+", name) if t]
    if len(tokens) < 2:
        return False
    first, last = tokens[0], tokens[-1]
    if last.endswith('.') or len(last.strip('.')) < 2:
        return False
    if len(first.strip('.')) < 2:
        return False
    if not first[0].isalpha() or not last[0].isalpha():
        return False
    return True

def find_name_in_text(text: str) -> Optional[str]:
    if not text:
        return None
    base = text.replace(' | LinkedIn', '').replace(' - LinkedIn', '')
    pattern = re.compile(r"\b([A-Z][A-Za-zÃ€-Ã–Ã˜-Ã¶Ã¸-Ã¿'\-]+)\s+(?:([a-zà-Ã¶Ã¸-Ã¿'\-]+)\s+)?([A-Z][A-Za-zÃ€-Ã–Ã˜-Ã¶Ã¸-Ã¿'\-]{2,})\b")
    for m in pattern.finditer(base):
        first = m.group(1)
        middle = (m.group(2) or '')
        last = m.group(3)
        candidate = f"{first} {last}"
        if is_plausible_full_name(candidate):
            return candidate
    return None

def extract_name_from_linkedin_url(href: Optional[str]) -> Optional[str]:
    try:
        if not href or 'linkedin.com/in/' not in href:
            return None
        slug = href.split('/in/', 1)[1].strip('/')
        slug = slug.split('/')[0]
        slug_decoded = urllib.parse.unquote(slug)
        cleaned = re.sub(r"[^A-Za-zÃ€-Ã–Ã˜-Ã¶Ã¸-Ã¿\-\s]", ' ', slug_decoded)
        parts = [p for p in re.split(r"[\-\s]+", cleaned) if p]
        if len(parts) >= 2:
            first, last = parts[0], parts[1]
            if len(last) >= 2 and len(first) >= 2:
                candidate = f"{first.title()} {last.title()}"
                if is_plausible_full_name(candidate):
                    return candidate
        return None
    except Exception:
        return None

async def search_bing(query: str, max_pages: int = 5, queue: queue.Queue = None) -> List[LinkedInProfile]:
    """Recherche des profils LinkedIn sur plusieurs pages de résultats Bing."""
    results = []
    
    def debug_log(message):
        # Ne plus afficher dans la console
        if queue:
            # Envoyer directement à la queue pour l'affichage dans l'interface
            try:
                queue.put(("log", message))
            except Exception as e:
                pass  # Ignorer silencieusement les erreurs

    try:
        debug_log("Initialisation de Playwright...")
        async with async_playwright() as p:
            debug_log("Lancement du navigateur...")
            browser = await p.chromium.launch(
                headless=False,  # Mode visible pour debug
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            debug_log("Configuration du contexte...")
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            debug_log("CrÃ©ation de la page...")
            page = await context.new_page()
            total_results = 0
            # DÃ©duplication inter-pages
            seen_urls: set = set()
            
            for current_page in range(max_pages):
                if not queue:  # Si la queue est None, le scraping a Ã©tÃ© arrÃªtÃ©
                    debug_log("Scraping arrÃªtÃ© par l'utilisateur")
                    break
                    
                debug_log(f"Analyse de la page {current_page + 1}...")
                
                try:
                    # Pagination DuckDuckGo: paramÃ¨tre s = offset (par blocs ~30)
                    offset = current_page * 30
                    url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}+&ia=web&s={offset}"
                    debug_log(f"URL de recherche : {url}")
                    
                    # Navigation avec retries
                    max_retries = 3
                    success = False
                    
                    for attempt in range(max_retries):
                        try:
                            debug_log(f"Tentative de navigation {attempt + 1}/{max_retries}...")
                            await page.goto(url, timeout=30000)  # 30 secondes de timeout
                            await page.wait_for_load_state('networkidle', timeout=30000)
                            
                            # Vérifier et gÃ©rer le CAPTCHA
                            try:
                                # Attendre que la vérification initiale se termine
                                debug_log("Attente de la vérification Bing...")
                                await asyncio.sleep(6)  # Attendre 6 secondes pour la vérification
                                
                                # Chercher le CAPTCHA avec le bon sÃ©lecteur
                                captcha_checkbox = await page.query_selector('label.cb-lb input[type="checkbox"]')
                                if captcha_checkbox:
                                    debug_log("CAPTCHA dÃ©tectÃ©, tentative de rÃ©solution automatique...")
                                    await captcha_checkbox.click()
                                    await asyncio.sleep(3)  # Attendre que le CAPTCHA se valide
                                    debug_log("CAPTCHA rÃ©solu automatiquement")
                                    
                                    # Attendre que la page se recharge
                                    await page.wait_for_load_state('networkidle', timeout=30000)
                                else:
                                    debug_log("Aucun CAPTCHA dÃ©tectÃ©, continuation normale")
                            except Exception as captcha_error:
                                debug_log(f"Erreur lors de la rÃ©solution du CAPTCHA: {captcha_error}")
                            
                            success = True
                            debug_log("Navigation rÃ©ussie")
                            break
                        except Exception as e:
                            debug_log(f"Erreur de navigation (tentative {attempt + 1}): {str(e)}")
                            if attempt == max_retries - 1:
                                raise
                            await asyncio.sleep(2)
                    
                    if not success:
                        debug_log("Ã‰chec de la navigation aprÃ¨s plusieurs tentatives")
                        continue
                    
                    # Scroll progressif
                    debug_log("Scroll de la page...")
                    for scroll in range(3):
                        await page.evaluate(f'window.scrollTo(0, {(scroll + 1) * 1000})')
                        await asyncio.sleep(0.5)
                    
                    # RÃ©cupÃ©ration DIRECTE des liens LinkedIn sur DuckDuckGo
                    debug_log("Recherche des résultats...")
                    links = await page.query_selector_all('a[data-testid="result-title-a"][href*="linkedin.com/in/"]')
                    debug_log(f"Liens LinkedIn trouvés : {len(links)}")

                    if not links:
                        debug_log("Aucun rÃ©sultat LinkedIn trouvÃ© sur cette page")
                        break

                    total_results += len(links)

                    for i, link in enumerate(links, 1):
                        try:
                            title = (await link.text_content()) or ""
                            href = await link.get_attribute('href')
                            # DÃ©duplication
                            if not href or href in seen_urls:
                                continue

                            # Essayer de rÃ©cupÃ©rer un snippet proche
                            description = ""
                            try:
                                container_handle = await link.evaluate_handle('el => el.closest(".result, .web-result")')
                                if container_handle:
                                    snippet_el = await container_handle.query_selector('.result__snippet, .result__body')
                                    if snippet_el:
                                        description = await snippet_el.text_content()
                            except Exception:
                                pass

                            if href and "linkedin.com/in/" in href:
                                debug_log(f"Traitement du profil : {title}")
                                name, position = await clean_linkedin_title(title)
                                # Renforcer l'extraction du nom
                                candidate_name = (name or "").strip()
                                if not is_plausible_full_name(candidate_name):
                                    alt = find_name_in_text(title)
                                    if alt and is_plausible_full_name(alt):
                                        candidate_name = alt
                                    else:
                                        alt2 = extract_name_from_linkedin_url(href)
                                        if alt2 and is_plausible_full_name(alt2):
                                            candidate_name = alt2
                                if is_plausible_full_name(candidate_name):
                                    company, domain = extract_company_info(position, description)

                                    # Mapping simple entreprise -> domaine
                                    text_all = f"{title} {position} {description}".lower()
                                    company_lower = (company or "").lower()
                                    known_domains = {
                                        'orange': ('Orange', 'orange.com'),
                                        'thales': ('Thales', 'thales.com'),
                                        'thalesgroup': ('Thales', 'thalesgroup.com'),
                                    }
                                    for key, (label, dom) in known_domains.items():
                                        if key in text_all or key in company_lower:
                                            company = label
                                            domain = dom
                                            break

                                    emails = generate_possible_emails(candidate_name, domain, company)

                                    profile = LinkedInProfile(
                                        name=clean_text(candidate_name),
                                        position=clean_text(position),
                                        company=company,
                                        description=clean_text(description),
                                        url=href,
                                        emails=emails
                                    )
                                    results.append(profile)
                                    seen_urls.add(href)
                                    debug_log(f"Profil ajoutÃ© : {name}")

                                    if queue:
                                        queue.put(("progress", (current_page * 10 + i) / (max_pages * 10)))

                            await asyncio.sleep(random.uniform(0.1, 0.3))

                        except Exception as e:
                            debug_log(f"Erreur lors du traitement d'un lien : {str(e)}")
                            continue
                    
                    # DÃ©lai entre les pages pour Ã©viter la dÃ©tection
                    await asyncio.sleep(random.uniform(1, 2))
                    
                except Exception as e:
                    debug_log(f"Erreur lors de l'analyse de la page {current_page + 1} : {str(e)}")
                    continue
            
            debug_log(f"Total des résultats analysés : {total_results}")
            await browser.close()
            debug_log("Navigateur fermÃ©")
            
    except Exception as e:
        debug_log(f"Erreur critique lors de la recherche : {str(e)}")
        if queue:
            queue.put(("error", str(e)))
    
    return results

def ask_yes_no(question: str) -> bool:
    """Demande une rÃ©ponse oui/non à l'utilisateur."""
    while True:
        reponse = input(f"{question} (o/n) âž¤ ").lower().strip()
        if reponse in ['o', 'oui', 'y', 'yes']:
            return True
        if reponse in ['n', 'non', 'no']:
            return False
        print("âŒ Veuillez rÃ©pondre par 'o' ou 'n'")

def get_search_filters() -> SearchFilters:
    """Demande les filtres de recherche à l'utilisateur."""
    filters = SearchFilters()
    
    # Filtre par entreprise
    if ask_yes_no("\nðŸ¢ Voulez-vous filtrer par entreprise spécifique ?"):
        filters.entreprise = input("Nom de l'entreprise âž¤ ").strip()
        print(f"âœ… Les résultats seront filtrés pour l'entreprise : {filters.entreprise}")
    
    # Filtre par localisation
    if ask_yes_no("\nðŸ“ Voulez-vous filtrer par localisation ?"):
        print("\nChoisissez une zone gÃ©ographique :")
        print("1. France")
        print("2. RÃ©gion spécifique")
        print("3. Ville spécifique")
        while True:
            try:
                choix = int(input("\nVotre choix (1-3) âž¤ "))
                if choix == 1:
                    filters.localisation = "France"
                    break
                elif choix == 2:
                    regions = [
                        "Auvergne-RhÃ´ne-Alpes", "Bourgogne-Franche-ComtÃ©", "Bretagne",
                        "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
                        "ÃŽle-de-France", "Normandie", "Nouvelle-Aquitaine",
                        "Occitanie", "Pays de la Loire", "Provence-Alpes-CÃ´te d'Azur"
                    ]
                    print("\nRÃ©gions disponibles :")
                    for i, region in enumerate(regions, 1):
                        print(f"{i}. {region}")
                    while True:
                        try:
                            choix_region = int(input("\nChoisissez une région (1-13) âž¤ "))
                            if 1 <= choix_region <= len(regions):
                                filters.localisation = regions[choix_region-1]
                                break
                        except ValueError:
                            print("âŒ Veuillez entrer un nombre valide")
                    break
                elif choix == 3:
                    filters.localisation = input("Entrez le nom de la ville âž¤ ").strip()
                    break
                else:
                    print("âŒ Veuillez choisir un nombre entre 1 et 3")
            except ValueError:
                print("âŒ Veuillez entrer un nombre valide")
    
    return filters

def filter_profile(profile: LinkedInProfile, filters: SearchFilters) -> bool:
    """Vérifie si un profil correspond aux filtres."""
    # Filtre par entreprise (plus tolÃ©rant: cherche aussi dans la description)
    if filters.entreprise:
        ent = filters.entreprise.lower()
        hay = f"{profile.company} {profile.position} {profile.description}".lower()
        if ent not in hay:
            return False
    
    # Filtre par localisation
    if filters.localisation:
        location_pattern = filters.localisation.lower()
        text_to_search = f"{profile.position} {profile.description}".lower()
        
        # Cas spÃ©cial pour la France
        if location_pattern == "france":
            french_patterns = ["france", "franÃ§ais", "franÃ§aise", "idf", "Ã®le-de-france", "ile-de-france"]
            if not any(pat in text_to_search for pat in french_patterns):
                return False
        else:
            if location_pattern not in text_to_search:
                return False
    
    return True

class LinkedInScraperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuration de la fenÃªtre
        self.title(f"LinkedIn Profile Scraper Pro v{APP_VERSION}")
        self.geometry("1000x800")
        self.minsize(800, 600)
        
        # Démarrer en plein Ã©cran
        self.after(100, lambda: self.state('zoomed'))  # Mode plein Ã©cran (avec bordures de fenÃªtre)
        
        # Variables
        self.search_var = ctk.StringVar()
        self.enterprise_var = ctk.StringVar()
        self.location_var = ctk.StringVar()
        self.pages_var = ctk.StringVar(value="5")
        self.use_enterprise_filter = ctk.BooleanVar(value=False)
        self.use_location_filter = ctk.BooleanVar(value=False)
        self.is_running = False
        self.current_task = None
        
        # Historique des recherches
        self.search_history = SearchHistory()
        self.history_visible = False
        
        # Queue pour la communication entre threads
        self.queue = queue.Queue()
        
        # CrÃ©ation de la boucle asyncio
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Ajout du vÃ©rificateur d'emails
        self.email_verifier = EmailVerifier()
        
        # CrÃ©ation de l'interface
        self.create_widgets()
        
        # Affichage du message de bienvenue
        self.show_welcome_message()
        
        # Démarrer le thread de mise à jour de l'interface
        self.check_queue()

    def check_queue(self):
        """Vérifie la queue pour les mises à jour de l'interface"""
        try:
            items_processed = 0
            # Traiter jusqu'à 10 éléments à la fois pour Ã©viter de bloquer l'interface
            while not self.queue.empty() and items_processed < 10:
                action, data = self.queue.get_nowait()
                
                if action == "log":
                    self.log_text.insert("end", f"{data}\n")
                    self.log_text.see("end")
                elif action == "progress":
                    self.progress_bar.set(data)
                    self.progress_label.configure(text=f"Progression : {int(data*100)}%")
                elif action == "complete":
                    self.on_scraping_complete()
                elif action == "error":
                    self.on_scraping_error(data)
                
                self.queue.task_done()
                items_processed += 1
                
            # Mise à jour forcÃ©e de l'interface
            self.update_idletasks()
            
        except Exception as e:
            print(f"Error in check_queue: {str(e)}")  # Debug log
        
        # Planifier la prochaine vérification
        self.after(100, self.check_queue)

    def scraping_thread(self, query, filters, nb_pages):
        """Thread sÃ©parÃ© pour le scraping"""
        try:
            # Créer une nouvelle boucle asyncio pour ce thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # ExÃ©cuter le scraping
            loop.run_until_complete(self.run_scraping_async(query, filters, nb_pages))
            loop.close()
        except Exception as e:
            self.queue.put(("error", str(e)))

    def start_scraping(self):
        """DÃ©marre le scraping avec une animation de chargement."""
        if not self.search_var.get().strip():
            messagebox.showerror("Erreur", "Veuillez entrer une recherche !")
            return
        
        self.is_running = True
        self.log_text.delete("1.0", "end")
        
        # Animation du bouton dÃ©marrer
        self.animate_button_click(self.start_button)
        
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.update_progress(0)  # RÃ©initialiser la barre de progression
        
        # PrÃ©paration des filtres
        filters = SearchFilters()
        if self.use_enterprise_filter.get():
            filters.entreprise = self.enterprise_var.get()
        if self.use_location_filter.get():
            filters.localisation = self.location_combo.get()
        
        # Lancement du thread de scraping
        query = self.search_var.get()
        nb_pages = int(self.pages_var.get())
        
        try:
            thread = threading.Thread(
                target=self.scraping_thread,
                args=(query, filters, nb_pages),
                daemon=True
            )
            thread.start()
        except Exception as e:
            self.queue.put(("error", f"Erreur lors du dÃ©marrage: {str(e)}"))

    def ask_for_export_location(self):
        """Demande à l'utilisateur où exporter les résultats."""
        from tkinter import filedialog
        
        # Demander le répertoire de destination
        export_dir = filedialog.askdirectory(
            title="Choisir un dossier pour l'exportation",
            initialdir=os.path.join(os.getcwd(), "resultatsv2")
        )
        
        if export_dir:
            self.queue.put(("log", f"\nðŸ’¾ Résultats seront exportÃ©s vers : {export_dir}"))
            return export_dir
        else:
            # Si l'utilisateur annule, utiliser le dossier par défaut
            default_dir = os.path.join(os.getcwd(), "resultatsv2")
            self.queue.put(("log", f"\nðŸ“ Utilisation du dossier par défaut : {default_dir}"))
            return default_dir

    async def run_scraping_async(self, query, filters, nb_pages):
        """ExÃ©cute le scraping de maniÃ¨re asynchrone"""
        try:
            # Utiliser la queue directement pour Ã©viter les problÃ¨mes de thread
            self.queue.put(("log", f"ðŸš€ DÃ©marrage de la recherche pour : {query}"))
            self.queue.put(("log", f"ðŸ“„ Nombre de pages à analyser : {nb_pages}"))
            
            dork_query = f"site:linkedin.com/in {query}"
            
            all_results = await search_bing(dork_query, max_pages=nb_pages, queue=self.queue)
            
            if filters.entreprise or filters.localisation:
                self.queue.put(("log", "\nðŸ” Application des filtres..."))
                results = [profile for profile in all_results if filter_profile(profile, filters)]
                if len(results) < len(all_results):
                    self.queue.put(("log", f"â„¹ï¸ {len(all_results) - len(results)} profils ont Ã©tÃ© filtrés"))
            else:
                results = all_results
            
            self.queue.put(("log", f"\nâœ… Recherche terminÃ©e ! {len(results)} profils trouvés."))
            
            total_profiles = len(results)
            for i, profile in enumerate(results, 1):
                self.queue.put(("log", f"\nðŸ‘¤ {profile.name}"))
                if profile.position:
                    self.queue.put(("log", f"ðŸ’¼ Poste : {profile.position}"))
                if profile.company != "Entreprise inconnue":
                    self.queue.put(("log", f"ðŸ¢ Entreprise : {profile.company}"))
                self.queue.put(("log", f"ðŸ”— {profile.url}"))
                
                if profile.emails:
                    self.queue.put(("log", "ðŸ“§ Emails professionnels :"))
                    
                    if self.verify_emails_var.get():
                        email_results = await self.email_verifier.verify_emails_batch(
                            [email for email, _ in profile.emails[:3]]
                        )
                        
                        for result in email_results:
                            self.queue.put(("log", f"   âž” {result['email']}"))
                            self.queue.put(("log", f"      âœ“ Score de validité : {result['score']}%"))
                            if result['score'] > 60:
                                self.queue.put(("log", f"      âœ… Email probablement valide"))
                                if 'smtp_valid' in result and result['smtp_valid']:
                                    self.queue.put(("log", f"      â­ VÃ©rifiÃ© par SMTP"))
                            else:
                                self.queue.put(("log", f"      âŒ Email probablement invalide"))
                            self.queue.put(("log", f"      â„¹ï¸ {result['details']}"))
                    else:
                        for email, prob in profile.emails[:3]:
                            self.queue.put(("log", f"   âž” {email} ({prob:.0%} de probabilité)"))
                
                self.queue.put(("progress", (i + 1) / (total_profiles + 1)))
            
            filename = ""
            if results:
                # Créer le dossier par défaut sans demander
                default_dir = os.path.join(os.getcwd(), "resultatsv2")
                filename = save_results(results, query, default_dir)
                self.queue.put(("log", f"\nâœ… Résultats sauvegardés dans : {filename}"))
                
                # Ajouter la recherche à l'historique
                history_item = SearchHistoryItem(
                    query=query,
                    timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"),
                    filters=filters,
                    results_count=len(results),
                    file_path=filename
                )
                self.search_history.add_search(history_item)
                
                # Mettre à jour l'affichage de l'historique si visible
                if self.history_visible:
                    self.update_history_display()
            
            self.queue.put(("complete", None))
            
        except Exception as e:
            self.queue.put(("error", str(e)))

    def safe_log(self, message):
        """Ajoute un message au log de maniÃ¨re thread-safe"""
        if self.queue:
            self.queue.put(("log", message))

    def safe_progress(self, value):
        """Met à jour la progression de maniÃ¨re thread-safe"""
        if self.queue:
            self.queue.put(("progress", value))

    def on_scraping_complete(self):
        """AppelÃ© quand le scraping est terminÃ©"""
        self.is_running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.update_progress(1.0)

    def on_scraping_error(self, error_message):
        """AppelÃ© en cas d'erreur pendant le scraping"""
        self.is_running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.log(f"\nâŒ Erreur : {error_message}")
        self.update_progress(0)

    def stop_scraping(self):
        """ArrÃªte le scraping avec animation."""
        if self.is_running:
            # Animation du bouton arrÃªter
            self.animate_button_click(self.stop_button)
            
            self.is_running = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.log("\nðŸ›‘ Recherche arrÃªtÃ©e par l'utilisateur")
            self.update_progress(0)

    def create_widgets(self):
        # DÃ©finition des couleurs personnalisées
        PRIMARY_COLOR = "#3498db"       # Bleu principal
        SECONDARY_COLOR = "#2ecc71"     # Vert pour les actions positives
        DANGER_COLOR = "#e74c3c"        # Rouge pour les actions d'arrÃªt
        BG_COLOR = "#1a1a2e"            # Fond sombre avec une teinte bleue
        CARD_COLOR = "#16213e"          # Couleur des cartes/panneaux
        TEXT_COLOR = "#fff"             # Texte blanc
        
        # Icônes pour l'interface (caractères Unicode)
        ICONS = {
            "search": "",
            "filter": "",
            "company": "",
            "location": "",
            "options": "",
            "pages": "",
            "email": "",
            "start": "",
            "stop": "",
            "help": "",
            "theme": "",
            "results": "",
            "web": "",
            "history": "",
            "clear": "",
            "apply": ""
        }
        
        # Configurer le thÃ¨me global
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_COLOR)
        
        # Container principal
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # En-tête Ã©lÃ©gant avec dÃ©gradÃ©
        header = ctk.CTkFrame(main_container, fg_color=CARD_COLOR, corner_radius=15)
        header.pack(fill="x", pady=(0, 20))
        
        # Logo stylisÃ© et titre
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.pack(pady=20)
        
        title = ctk.CTkLabel(
            logo_frame,
            text="LinkedIn Profile Scraper",
            font=("Segoe UI", 38, "bold"),
            text_color=PRIMARY_COLOR
        )
        title.pack()
        
        subtitle = ctk.CTkLabel(
            logo_frame,
            text="Trouvez des profils et emails professionnels en quelques clics",
            font=("Segoe UI", 16),
            text_color=TEXT_COLOR
        )
        subtitle.pack(pady=(5, 0))
        
        version = ctk.CTkLabel(
            logo_frame,
            text=f"v{APP_VERSION}",
            font=("Segoe UI", 14),
            text_color=PRIMARY_COLOR
        )
        version.pack(pady=(5, 0))
        
        # Conteneur à deux colonnes
        content = ctk.CTkFrame(main_container, fg_color="transparent")
        content.pack(fill="both", expand=True)
        
        # Configuration des colonnes
        content.grid_columnconfigure(0, weight=1)  # Colonne des contrÃ´les
        content.grid_columnconfigure(1, weight=2)  # Colonne des résultats
        
        # === COLONNE GAUCHE: CONTRÃ”LES ===
        controls = ctk.CTkFrame(content, fg_color=CARD_COLOR, corner_radius=15)
        controls.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        # Barre de recherche moderne
        search_frame = ctk.CTkFrame(controls, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        search_label = ctk.CTkLabel(
            search_frame,
            text=f"{ICONS['search']} Que recherchez-vous ?",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_COLOR
        )
        search_label.pack(anchor="w")
        
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Ex: RH France Orange",
            height=50,
            font=("Segoe UI", 16),
            border_width=0,
            corner_radius=10
        )
        search_entry.pack(fill="x", pady=(10, 5))
        self.create_tooltip(search_entry, TOOLTIPS["search"])
        
        # Section filtres
        filters_section = ctk.CTkFrame(controls, fg_color="transparent")
        filters_section.pack(fill="x", padx=20, pady=10)
        
        filters_label = ctk.CTkLabel(
            filters_section,
            text=f"{ICONS['filter']} Filtres",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_COLOR
        )
        filters_label.pack(anchor="w", pady=(0, 10))
        
        # Filtre entreprise
        enterprise_frame = ctk.CTkFrame(filters_section, fg_color="transparent")
        enterprise_frame.pack(fill="x", pady=5)
        
        enterprise_check = ctk.CTkSwitch(
            enterprise_frame,
            text=f"{ICONS['company']} Filtrer par entreprise",
            font=("Segoe UI", 16),
            variable=self.use_enterprise_filter,
            command=self.toggle_enterprise,
            progress_color=PRIMARY_COLOR,
            button_color=PRIMARY_COLOR
        )
        enterprise_check.pack(anchor="w")
        self.create_tooltip(enterprise_check, TOOLTIPS["enterprise_filter"])
        
        self.enterprise_entry = ctk.CTkEntry(
            enterprise_frame,
            textvariable=self.enterprise_var,
            placeholder_text="Nom de l'entreprise",
            state="disabled",
            font=("Segoe UI", 16),
            corner_radius=10,
            border_width=0,
            height=40
        )
        self.enterprise_entry.pack(fill="x", pady=(5, 0))
        
        # Filtre localisation
        location_frame = ctk.CTkFrame(filters_section, fg_color="transparent")
        location_frame.pack(fill="x", pady=10)
        
        location_check = ctk.CTkSwitch(
            location_frame,
            text=f"{ICONS['location']} Filtrer par localisation",
            font=("Segoe UI", 16),
            variable=self.use_location_filter,
            command=self.toggle_location,
            progress_color=PRIMARY_COLOR,
            button_color=PRIMARY_COLOR
        )
        location_check.pack(anchor="w")
        self.create_tooltip(location_check, TOOLTIPS["location_filter"])
        
        self.location_combo = ctk.CTkOptionMenu(
            location_frame,
            values=["France"] + [
                "Auvergne-RhÃ´ne-Alpes", "Bourgogne-Franche-ComtÃ©", "Bretagne",
                "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
                "ÃŽle-de-France", "Normandie", "Nouvelle-Aquitaine",
                "Occitanie", "Pays de la Loire", "Provence-Alpes-CÃ´te d'Azur"
            ],
            state="disabled",
            font=("Segoe UI", 16),
            dropdown_font=("Segoe UI", 16),
            button_color=CARD_COLOR,
            dropdown_fg_color=CARD_COLOR,
            corner_radius=10,
            height=40
        )
        self.location_combo.pack(fill="x", pady=(5, 0))
        
        # Options avancées
        options_section = ctk.CTkFrame(controls, fg_color="transparent")
        options_section.pack(fill="x", padx=20, pady=10)
        
        options_label = ctk.CTkLabel(
            options_section,
            text=f"{ICONS['options']} Options avancées",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_COLOR
        )
        options_label.pack(anchor="w", pady=(0, 10))
        
        # Pages slider
        pages_frame = ctk.CTkFrame(options_section, fg_color="transparent")
        pages_frame.pack(fill="x", pady=5)
        
        pages_label = ctk.CTkLabel(
            pages_frame,
            text=f"{ICONS['pages']} Nombre de pages à analyser",
            font=("Segoe UI", 16),
            text_color=TEXT_COLOR
        )
        pages_label.pack(anchor="w")
        
        slider_frame = ctk.CTkFrame(pages_frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(5, 0))
        
        self.pages_slider = ctk.CTkSlider(
            slider_frame,
            from_=1,
            to=20,
            number_of_steps=19,
            command=self.update_pages_label,
            width=200,
            progress_color=PRIMARY_COLOR,
            button_color=PRIMARY_COLOR,
            button_hover_color=PRIMARY_COLOR,
            height=20
        )
        self.pages_slider.pack(side="left", fill="x", expand=True)
        self.pages_slider.set(5)
        self.create_tooltip(self.pages_slider, TOOLTIPS["pages"])
        
        self.pages_label = ctk.CTkLabel(slider_frame, text="5 pages", font=("Segoe UI", 16), width=80)
        self.pages_label.pack(side="left", padx=(10, 0))
        
        # Vérification email
        email_frame = ctk.CTkFrame(options_section, fg_color="transparent")
        email_frame.pack(fill="x", pady=10)
        
        self.verify_emails_var = ctk.BooleanVar(value=True)
        verify_emails_check = ctk.CTkSwitch(
            email_frame,
            text=f"{ICONS['email']} Vérifier les emails (DNS + SMTP)",
            font=("Segoe UI", 16),
            variable=self.verify_emails_var,
            progress_color=PRIMARY_COLOR,
            button_color=PRIMARY_COLOR
        )
        verify_emails_check.pack(anchor="w")
        self.create_tooltip(verify_emails_check, TOOLTIPS["verify_emails"])
        
        # Boutons d'action
        actions_frame = ctk.CTkFrame(controls, fg_color="transparent")
        actions_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # Bouton Démarrer
        self.start_button = ctk.CTkButton(
            actions_frame,
            text=f"{ICONS['start']} DÉMARRER LA RECHERCHE",
            command=self.start_scraping,
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_COLOR,
            height=60,
            fg_color=SECONDARY_COLOR,
            hover_color="#27ae60",
            corner_radius=10
        )
        self.start_button.pack(fill="x", pady=(0, 10))
        self.create_tooltip(self.start_button, TOOLTIPS["start"])
        
        # Bouton Arrêter
        self.stop_button = ctk.CTkButton(
            actions_frame,
            text=f"{ICONS['stop']} ARRÃŠTER",
            command=self.stop_scraping,
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_COLOR,
            height=60,
            fg_color=DANGER_COLOR,
            hover_color="#c0392b",
            state="disabled",
            corner_radius=10
        )
        self.stop_button.pack(fill="x")
        self.create_tooltip(self.stop_button, TOOLTIPS["stop"])
        
        # Boutons d'aide, historique et thÃ¨me
        utility_frame = ctk.CTkFrame(controls, fg_color="transparent")
        utility_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # Bouton historique
        history_button = ctk.CTkButton(
            utility_frame,
            text=f"{ICONS['history']} Historique",
            command=self.toggle_history_panel,
            font=("Segoe UI", 16),
            text_color=TEXT_COLOR,
            fg_color=PRIMARY_COLOR,
            hover_color="#2980b9",
            corner_radius=10,
            height=40
        )
        history_button.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.create_tooltip(history_button, "Afficher l'historique des recherches")
        
        help_button = ctk.CTkButton(
            utility_frame,
            text=f"{ICONS['help']} Aide",
            command=self.show_help,
            font=("Segoe UI", 16),
            text_color=TEXT_COLOR,
            fg_color=PRIMARY_COLOR,
            hover_color="#2980b9",
            corner_radius=10,
            height=40
        )
        help_button.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        theme_button = ctk.CTkButton(
            utility_frame, 
            text=f"{ICONS['theme']} ThÃ¨me",
            command=self.toggle_theme,
            font=("Segoe UI", 16),
            text_color=TEXT_COLOR,
            fg_color=PRIMARY_COLOR,
            hover_color="#2980b9",
            corner_radius=10,
            height=40
        )
        theme_button.pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        # === COLONNE DROITE: RÃ‰SULTATS ===
        self.results_frame = ctk.CTkFrame(content, fg_color=CARD_COLOR, corner_radius=15)
        self.results_frame.grid(row=0, column=1, sticky="nsew")
        
        # En-tête des résultats
        results_header = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        results_header.pack(fill="x", padx=20, pady=(20, 10))
        
        results_title = ctk.CTkLabel(
            results_header,
            text=f"{ICONS['results']} Résultats",
            font=("Segoe UI", 24, "bold"),
            text_color=TEXT_COLOR
        )
        results_title.pack(side="left")
        
        # Zone de log stylisÃ©e
        log_container = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        log_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.log_text = ctk.CTkTextbox(
            log_container, 
            font=("Segoe UI", 15),
            corner_radius=10,
            border_width=0,
            fg_color="#10172a"
        )
        self.log_text.pack(fill="both", expand=True)
        
        # Barre de progression
        progress_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Progression : 0%",
            font=("Segoe UI", 16),
            text_color=TEXT_COLOR
        )
        self.progress_label.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=20,
            corner_radius=10,
            progress_color=PRIMARY_COLOR
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        
        # === PANNEAU D'HISTORIQUE (initialement cachÃ©) ===
        self.history_panel = ctk.CTkFrame(self.results_frame, fg_color="#10172a", corner_radius=10)
        self.history_items_frame = ctk.CTkFrame(self.history_panel, fg_color="transparent")
        self.history_items_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # En-tête de l'historique
        history_header = ctk.CTkFrame(self.history_panel, fg_color="transparent")
        history_header.pack(fill="x", padx=20, pady=(15, 5))
        
        history_title = ctk.CTkLabel(
            history_header,
            text=f"{ICONS['history']} Historique des recherches",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_COLOR
        )
        history_title.pack(side="left")
        
        # Bouton pour effacer l'historique
        clear_button = ctk.CTkButton(
            history_header,
            text=f"{ICONS['clear']} Effacer",
            command=self.clear_history,
            font=("Segoe UI", 14),
            fg_color=DANGER_COLOR,
            hover_color="#c0392b",
            corner_radius=8,
            width=100,
            height=30
        )
        clear_button.pack(side="right")
        
        # Container scrollable pour les éléments d'historique
        self.history_scroll = ctk.CTkScrollableFrame(self.history_items_frame, fg_color="transparent")
        self.history_scroll.pack(fill="both", expand=True, pady=10)
        
        # Pied de page
        footer_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        footer_frame.pack(fill="x", pady=(10, 0))
        
        footer_text = ctk.CTkLabel(
            footer_frame,
            text="2025 LinkedIn Profile Scraper Pro | Tous droits réservés",
            font=("Segoe UI", 14),
            text_color="#6c7a89"
        )
        footer_text.pack(side="left")
        
        website_button = ctk.CTkButton(
            footer_frame,
            text=f"{ICONS['web']} Site web",
            command=lambda: webbrowser.open("https://linkedinscraper.pro"),
            font=("Segoe UI", 14),
            fg_color="transparent",
            text_color=PRIMARY_COLOR,
            hover_color="#10172a",
            corner_radius=5,
            width=100,
            height=30
        )
        website_button.pack(side="right")

    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=text, justify="left",
                           background="#2d2d2d", fg="white",
                           relief="solid", borderwidth=1,
                           font=("Helvetica", 10))
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.after(3000, hide_tooltip)
        
        def hide_tooltip(event):
            if hasattr(widget, "tooltip"):
                widget.tooltip.destroy()
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def show_welcome_message(self):
        self.log(" Bienvenue sur LPS ! (LinkedIn Profile Scraper)")
        self.log(" Cet outil vous permet de :")
        self.log("   Rechercher des profils LinkedIn selon vos critéres")
        self.log("   Extraire les informations de contact")
        self.log("   Vérifier la validité des emails professionnels")
        self.log("\n Pour commencer :")
        self.log("1. Entrez vos mots-clés de recherche")
        self.log("2. Configurez les filtres si besoin")
        self.log("3. Cliquez sur 'Démarrer'")
        self.log("\n❓ Besoin d'aide ? Cliquez sur le bouton 'Aide'")
    
    def show_help(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("Aide - LinkedIn Profile Scraper Pro")
        help_window.geometry("600x700")
        
        help_text = ctk.CTkTextbox(help_window, width=550, height=650)
        help_text.pack(padx=20, pady=20)
        help_text.insert("1.0", HELP_TEXT)
        help_text.configure(state="disabled")
    
    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        new_mode = "light" if current_mode == "dark" else "dark"
        ctk.set_appearance_mode(new_mode)
    
    def update_progress(self, value):
        """Met à jour la progression directement (pour les appels depuis le thread principal)"""
        self.progress_bar.set(value)
        self.progress_label.configure(text=f"Progression : {int(value*100)}%")
    
    def toggle_enterprise(self):
        """Active/dÃ©sactive le champ entreprise avec animation."""
        if self.use_enterprise_filter.get():
            # Animation d'activation
            self.enterprise_entry.configure(state="normal")
            self.animate_widget_appearance(self.enterprise_entry)
        else:
            # Animation de dÃ©sactivation
            self.animate_widget_disappearance(self.enterprise_entry, lambda: self.enterprise_entry.configure(state="disabled"))
    
    def toggle_location(self):
        """Active/dÃ©sactive la sÃ©lection de lieu avec animation."""
        if self.use_location_filter.get():
            # Animation d'activation
            self.location_combo.configure(state="normal")
            self.animate_widget_appearance(self.location_combo)
        else:
            # Animation de dÃ©sactivation
            self.animate_widget_disappearance(self.location_combo, lambda: self.location_combo.configure(state="disabled"))
            
    def animate_widget_appearance(self, widget, steps=10, duration=200):
        """Anime l'apparition d'un widget."""
        # Sauvegarde de la couleur d'origine
        original_fg = widget.cget("fg_color") if hasattr(widget, "cget") else None
        
        def _animate_step(step, total_steps):
            if step <= total_steps:
                # Calculer l'opacitÃ© actuelle (de 0.3 à 1.0)
                opacity = 0.3 + 0.7 * (step / total_steps)
                
                # Appliquer l'opacitÃ©
                if hasattr(widget, "configure") and hasattr(widget, "cget"):
                    if widget.cget("fg_color") != "transparent":
                        try:
                            current_color = widget.cget("fg_color")
                            # Si c'est un tuple (mode, couleur), prendre la couleur
                            if isinstance(current_color, tuple):
                                current_color = current_color[1]  # Prendre la couleur du mode dark
                            
                            # Ajuster l'opacitÃ©
                            r, g, b = self.hex_to_rgb(current_color)
                            widget.configure(fg_color=f"#{int(r*opacity):02x}{int(g*opacity):02x}{int(b*opacity):02x}")
                        except:
                            pass  # Ignorer les erreurs de couleur
                
                # Planifier la prochaine Ã©tape
                self.after(int(duration/total_steps), lambda: _animate_step(step+1, total_steps))
            else:
                # Restaurer la couleur d'origine à la fin
                if original_fg and hasattr(widget, "configure"):
                    widget.configure(fg_color=original_fg)
                    
        # Démarrer l'animation
        _animate_step(1, steps)
    
    def animate_widget_disappearance(self, widget, callback=None, steps=5, duration=100):
        """Anime la disparition d'un widget puis exÃ©cute le callback."""
        # Sauvegarde de la couleur d'origine
        original_fg = widget.cget("fg_color") if hasattr(widget, "cget") else None
        
        def _animate_step(step, total_steps):
            if step <= total_steps:
                # Calculer l'opacitÃ© actuelle (de 1.0 à 0.3)
                opacity = 1.0 - 0.7 * (step / total_steps)
                
                # Appliquer l'opacitÃ©
                if hasattr(widget, "configure") and hasattr(widget, "cget"):
                    if widget.cget("fg_color") != "transparent":
                        try:
                            current_color = widget.cget("fg_color")
                            # Si c'est un tuple (mode, couleur), prendre la couleur
                            if isinstance(current_color, tuple):
                                current_color = current_color[1]  # Prendre la couleur du mode dark
                            
                            # Ajuster l'opacitÃ©
                            r, g, b = self.hex_to_rgb(current_color)
                            widget.configure(fg_color=f"#{int(r*opacity):02x}{int(g*opacity):02x}{int(b*opacity):02x}")
                        except:
                            pass  # Ignorer les erreurs de couleur
                
                # Planifier la prochaine Ã©tape
                self.after(int(duration/total_steps), lambda: _animate_step(step+1, total_steps))
            else:
                # ExÃ©cuter le callback à la fin
                if callback:
                    callback()
                # Restaurer la couleur d'origine
                if original_fg and hasattr(widget, "configure"):
                    widget.configure(fg_color=original_fg)
                    
        # Démarrer l'animation
        _animate_step(1, steps)
    
    def update_pages_label(self, value):
        pages = int(value)
        self.pages_label.configure(text=f"{pages} pages")
        self.pages_var.set(str(pages))
    
    def log(self, message):
        """Ajoute un message au log directement (pour les appels depuis le thread principal)"""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
    
    def hex_to_rgb(self, hex_color):
        """Convertit une couleur hexadÃ©cimale en RGB."""
        # S'assurer que la couleur commence par #
        if not hex_color.startswith('#'):
            hex_color = '#' + hex_color
        
        # Enlever le # et convertir en RGB
        h = hex_color.lstrip('#')
        
        # GÃ©rer les formats courts (#fff) et longs (#ffffff)
        if len(h) == 3:
            return tuple(int(h[i] + h[i], 16) for i in range(3))
        elif len(h) == 6:
            return tuple(int(h[i:i+2], 16) for i in range(0, 6, 2))
        else:
            return (0, 0, 0)  # Noir par défaut

    def animate_button_click(self, button):
        """Anime un clic de bouton avec effet de pression."""
        original_color = button.cget("fg_color")
        hover_color = button.cget("hover_color")
        
        # Effet de pression
        button.configure(fg_color=hover_color)
        
        # Retour à la couleur normale aprÃ¨s un court dÃ©lai
        self.after(100, lambda: button.configure(fg_color=original_color))

    def toggle_history_panel(self):
        """Affiche ou cache le panneau d'historique."""
        if self.history_visible:
            self.history_panel.pack_forget()
            self.history_visible = False
        else:
            self.history_panel.pack(fill="both", expand=True)
            self.history_visible = True
            self.update_history_display()

    def update_history_display(self):
        """Met à jour l'affichage de l'historique."""
        # Effacer tous les widgets existants
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
        
        # Couleurs pour l'interface
        PRIMARY_COLOR = "#3498db"
        SECONDARY_COLOR = "#2ecc71"
        BG_COLOR = "#1a1a2e"
        HOVER_COLOR = "#1e2f4d"
        TEXT_COLOR = "#fff"
        
        # Icônes
        ICONS = {
            "search": "",
            "time": "",
            "results": "",
            "file": "",
            "use": ""
        }
        
        # RÃ©cupÃ©rer les éléments d'historique
        history_items = self.search_history.get_items()
        
        if not history_items:
            # Afficher un message si l'historique est vide
            empty_label = ctk.CTkLabel(
                self.history_scroll,
                text="Aucune recherche dans l'historique",
                font=("Segoe UI", 16),
                text_color="#6c7a89"
            )
            empty_label.pack(pady=20)
            return
        
        # Créer un widget pour chaque Ã©lÃ©ment d'historique
        for item in history_items:
            # Conteneur pour l'Ã©lÃ©ment
            item_frame = ctk.CTkFrame(self.history_scroll, fg_color=HOVER_COLOR, corner_radius=10)
            item_frame.pack(fill="x", pady=5, padx=5)
            
            # Configuration des lignes de l'Ã©lÃ©ment
            inner_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            inner_frame.pack(fill="x", padx=10, pady=10)
            
            # Ligne 1: RequÃªte et date
            line1 = ctk.CTkFrame(inner_frame, fg_color="transparent")
            line1.pack(fill="x", pady=(0, 5))
            
            # RequÃªte
            query_label = ctk.CTkLabel(
                line1,
                text=f"{ICONS['search']} {item.query}",
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT_COLOR
            )
            query_label.pack(side="left")
            
            # Date
            date_label = ctk.CTkLabel(
                line1,
                text=f"{ICONS['time']} {item.timestamp}",
                font=("Segoe UI", 14),
                text_color="#6c7a89"
            )
            date_label.pack(side="right")
            
            
            line2 = ctk.CTkFrame(inner_frame, fg_color="transparent")
            line2.pack(fill="x", pady=(0, 5))
            
            # Filtres appliquÃ©s
            filters_text = []
            if item.filters.entreprise:
                filters_text.append(f"Entreprise: {item.filters.entreprise}")
            if item.filters.localisation:
                filters_text.append(f"Lieu: {item.filters.localisation}")
                
            filters_str = " | ".join(filters_text) if filters_text else "Aucun filtre"
            filters_label = ctk.CTkLabel(
                line2,
                text=f"Filtres: {filters_str}",
                font=("Segoe UI", 14),
                text_color="#6c7a89"
            )
            filters_label.pack(side="left")
            
            # Nombre de résultats
            results_label = ctk.CTkLabel(
                line2,
                text=f"{ICONS['results']} {item.results_count} résultats",
                font=("Segoe UI", 14),
                text_color=TEXT_COLOR
            )
            results_label.pack(side="right")
            
            # Ligne 3: Boutons d'action
            line3 = ctk.CTkFrame(inner_frame, fg_color="transparent")
            line3.pack(fill="x", pady=(5, 0))
            
            # Bouton pour relancer la recherche
            use_button = ctk.CTkButton(
                line3,
                text=f"{ICONS['use']} Relancer",
                command=lambda q=item.query, f=item.filters: self.reuse_search(q, f),
                font=("Segoe UI", 14),
                fg_color=PRIMARY_COLOR,
                hover_color="#2980b9",
                corner_radius=8,
                height=30
            )
            use_button.pack(side="left")
            
            # Bouton pour ouvrir le fichier de résultats
            if item.file_path and os.path.exists(item.file_path):
                open_button = ctk.CTkButton(
                    line3,
                    text=f"{ICONS['file']} Voir résultats",
                    command=lambda path=item.file_path: os.startfile(path),
                    font=("Segoe UI", 14),
                    fg_color=SECONDARY_COLOR,
                    hover_color="#27ae60",
                    corner_radius=8,
                    height=30
                )
                open_button.pack(side="right")
    
    def reuse_search(self, query, filters):
        """Relance une recherche à partir de l'historique."""
        # Remplir le formulaire avec les paramètres de la recherche
        self.search_var.set(query)
        
        if filters.entreprise:
            self.use_enterprise_filter.set(True)
            self.enterprise_var.set(filters.entreprise)
            self.enterprise_entry.configure(state="normal")
        else:
            self.use_enterprise_filter.set(False)
            self.enterprise_var.set("")
            self.enterprise_entry.configure(state="disabled")
            
        if filters.localisation:
            self.use_location_filter.set(True)
            self.location_combo.set(filters.localisation)
            self.location_combo.configure(state="normal")
        else:
            self.use_location_filter.set(False)
            self.location_combo.configure(state="disabled")
        
        # Cacher le panneau d'historique
        self.history_panel.pack_forget()
        self.history_visible = False
        
        # Mettre en Ã©vidence le bouton de dÃ©marrage
        self.animate_button_click(self.start_button)
    
    def clear_history(self):
        """Efface l'historique."""
        self.search_history.clear_history()
        self.update_history_display()

if __name__ == "__main__":
    app = LinkedInScraperGUI()
    app.mainloop()


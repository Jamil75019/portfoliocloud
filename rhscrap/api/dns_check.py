import dns.resolver
import socket
import smtplib
import re
from typing import Dict, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
import time
import random

class EmailVerifier:
    def __init__(self):
        self.smtp_cache = {}  # Cache pour les résultats SMTP
        self.dns_cache = {}   # Cache pour les résultats DNS
        self.haveibeenpwned_cache = {}  # Cache pour les résultats de fuite de données
        
        # Liste de mots interdits et suspects
        self.forbidden_words = {
            # Mots inappropriés
            'caca', 'pipi', 'zizi', 'penis', 'fuck', 'shit', 'pute', 'bite', 'sex',
            'porn', 'xxx', 'dick', 'ass', 'fake', 'hack', 'crack', 'warez', 'spam',
            'scam', 'phish', 'troll', 'noob', 'lol', 'mdr', 'ptdr', 'kikoo',
            # Noms génériques
            'test', 'demo', 'example', 'sample', 'admin', 'root', 'user', 'guest',
            'info', 'contact', 'mail', 'email', 'webmaster', 'postmaster',
            # Nombres et caractères suspects en série
            '123', '1234', '12345', '111', '000', '666', '777',
            # Mots liés au piratage
            'hack', 'crack', 'exploit', 'ddos', 'spam', 'phish'
        }
        
        # Patterns suspects
        self.suspicious_patterns = [
            r'\d{4,}',  # 4 chiffres ou plus d'affilée
            r'(.)\1{2,}',  # Même caractère répété 3 fois ou plus
            r'[^a-zA-Z]{3,}',  # 3 caractères non-alphabétiques d'affilée
        ]
        
    def verify_email_format(self, email: str) -> bool:
        """Vérifie si le format de l'email est valide."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def verify_domain_dns(self, domain: str) -> Tuple[bool, str]:
        """Vérifie les enregistrements MX et autres du domaine."""
        if domain in self.dns_cache:
            return self.dns_cache[domain]
            
        try:
            # Vérification MX
            mx_valid = False
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                if mx_records:
                    mx_valid = True
            except:
                pass
            
            # Vérification A
            a_valid = False
            try:
                a_records = dns.resolver.resolve(domain, 'A')
                if a_records:
                    a_valid = True
            except:
                pass
            
            # Vérification SPF
            spf_valid = False
            try:
                txt_records = dns.resolver.resolve(domain, 'TXT')
                for record in txt_records:
                    if 'v=spf1' in str(record):
                        spf_valid = True
                        break
            except:
                pass
            
            # Vérification DMARC
            dmarc_valid = False
            try:
                dmarc_records = dns.resolver.resolve(f'_dmarc.{domain}', 'TXT')
                for record in dmarc_records:
                    if 'v=DMARC1' in str(record):
                        dmarc_valid = True
                        break
            except:
                pass
            
            # Calcul du score DNS
            score = 0
            details = []
            
            if mx_valid:
                score += 40
                details.append("MX: ✅")
            else:
                details.append("MX: ❌")
                
            if a_valid:
                score += 20
                details.append("A: ✅")
            else:
                details.append("A: ❌")
                
            if spf_valid:
                score += 20
                details.append("SPF: ✅")
            else:
                details.append("SPF: ❌")
                
            if dmarc_valid:
                score += 20
                details.append("DMARC: ✅")
            else:
                details.append("DMARC: ❌")
            
            is_valid = score >= 60
            message = f"Score DNS: {score}% ({', '.join(details)})"
            
            self.dns_cache[domain] = (is_valid, message)
            return is_valid, message
            
        except Exception as e:
            self.dns_cache[domain] = (False, f"Erreur DNS: {str(e)}")
            return False, f"Erreur DNS: {str(e)}"
    
    def verify_name_quality(self, name_part: str) -> Tuple[bool, float, str]:
        """Vérifie la qualité du nom dans l'email."""
        name_lower = name_part.lower()
        
        # Vérification des mots interdits
        for word in self.forbidden_words:
            if word in name_lower:
                return False, 0.0, f"Mot interdit détecté : {word}"
        
        # Vérification des patterns suspects
        for pattern in self.suspicious_patterns:
            if re.search(pattern, name_lower):
                return False, 0.1, "Pattern suspect détecté"
        
        # Analyse de la structure du nom
        parts = re.split(r'[._-]', name_lower)
        
        # Vérification de la longueur des parties
        for part in parts:
            if len(part) < 2:
                return False, 0.2, "Parties du nom trop courtes"
            if len(part) > 20:
                return False, 0.3, "Parties du nom trop longues"
        
        # Vérification du ratio consonnes/voyelles
        voyelles = sum(1 for c in name_lower if c in 'aeiouy')
        consonnes = sum(1 for c in name_lower if c in 'bcdfghjklmnpqrstvwxz')
        
        if voyelles == 0 or consonnes == 0:
            return False, 0.2, "Ratio consonnes/voyelles invalide"
        
        ratio = voyelles / (voyelles + consonnes)
        if ratio < 0.2 or ratio > 0.8:
            return False, 0.4, "Ratio consonnes/voyelles suspect"
        
        # Vérification des caractères spéciaux
        special_chars = sum(1 for c in name_lower if not c.isalnum() and c not in '._-')
        if special_chars > 0:
            return False, 0.3, "Caractères spéciaux non autorisés"
        
        # Score basé sur la qualité du nom
        score = 1.0
        
        # Pénalité pour les noms courts ou longs
        total_length = len(name_lower)
        if total_length < 5:
            score *= 0.7
        elif total_length > 30:
            score *= 0.8
        
        # Bonus pour les formats standards
        if '.' in name_lower and len(parts) == 2:
            if all(3 <= len(part) <= 15 for part in parts):
                score *= 1.2
        
        return True, score, "Nom valide"
    
    def verify_common_patterns(self, email: str, company: str) -> Tuple[bool, float, str]:
        """Vérifie si l'email suit les patterns communs d'entreprise."""
        email_lower = email.lower()
        name_part = email_lower.split('@')[0]
        
        # Vérification de la qualité du nom
        name_valid, name_score, name_message = self.verify_name_quality(name_part)
        if not name_valid:
            return False, name_score, name_message
        
        # Patterns communs d'entreprise avec leurs scores
        patterns = {
            'prenom.nom': 0.9,
            'p.nom': 0.8,
            'prenom_nom': 0.8,
            'nom.prenom': 0.7,
            'prenomnom': 0.6
        }
        
        # Détection du pattern
        parts = re.split(r'[._-]', name_part)
        
        if len(parts) == 2:
            if '.' in name_part:
                if len(parts[0]) == 1:
                    return True, patterns['p.nom'], "Format p.nom détecté"
                return True, patterns['prenom.nom'], "Format prenom.nom détecté"
            elif '_' in name_part:
                return True, patterns['prenom_nom'], "Format prenom_nom détecté"
        elif len(parts) == 1:
            return True, patterns['prenomnom'], "Format prenomnom détecté"
        
        return True, 0.5, "Format acceptable"
    
    def verify_disposable_email(self, domain: str) -> bool:
        """Vérifie si le domaine est un service d'email temporaire."""
        disposable_domains = {
            'tempmail.com', 'throwawaymail.com', 'mailinator.com', 
            'guerrillamail.com', 'yopmail.com', '10minutemail.com'
        }
        return domain.lower() in disposable_domains
    
    async def verify_email_complete(self, email: str) -> Dict:
        """Vérifie un email avec toutes les méthodes disponibles."""
        try:
            domain = email.split('@')[1]
            company = domain.split('.')[0]
            
            # Vérification du format
            format_valid = self.verify_email_format(email)
            if not format_valid:
                return {
                    "email": email,
                    "format_valid": False,
                    "dns_valid": False,
                    "pattern_score": 0,
                    "score": 0,
                    "details": "Format d'email invalide"
                }
            
            # Vérification si email temporaire
            if self.verify_disposable_email(domain):
                return {
                    "email": email,
                    "format_valid": True,
                    "dns_valid": False,
                    "pattern_score": 0,
                    "score": 0,
                    "details": "Service d'email temporaire détecté"
                }
            
            # Vérification DNS
            dns_valid, dns_message = self.verify_domain_dns(domain)
            
            # Vérification du pattern
            pattern_valid, pattern_score, pattern_message = self.verify_common_patterns(email, company)
            
            # Calcul du score final
            score = 0
            if format_valid: score += 20
            if dns_valid: score += 40
            score += int(pattern_score * 40)  # Max 40 points pour le pattern
            
            details = []
            if format_valid:
                details.append("Format: ✅")
            else:
                details.append("Format: ❌")
            
            details.append(f"DNS: {dns_message}")
            details.append(f"Pattern: {pattern_message} ({int(pattern_score*100)}%)")
            
            return {
                "email": email,
                "format_valid": format_valid,
                "dns_valid": dns_valid,
                "pattern_score": pattern_score,
                "score": score,
                "details": " | ".join(details)
            }
            
        except Exception as e:
            return {
                "email": email,
                "format_valid": False,
                "dns_valid": False,
                "pattern_score": 0,
                "score": 0,
                "details": f"Erreur: {str(e)}"
            }
    
    async def verify_emails_batch(self, emails: list) -> list:
        """Vérifie plusieurs emails en parallèle."""
        tasks = [self.verify_email_complete(email) for email in emails]
        results = await asyncio.gather(*tasks)
        return results

def get_mx_records(domain):
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8']  # DNS public Google
        mx_records = resolver.resolve(domain, 'MX')
        print(f"\n✅ Serveurs mail trouvés pour {domain} :")
        for mx in mx_records:
            print(f" • {mx.exchange}")
    except dns.resolver.NXDOMAIN:
        print(f"❌ Domaine {domain} introuvable.")
    except dns.resolver.NoAnswer:
        print(f"❌ Aucun enregistrement MX pour {domain}.")
    except dns.resolver.Timeout:
        print(f"❌ Timeout DNS pour {domain}.")
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

def main():
    nom_entreprise = input("🔍 Nom de l'entreprise (ex: capgemini) : ").strip().lower()
    extensions = ["com", "fr", "net", "org"]

    for ext in extensions:
        domaine = f"{nom_entreprise}.{ext}"
        print(f"\n🔎 Test de {domaine} ...")
        get_mx_records(domaine)

if __name__ == "__main__":
    main()

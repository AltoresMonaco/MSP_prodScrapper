#!/usr/bin/env python3
"""
Configuration pour l'API Scraper
"""

import os
import secrets
from pathlib import Path

def generate_secure_token():
    """Génère un token sécurisé"""
    return secrets.token_urlsafe(32)

def setup_api_token():
    """Configure le token API"""
    env_file = Path(".env")
    
    # Lire le fichier .env existant ou créer un nouveau
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Ajouter/mettre à jour le token API s'il n'existe pas
    if 'SCRAPER_API_TOKEN' not in env_vars or env_vars['SCRAPER_API_TOKEN'] == 'your-secure-token-here-change-me':
        new_token = generate_secure_token()
        env_vars['SCRAPER_API_TOKEN'] = new_token
        print(f"🔑 Nouveau token généré : {new_token}")
    else:
        print(f"🔑 Token existant : {env_vars['SCRAPER_API_TOKEN']}")
    
    # Sauvegarder le fichier .env
    with open(env_file, 'w') as f:
        f.write("# Configuration Mon Service Public Scraper\n")
        f.write(f"SCRAPER_API_TOKEN={env_vars.get('SCRAPER_API_TOKEN', '')}\n")
        f.write("\n# Configuration OpenAI\n")
        f.write(f"OPENAI_API_KEY={env_vars.get('OPENAI_API_KEY', '')}\n")
        f.write("\n# Configuration Pinecone\n")
        f.write(f"PINECONE_API_KEY={env_vars.get('PINECONE_API_KEY', '')}\n")
        f.write(f"PINECONE_INDEX_NAME={env_vars.get('PINECONE_INDEX_NAME', 'msp')}\n")
    
    return env_vars['SCRAPER_API_TOKEN']

if __name__ == "__main__":
    print("🔧 Configuration de l'API Scraper")
    token = setup_api_token()
    print("✅ Configuration terminée !")
    print(f"📝 Fichier .env mis à jour avec le token : {token}") 
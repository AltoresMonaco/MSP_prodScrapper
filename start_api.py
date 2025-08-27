#!/usr/bin/env python3
"""
Script de démarrage pour l'API Scraper
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def start_api():
    """Démarre l'API avec configuration"""
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Vérifier que le token API est configuré
    api_token = os.getenv("SCRAPER_API_TOKEN")
    if not api_token or api_token == "your-secure-token-here-change-me":
        print("❌ Token API non configuré !")
        print("🔧 Exécutez d'abord : python3 api_config.py")
        sys.exit(1)
    
    # La vérification des autres clés est retirée d'ici.
    # Elle se fera au moment de l'utilisation pour plus de flexibilité.
    
    print("🚀 Démarrage de l'API Mon Service Public Scraper")
    print("="*60)
    print(f"🔑 Token API configuré : {api_token[:16]}...")
    print("📚 Documentation automatique : http://localhost:8000/docs")
    print("⚡ Interface Redoc : http://localhost:8000/redoc")
    print("📊 Health check : http://localhost:8000/")
    print("="*60)
    print("\n💡 Exemples d'utilisation :")
    print("   Scraping complet : POST /scrape/quick")
    print("   Statut des jobs : GET /jobs")
    print("   Job spécifique : GET /jobs/{job_id}")
    print("\n🛑 Arrêt : Ctrl+C")
    print("=" * 60)
    
    # Démarrer l'API
    import uvicorn
    from api_scraper import app
    
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            reload=False,  # Désactiver le reload en production
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 API arrêtée par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage : {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_api() 
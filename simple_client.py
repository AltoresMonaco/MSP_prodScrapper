#!/usr/bin/env python3
"""
Client Simple pour l'API Scraper
Vos 3 cas d'usage principaux simplifiés
"""

import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

class SimpleScraperClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token or os.getenv("SCRAPER_API_TOKEN")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        if not self.token:
            print("❌ Token API requis ! Configurez SCRAPER_API_TOKEN dans .env")
            raise ValueError("Token manquant")
    
    def scrape_everything(self, workers=8):
        """
        CAS 1: Lance le scraping + embedding COMPLET 
        (tous les sitemaps automatiquement)
        """
        print("🚀 Lancement scraping + embedding COMPLET...")
        
        response = requests.post(
            f"{self.base_url}/scrape/full",
            headers=self.headers,
            json={"workers": workers}
        )
        
        if response.status_code == 200:
            job = response.json()
            print(f"✅ Job créé : {job['job_id']}")
            return job['job_id']
        else:
            print(f"❌ Erreur : {response.text}")
            return None
    
    def embedding_only(self, output_folder="output"):
        """
        CAS 2: Lance SEULEMENT l'embedding 
        (suppose que les fichiers existent déjà)
        """
        print("🔢 Lancement embedding seul...")
        
        response = requests.post(
            f"{self.base_url}/embedding/run",
            headers=self.headers,
            json={"output_folder": output_folder}
        )
        
        if response.status_code == 200:
            job = response.json()
            print(f"✅ Job embedding créé : {job['job_id']}")
            return job['job_id']
        else:
            print(f"❌ Erreur : {response.text}")
            return None
    
    def check_status(self, job_id):
        """
        CAS 3: Vérifie l'état COMPLET d'un job
        Retourne un dict avec toutes les infos essentielles
        """
        response = requests.get(
            f"{self.base_url}/status/simple/{job_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erreur lors de la vérification : {response.text}")
            return None
    
    def wait_for_completion(self, job_id, check_interval=10):
        """
        Attend qu'un job se termine et affiche le progress
        """
        print(f"⏳ Attente de completion du job {job_id}...")
        print("=" * 60)
        
        start_time = time.time()
        
        while True:
            status = self.check_status(job_id)
            
            if not status:
                break
            
            # Calculer temps écoulé
            elapsed = time.time() - start_time
            elapsed_str = f"{int(elapsed//60)}:{int(elapsed%60):02d}"
            
            # Afficher progress
            phase = status.get('current_phase', 'unknown')
            progress = status.get('progress_text', '')
            
            print(f"⏱️  {elapsed_str} | {status['status'].upper():10} | {phase:12} | {progress}")
            
            # Vérifier si terminé
            if status['is_completed']:
                print("\n🎉 JOB TERMINÉ AVEC SUCCÈS !")
                self._print_final_stats(status)
                return True
                
            elif status['is_failed']:
                print(f"\n❌ JOB ÉCHOUÉ !")
                print(f"   Erreur : {status.get('error', 'Inconnue')}")
                return False
            
            time.sleep(check_interval)
    
    def _print_final_stats(self, status):
        """Affiche les statistiques finales"""
        print("📊 RÉSULTATS FINAUX :")
        print("-" * 40)
        
        if 'urls_scraped' in status:
            print(f"📄 URLs scrapées      : {status['urls_scraped']:,}")
        if 'files_created' in status:
            print(f"📁 Fichiers créés     : {status['files_created']:,}")
        if 'vectors_created' in status:
            print(f"🔢 Vecteurs créés     : {status['vectors_created']:,}")
        if 'annuaire_services' in status:
            print(f"🏢 Services annuaire  : {status['annuaire_services']}")
        if 'total_time' in status:
            print(f"⏱️  Temps total       : {status['total_time']}")

# Fonctions pratiques pour utilisation directe
def run_full_scraping(workers=8):
    """Lance un scraping complet et attend la fin"""
    client = SimpleScraperClient()
    job_id = client.scrape_everything(workers)
    
    if job_id:
        return client.wait_for_completion(job_id)
    return False

def run_embedding_only(output_folder="output"):
    """Lance seulement l'embedding et attend la fin"""
    client = SimpleScraperClient()
    job_id = client.embedding_only(output_folder)
    
    if job_id:
        return client.wait_for_completion(job_id)
    return False

def check_job_status(job_id):
    """Vérifie rapidement le statut d'un job"""
    client = SimpleScraperClient()
    return client.check_status(job_id)

# Script de démonstration
if __name__ == "__main__":
    print("🎯 CLIENT SIMPLE API SCRAPER")
    print("=" * 40)
    
    client = SimpleScraperClient()
    
    print("\n1. Test de connexion...")
    try:
        # Test health check
        response = requests.get(f"{client.base_url}/", headers=client.headers)
        if response.status_code == 200:
            print("✅ API accessible")
        else:
            print("❌ API non accessible")
            exit(1)
    except:
        print("❌ Impossible de contacter l'API")
        exit(1)
    
    print("\n2. Menu des actions :")
    print("   A. Scraping + Embedding complet")
    print("   B. Embedding seul") 
    print("   C. Vérifier un job existant")
    
    choice = input("\nVotre choix (A/B/C) : ").upper()
    
    if choice == "A":
        print("\n🚀 LANCEMENT PROCESSUS COMPLET")
        run_full_scraping(workers=8)
        
    elif choice == "B":
        print("\n🔢 LANCEMENT EMBEDDING SEUL")
        run_embedding_only()
        
    elif choice == "C":
        job_id = input("ID du job à vérifier : ")
        if job_id:
            status = check_job_status(job_id)
            if status:
                print(f"\n📊 Status : {status['status']}")
                print(f"📈 Phase : {status['current_phase']}")
                print(f"📝 Progress : {status['progress_text']}")
                
                if status['is_completed']:
                    client._print_final_stats(status)
    
    print("\n✅ Terminé !") 
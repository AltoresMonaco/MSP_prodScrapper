#run.py
import argparse
from upsert import run_upsert
from embedding_pipeline import run_embedding
import os
import time

def run_full_process(sitemaps, output_folder, thematique, workers, skip_scraping, skip_embedding):
    start_time = time.time()
    
    if not skip_scraping:
        print("[INFO] Début du scraping...")
        run_upsert(sitemaps, output_folder, workers=workers)
        print("[INFO] Scraping terminé.")
    else:
        print("[INFO] Scraping ignoré (--skip-scraping activé).")
    
    if not skip_embedding:
        print("[INFO] Début de l'embedding et vectorisation...")
        run_embedding(output_folder, thematique)
        print("[INFO] Embedding terminé.")
    else:
        print("[INFO] Embedding ignoré (--skip-embedding activé).")
    
    # Afficher un résumé
    elapsed_time = time.time() - start_time
    print("\n" + "="*50)
    print(f"RÉSUMÉ DE L'EXÉCUTION (durée: {elapsed_time:.2f} secondes)")
    print("="*50)
    
    # Compter les fichiers générés
    if os.path.exists(output_folder):
        file_count = sum([len(files) for _, _, files in os.walk(output_folder)])
        dir_count = sum([len(dirs) for _, dirs, _ in os.walk(output_folder)]) - 1  # -1 pour ne pas compter le dossier racine
        print(f"Dossiers créés: {dir_count}")
        print(f"Fichiers générés: {file_count}")
    
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline complet de scraping et d'embedding.")
    parser.add_argument("--sitemaps", "-s", nargs="+", required=True,
                        help="Liste de liens ou chemins vers des sitemaps XML.")
    parser.add_argument("--output", "-o", required=True,
                        help="Dossier de base pour sauvegarder les pages scrappées.")
    parser.add_argument("--thematique", "-t", default="default",
                        help="Nom de la thématique à associer aux URL fixes (namespace 'general').")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="Nombre de workers pour le scraping parallèle.")
    parser.add_argument("--skip-scraping", action="store_true",
                        help="Ignorer la phase de scraping.")
    parser.add_argument("--skip-embedding", action="store_true",
                        help="Ignorer la phase d'embedding.")
    args = parser.parse_args()

    run_full_process(
        sitemaps=args.sitemaps,
        output_folder=args.output,
        thematique=args.thematique,
        workers=args.workers,
        skip_scraping=args.skip_scraping,
        skip_embedding=args.skip_embedding
    )

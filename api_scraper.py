#!/usr/bin/env python3
"""
API sécurisée pour déclencher le scraper avec bearer token
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import time
import asyncio
import threading
from datetime import datetime
import json
from pathlib import Path

# Imports du scraper
from run import run_full_process

# Configuration
API_TOKEN = os.getenv("SCRAPER_API_TOKEN", "your-secure-token-here-change-me")
JOBS_DIR = Path("api_jobs")
JOBS_DIR.mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(
    title="Mon Service Public Scraper API",
    description="API sécurisée pour déclencher le scraping et embedding",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# Models
class JobStats(BaseModel):
    urls_total: int = 0
    urls_processed: int = 0
    urls_failed: int = 0
    annuaire_services: int = 0
    vectors_created: int = 0
    directories_created: int = 0
    files_created: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    total_duration_seconds: Optional[float] = None
    total_duration_formatted: Optional[str] = None
    current_phase: str = "pending"

class JobSummary(BaseModel):
    urls_scraped: int = 0
    urls_failed: int = 0
    files_created: int = 0
    annuaire_services: int = 0
    vectors_created: int = 0
    total_time: str = "0s"

class ScrapingRequest(BaseModel):
    sitemaps: List[str]
    output_folder: str = "output"
    thematique: str = "monservicepublic"
    workers: int = 8
    skip_scraping: bool = False
    skip_embedding: bool = False

class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    parameters: dict
    stats: Optional[JobStats] = None
    summary: Optional[JobSummary] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

# Global jobs storage
jobs = {}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Vérifie le bearer token"""
    if credentials.credentials != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

def save_job_status(job_id: str, job_data: dict):
    """Sauvegarde le statut d'un job"""
    job_file = JOBS_DIR / f"{job_id}.json"
    with open(job_file, 'w') as f:
        json.dump(job_data, f, indent=2)

def load_job_status(job_id: str) -> Optional[dict]:
    """Charge le statut d'un job"""
    job_file = JOBS_DIR / f"{job_id}.json"
    if job_file.exists():
        with open(job_file, 'r') as f:
            return json.load(f)
    return None

def run_scraping_job(job_id: str, request: ScrapingRequest):
    """Execute le job de scraping en arrière-plan avec suivi détaillé"""
    start_time = time.time()
    
    try:
        # Mettre à jour le statut initial
        job_data = jobs[job_id]
        job_data["status"] = "running"
        job_data["started_at"] = datetime.now().isoformat()
        job_data["progress"] = "Initialisation du scraping..."
        job_data["stats"] = {
            "urls_total": 0,
            "urls_processed": 0,
            "urls_failed": 0,
            "annuaire_services": 0,
            "vectors_created": 0,
            "directories_created": 0,
            "files_created": 0,
            "start_time": start_time,
            "current_phase": "initialization"
        }
        jobs[job_id] = job_data
        save_job_status(job_id, job_data)
        
        # Créer un wrapper pour capturer les logs et métriques
        import sys
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        # Buffers pour capturer les outputs
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        # Phase 1: Scraping
        if not request.skip_scraping:
            job_data["stats"]["current_phase"] = "scraping"
            job_data["progress"] = "Phase 1/2: Démarrage du scraping..."
            jobs[job_id] = job_data
            save_job_status(job_id, job_data)
            
            # Hook dans le processus de scraping pour suivre le progrès
            import upsert
            original_process_single_url = upsert.process_single_url
            
            def tracked_process_single_url(url, output_folder, silent=False):
                try:
                    result = original_process_single_url(url, output_folder, silent)
                    job_data["stats"]["urls_processed"] += 1
                    
                    # Mettre à jour le progrès tous les 10 URLs
                    if job_data["stats"]["urls_processed"] % 10 == 0:
                        total = job_data["stats"]["urls_total"]
                        processed = job_data["stats"]["urls_processed"]
                        progress_pct = (processed / total * 100) if total > 0 else 0
                        job_data["progress"] = f"Scraping: {processed}/{total} URLs ({progress_pct:.1f}%)"
                        jobs[job_id] = job_data
                        # Pas de save_job_status à chaque fois pour éviter trop d'I/O
                    
                    return result
                except Exception as e:
                    job_data["stats"]["urls_failed"] += 1
                    raise e
            
            # Remplacer temporairement la fonction
            upsert.process_single_url = tracked_process_single_url
            
            try:
                # Charger les URLs pour connaître le total
                from upsert import load_urls_from_sitemaps
                urls = load_urls_from_sitemaps(request.sitemaps)
                job_data["stats"]["urls_total"] = len(urls)
                job_data["progress"] = f"Phase 1/2: Scraping de {len(urls)} URLs..."
                jobs[job_id] = job_data
                save_job_status(job_id, job_data)
                
                # Exécuter le scraping
                from run import run_full_process
                run_full_process(
                    sitemaps=request.sitemaps,
                    output_folder=request.output_folder,
                    thematique=request.thematique,
                    workers=request.workers,
                    skip_scraping=False,
                    skip_embedding=True  # On fait l'embedding après
                )
                
                # Compter les fichiers créés
                import os
                if os.path.exists(request.output_folder):
                    files_count = sum([len(files) for _, _, files in os.walk(request.output_folder)])
                    dirs_count = sum([len(dirs) for _, dirs, _ in os.walk(request.output_folder)]) - 1
                    job_data["stats"]["files_created"] = files_count
                    job_data["stats"]["directories_created"] = max(0, dirs_count)
                
            finally:
                # Restaurer la fonction originale
                upsert.process_single_url = original_process_single_url
        
        # Phase 2: Embedding
        if not request.skip_embedding:
            job_data["stats"]["current_phase"] = "embedding"
            job_data["progress"] = "Phase 2/2: Génération des embeddings..."
            jobs[job_id] = job_data
            save_job_status(job_id, job_data)
            
            # Hook dans le processus d'embedding
            import embedding_pipeline
            original_upsert_to_pinecone = embedding_pipeline.upsert_to_pinecone
            
            def tracked_upsert_to_pinecone(index, vectors, namespace):
                result = original_upsert_to_pinecone(index, vectors, namespace)
                job_data["stats"]["vectors_created"] += len(vectors)
                job_data["progress"] = f"Embedding: {job_data['stats']['vectors_created']} vecteurs créés"
                jobs[job_id] = job_data
                return result
            
            # Remplacer temporairement
            embedding_pipeline.upsert_to_pinecone = tracked_upsert_to_pinecone
            
            try:
                from embedding_pipeline import run_embedding
                run_embedding(request.output_folder, request.thematique)
            finally:
                # Restaurer la fonction originale
                embedding_pipeline.upsert_to_pinecone = original_upsert_to_pinecone
        
        # Calculer le temps total
        end_time = time.time()
        total_time = end_time - start_time
        
        # Succès - Statistiques finales
        job_data["status"] = "completed"
        job_data["completed_at"] = datetime.now().isoformat()
        job_data["stats"]["end_time"] = end_time
        job_data["stats"]["total_duration_seconds"] = total_time
        job_data["stats"]["total_duration_formatted"] = format_duration(total_time)
        job_data["stats"]["current_phase"] = "completed"
        
        # Compter les services d'annuaire si applicable
        annuaire_files = 0
        if os.path.exists(os.path.join(request.output_folder, "Annuaire")):
            annuaire_files = len([f for f in os.listdir(os.path.join(request.output_folder, "Annuaire")) if f.endswith('.txt')])
        job_data["stats"]["annuaire_services"] = annuaire_files
        
        job_data["progress"] = f"✅ Terminé en {job_data['stats']['total_duration_formatted']}"
        job_data["summary"] = {
            "urls_scraped": job_data["stats"]["urls_processed"],
            "urls_failed": job_data["stats"]["urls_failed"],
            "files_created": job_data["stats"]["files_created"],
            "annuaire_services": job_data["stats"]["annuaire_services"],
            "vectors_created": job_data["stats"]["vectors_created"],
            "total_time": job_data["stats"]["total_duration_formatted"]
        }
        
        jobs[job_id] = job_data
        save_job_status(job_id, job_data)
        
    except Exception as e:
        # Erreur - Capturer les détails
        end_time = time.time()
        total_time = end_time - start_time
        
        job_data = jobs.get(job_id, {})
        job_data["status"] = "failed"
        job_data["completed_at"] = datetime.now().isoformat()
        job_data["error"] = str(e)
        job_data["error_type"] = type(e).__name__
        
        if "stats" not in job_data:
            job_data["stats"] = {}
        
        job_data["stats"]["end_time"] = end_time
        job_data["stats"]["total_duration_seconds"] = total_time
        job_data["stats"]["total_duration_formatted"] = format_duration(total_time)
        job_data["stats"]["current_phase"] = "failed"
        
        job_data["progress"] = f"❌ Erreur après {format_duration(total_time)}: {str(e)}"
        
        jobs[job_id] = job_data
        save_job_status(job_id, job_data)

def format_duration(seconds):
    """Formate une durée en secondes en format lisible"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

# Endpoints

@app.get("/", summary="Health check")
async def root():
    """Point d'entrée pour vérifier que l'API fonctionne"""
    return {
        "message": "Mon Service Public Scraper API",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/scrape", response_model=JobResponse, summary="Déclencher le scraping")
async def start_scraping(
    request: ScrapingRequest,
    background_tasks: BackgroundTasks, 
    token: str = Depends(verify_token)
):
    """
    Démarre un job de scraping en arrière-plan
    
    Nécessite un bearer token pour l'authentification.
    """
    # Générer un ID de job unique
    job_id = str(uuid.uuid4())
    
    # Créer les données du job
    job_data = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "parameters": request.dict()
    }
    
    # Sauvegarder le job
    jobs[job_id] = job_data
    save_job_status(job_id, job_data)
    
    # Lancer le job en arrière-plan
    background_tasks.add_task(run_scraping_job, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        message="Job de scraping créé et démarré"
    )

@app.get("/jobs/{job_id}", response_model=JobStatus, summary="Statut d'un job")
async def get_job_status(job_id: str, token: str = Depends(verify_token)):
    """
    Récupère le statut d'un job spécifique
    """
    # Chercher dans la mémoire d'abord
    if job_id in jobs:
        job_data = jobs[job_id]
    else:
        # Chercher dans les fichiers sauvegardés
        job_data = load_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} non trouvé"
        )
    
    return JobStatus(**job_data)

@app.get("/jobs", summary="Liste des jobs")
async def list_jobs(token: str = Depends(verify_token)):
    """
    Liste tous les jobs (actifs et sauvegardés)
    """
    all_jobs = []
    
    # Jobs en mémoire
    all_jobs.extend(jobs.values())
    
    # Jobs sauvegardés
    for job_file in JOBS_DIR.glob("*.json"):
        job_id = job_file.stem
        if job_id not in jobs:
            job_data = load_job_status(job_id)
            if job_data:
                all_jobs.append(job_data)
    
    # Trier par date de création (plus récents en premier)
    all_jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "jobs": all_jobs,
        "total": len(all_jobs)
    }

@app.delete("/jobs/{job_id}", summary="Supprimer un job")
async def delete_job(job_id: str, token: str = Depends(verify_token)):
    """
    Supprime un job et ses données
    """
    # Supprimer de la mémoire
    if job_id in jobs:
        del jobs[job_id]
    
    # Supprimer le fichier
    job_file = JOBS_DIR / f"{job_id}.json"
    if job_file.exists():
        job_file.unlink()
        return {"message": f"Job {job_id} supprimé"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} non trouvé"
        )

@app.post("/scrape/quick", response_model=JobResponse, summary="Scraping rapide avec paramètres prédéfinis")
async def quick_scrape(
    background_tasks: BackgroundTasks,
    skip_scraping: bool = False,
    skip_embedding: bool = False,
    workers: int = 8,
    token: str = Depends(verify_token)
):
    """
    Lance un scraping avec les paramètres par défaut (tous les sitemaps)
    """
    default_sitemaps = [
        "https://monservicepublic.gouv.mc/sitemap-1.xml",
        "https://monservicepublic.gouv.mc/sitemap-2.xml",
        "https://monservicepublic.gouv.mc/sitemap-3.xml",
        "https://monservicepublic.gouv.mc/sitemap-4.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-1.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-2.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-3.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-4.xml"
    ]
    
    request = ScrapingRequest(
        sitemaps=default_sitemaps,
        skip_scraping=skip_scraping,
        skip_embedding=skip_embedding,
        workers=workers
    )
    
    return await start_scraping(request, background_tasks, token)

@app.post("/scrape/full", response_model=JobResponse, summary="Scraping + Embedding complet (tous sitemaps)")
async def full_scraping(
    background_tasks: BackgroundTasks,
    workers: int = 8,
    token: str = Depends(verify_token)
):
    """
    Lance un scraping + embedding COMPLET avec tous les sitemaps
    (Aucun paramètre de sitemap requis - utilise tous les sitemaps automatiquement)
    """
    all_sitemaps = [
        "https://monservicepublic.gouv.mc/sitemap-1.xml",
        "https://monservicepublic.gouv.mc/sitemap-2.xml",
        "https://monservicepublic.gouv.mc/sitemap-3.xml",
        "https://monservicepublic.gouv.mc/sitemap-4.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-1.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-2.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-3.xml",
        "https://monservicepublic.gouv.mc/en/sitemap-4.xml"
    ]
    
    request = ScrapingRequest(
        sitemaps=all_sitemaps,
        output_folder="output",
        thematique="monservicepublic",
        workers=workers,
        skip_scraping=False,
        skip_embedding=False
    )
    
    return await start_scraping(request, background_tasks, token)

@app.post("/embedding/run", response_model=JobResponse, summary="Embedding seul (sans scraping)")
async def run_embedding_only(
    background_tasks: BackgroundTasks,
    output_folder: str = "output",
    thematique: str = "monservicepublic",
    token: str = Depends(verify_token)
):
    """
    Lance UNIQUEMENT l'embedding sur les fichiers existants
    (Suppose que le scraping a déjà été fait)
    """
    # Créer une requête qui skip le scraping
    request = ScrapingRequest(
        sitemaps=[],  # Pas besoin de sitemaps pour embedding seul
        output_folder=output_folder,
        thematique=thematique,
        workers=1,  # Pas utilisé pour embedding
        skip_scraping=True,
        skip_embedding=False
    )
    
    return await start_scraping(request, background_tasks, token)

@app.get("/jobs/{job_id}/stats", summary="Statistiques détaillées d'un job")
async def get_job_stats(job_id: str, token: str = Depends(verify_token)):
    """
    Récupère uniquement les statistiques détaillées d'un job
    Idéal pour le suivi en temps réel du progrès
    """
    # Chercher le job
    if job_id in jobs:
        job_data = jobs[job_id]
    else:
        job_data = load_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} non trouvé"
        )
    
    # Retourner seulement les stats + infos essentielles
    return {
        "job_id": job_id,
        "status": job_data.get("status", "unknown"),
        "current_phase": job_data.get("stats", {}).get("current_phase", "unknown"),
        "progress": job_data.get("progress", ""),
        "stats": job_data.get("stats", {}),
        "summary": job_data.get("summary"),
        "error": job_data.get("error"),
        "duration": job_data.get("stats", {}).get("total_duration_formatted")
    }

@app.get("/jobs/{job_id}/progress", summary="Progrès simplifié d'un job")
async def get_job_progress(job_id: str, token: str = Depends(verify_token)):
    """
    Récupère uniquement le progrès d'un job (version allégée)
    """
    if job_id in jobs:
        job_data = jobs[job_id]
    else:
        job_data = load_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} non trouvé"
        )
    
    stats = job_data.get("stats", {})
    
    # Calculer le pourcentage de progression
    progress_percentage = 0
    if stats.get("urls_total", 0) > 0:
        progress_percentage = (stats.get("urls_processed", 0) / stats.get("urls_total", 1)) * 100
    
    return {
        "job_id": job_id,
        "status": job_data.get("status", "unknown"),
        "progress_text": job_data.get("progress", ""),
        "progress_percentage": round(progress_percentage, 1),
        "current_phase": stats.get("current_phase", "unknown"),
        "urls_processed": stats.get("urls_processed", 0),
        "urls_total": stats.get("urls_total", 0),
        "vectors_created": stats.get("vectors_created", 0),
        "is_completed": job_data.get("status") in ["completed", "failed"],
        "error": job_data.get("error") if job_data.get("status") == "failed" else None
    }

@app.get("/jobs/active", summary="Liste des jobs actifs seulement")
async def list_active_jobs(token: str = Depends(verify_token)):
    """
    Liste uniquement les jobs en cours d'exécution
    """
    active_jobs = []
    
    # Jobs en mémoire (généralement actifs)
    for job_data in jobs.values():
        if job_data.get("status") in ["pending", "running"]:
            active_jobs.append({
                "job_id": job_data.get("job_id"),
                "status": job_data.get("status"),
                "progress": job_data.get("progress", ""),
                "current_phase": job_data.get("stats", {}).get("current_phase", "unknown"),
                "created_at": job_data.get("created_at"),
                "started_at": job_data.get("started_at")
            })
    
    return {
        "active_jobs": active_jobs,
        "count": len(active_jobs)
    }

@app.get("/status/simple/{job_id}", summary="État simple d'un job")
async def get_simple_status(job_id: str, token: str = Depends(verify_token)):
    """
    Récupère l'état d'un job de manière simplifiée
    Retourne : pending, running, completed, failed + infos essentielles
    """
    # Chercher le job
    if job_id in jobs:
        job_data = jobs[job_id]
    else:
        job_data = load_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} non trouvé"
        )
    
    status = job_data.get("status", "unknown")
    stats = job_data.get("stats", {})
    
    result = {
        "job_id": job_id,
        "status": status,
        "is_running": status == "running",
        "is_completed": status == "completed",
        "is_failed": status == "failed",
        "progress_text": job_data.get("progress", ""),
        "current_phase": stats.get("current_phase", "unknown")
    }
    
    # Ajouter des infos selon le statut
    if status == "completed":
        summary = job_data.get("summary", {})
        result.update({
            "urls_scraped": summary.get("urls_scraped", 0),
            "vectors_created": summary.get("vectors_created", 0),
            "total_time": summary.get("total_time", "0s"),
            "files_created": summary.get("files_created", 0),
            "annuaire_services": summary.get("annuaire_services", 0)
        })
    elif status == "failed":
        result.update({
            "error": job_data.get("error", "Erreur inconnue"),
            "error_type": job_data.get("error_type", "Unknown")
        })
    elif status == "running":
        result.update({
            "urls_processed": stats.get("urls_processed", 0),
            "urls_total": stats.get("urls_total", 0),
            "vectors_created": stats.get("vectors_created", 0)
        })
    
    return result

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Démarrage de l'API Scraper")
    print(f"🔑 Token API: {API_TOKEN}")
    print("📚 Documentation: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000) 
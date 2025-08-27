# Guide d'utilisation pratique - API Scraper

## 🎯 Vos 3 cas d'usage principaux

### 1️⃣ **Scraping + Embedding COMPLET** (tous sitemaps automatiquement)

**CURL :**

```bash
# Lancer le processus complet (scraping + embedding)
curl -X POST "http://localhost:8000/scrape/full" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"workers": 8}'

# Réponse :
# {
#   "job_id": "abc123-def456-...",
#   "status": "pending",
#   "message": "Job de scraping créé et démarré"
# }
```

**Python :**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

# Lancer le processus complet
response = requests.post(
    "http://localhost:8000/scrape/full",
    headers=headers,
    json={"workers": 8}
)

job = response.json()
job_id = job["job_id"]
print(f"🚀 Processus complet lancé : {job_id}")
```

---

### 2️⃣ **Embedding SEUL** (sur fichiers existants)

**CURL :**

```bash
# Lancer seulement l'embedding (suppose que les fichiers existent dans output/)
curl -X POST "http://localhost:8000/embedding/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_folder": "output",
    "thematique": "monservicepublic"
  }'
```

**Python :**

```python
# Lancer seulement l'embedding
response = requests.post(
    "http://localhost:8000/embedding/run",
    headers=headers,
    json={
        "output_folder": "output",
        "thematique": "monservicepublic"
    }
)

job = response.json()
job_id = job["job_id"]
print(f"🔢 Embedding seul lancé : {job_id}")
```

---

### 3️⃣ **Vérifier l'état COMPLET** (simple et efficace)

**CURL :**

```bash
# Vérifier l'état d'un job de manière simple
curl -X GET "http://localhost:8000/status/simple/YOUR_JOB_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python - Suivi complet automatisé :**

```python
import time

def monitor_job_simple(job_id):
    """Suit un job jusqu'à completion avec état simple"""

    print(f"📊 Suivi du job {job_id}...")

    while True:
        response = requests.get(
            f"http://localhost:8000/status/simple/{job_id}",
            headers=headers
        )

        status_data = response.json()

        # Infos de base
        status = status_data["status"]
        phase = status_data["current_phase"]
        progress = status_data["progress_text"]

        print(f"📈 {status.upper()} | {phase} | {progress}")

        # Si terminé
        if status_data["is_completed"]:
            print("✅ JOB TERMINÉ !")
            print(f"   📄 URLs scrapées : {status_data.get('urls_scraped', 0)}")
            print(f"   🔢 Vecteurs créés : {status_data.get('vectors_created', 0)}")
            print(f"   📁 Fichiers créés : {status_data.get('files_created', 0)}")
            print(f"   🏢 Services annuaire : {status_data.get('annuaire_services', 0)}")
            print(f"   ⏱️  Temps total : {status_data.get('total_time', 'N/A')}")
            break

        # Si erreur
        elif status_data["is_failed"]:
            print("❌ JOB ÉCHOUÉ !")
            print(f"   Erreur : {status_data.get('error', 'Inconnue')}")
            break

        # Si en cours
        elif status_data["is_running"]:
            urls_done = status_data.get("urls_processed", 0)
            urls_total = status_data.get("urls_total", 0)
            vectors = status_data.get("vectors_created", 0)

            if urls_total > 0:
                pct = (urls_done / urls_total) * 100
                print(f"   Progress: {pct:.1f}% | URLs: {urls_done}/{urls_total} | Vecteurs: {vectors}")

        time.sleep(5)  # Vérifier toutes les 5 secondes

# Utilisation
job_id = "votre-job-id-ici"
monitor_job_simple(job_id)
```

---

## 🔥 **Script complet - Workflow type**

```python
import requests
import time

TOKEN = "YOUR_TOKEN_HERE"
BASE_URL = "http://localhost:8000"
headers = {"Authorization": f"Bearer {TOKEN}"}

def complete_workflow():
    """Workflow complet : lancer + surveiller"""

    print("🚀 DÉMARRAGE WORKFLOW COMPLET")
    print("="*50)

    # 1. Lancer le processus complet
    print("\n1️⃣ Lancement scraping + embedding complet...")

    response = requests.post(
        f"{BASE_URL}/scrape/full",
        headers=headers,
        json={"workers": 8}
    )

    if response.status_code != 200:
        print(f"❌ Erreur : {response.text}")
        return

    job = response.json()
    job_id = job["job_id"]

    print(f"✅ Job créé : {job_id}")
    print(f"📊 Status initial : {job['status']}")

    # 2. Surveiller jusqu'à completion
    print(f"\n2️⃣ Surveillance en cours...")
    print("-" * 60)

    while True:
        # Vérifier l'état
        response = requests.get(
            f"{BASE_URL}/status/simple/{job_id}",
            headers=headers
        )

        status = response.json()

        print(f"📈 {status['status'].upper():10} | {status['current_phase']:12} | {status['progress_text']}")

        if status["is_completed"]:
            print("\n🎉 PROCESSUS TERMINÉ AVEC SUCCÈS !")
            print("=" * 50)
            print(f"📊 Résultats finaux :")
            print(f"   📄 URLs scrapées      : {status.get('urls_scraped', 0):,}")
            print(f"   📁 Fichiers créés     : {status.get('files_created', 0):,}")
            print(f"   🏢 Services annuaire  : {status.get('annuaire_services', 0)}")
            print(f"   🔢 Vecteurs créés     : {status.get('vectors_created', 0):,}")
            print(f"   ⏱️  Temps total       : {status.get('total_time', 'N/A')}")
            break

        elif status["is_failed"]:
            print(f"\n❌ PROCESSUS ÉCHOUÉ !")
            print(f"   Erreur : {status.get('error', 'Inconnue')}")
            break

        time.sleep(10)  # Attendre 10 secondes

    print("\n✅ Workflow terminé !")

if __name__ == "__main__":
    complete_workflow()
```

---

## 📋 **Réponses des nouveaux endpoints**

### `/scrape/full` - Job créé

```json
{
  "job_id": "abc123-def456-789",
  "status": "pending",
  "message": "Job de scraping créé et démarré"
}
```

### `/embedding/run` - Job embedding

```json
{
  "job_id": "xyz789-abc123-456",
  "status": "pending",
  "message": "Job de scraping créé et démarré"
}
```

### `/status/simple/{id}` - État en cours

```json
{
  "job_id": "abc123-def456-789",
  "status": "running",
  "is_running": true,
  "is_completed": false,
  "is_failed": false,
  "progress_text": "Scraping: 450/1500 URLs (30.0%)",
  "current_phase": "scraping",
  "urls_processed": 450,
  "urls_total": 1500,
  "vectors_created": 0
}
```

### `/status/simple/{id}` - État terminé

```json
{
  "job_id": "abc123-def456-789",
  "status": "completed",
  "is_running": false,
  "is_completed": true,
  "is_failed": false,
  "progress_text": "✅ Terminé en 15m 32s",
  "current_phase": "completed",
  "urls_scraped": 1485,
  "vectors_created": 3247,
  "total_time": "15m 32s",
  "files_created": 1485,
  "annuaire_services": 71
}
```

---

## 🎯 **Résumé pour vous**

```bash
# 1. Processus COMPLET (tous sitemaps automatiquement)
curl -X POST "http://localhost:8000/scrape/full" -H "Authorization: Bearer TOKEN" -d '{"workers":8}'

# 2. Embedding SEUL (fichiers existants)
curl -X POST "http://localhost:8000/embedding/run" -H "Authorization: Bearer TOKEN" -d '{}'

# 3. État SIMPLE (vérification facile)
curl -X GET "http://localhost:8000/status/simple/JOB_ID" -H "Authorization: Bearer TOKEN"
```

**C'est exactement ce que vous vouliez !** 🎉

# API Scraper - Exemples d'utilisation

## 🚀 Démarrage rapide

### 1. Configuration du token

```bash
# Générer un token sécurisé
python3 api_config.py
```

### 2. Démarrage de l'API

```bash
# Démarrer le serveur API
python3 start_api.py
```

L'API sera disponible sur : **http://localhost:8000**

## 🔑 Authentification

Toutes les requêtes nécessitent un bearer token dans l'en-tête :

```
Authorization: Bearer your-token-here
```

## 📚 Endpoints disponibles

### Health Check

```bash
curl http://localhost:8000/
```

### Documentation interactive

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## 🔥 Exemples d'utilisation

### 1. Scraping rapide (paramètres par défaut)

**CURL :**

```bash
curl -X POST "http://localhost:8000/scrape/quick" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "skip_scraping": false,
    "skip_embedding": false,
    "workers": 8
  }'
```

**Python requests :**

```python
import requests

url = "http://localhost:8000/scrape/quick"
headers = {
    "Authorization": "Bearer YOUR_TOKEN_HERE",
    "Content-Type": "application/json"
}
data = {
    "skip_scraping": False,
    "skip_embedding": False,
    "workers": 8
}

response = requests.post(url, headers=headers, json=data)
job = response.json()
print(f"Job créé : {job['job_id']}")
```

**JavaScript/Node.js :**

```javascript
const axios = require("axios");

const response = await axios.post(
  "http://localhost:8000/scrape/quick",
  {
    skip_scraping: false,
    skip_embedding: false,
    workers: 8,
  },
  {
    headers: {
      Authorization: "Bearer YOUR_TOKEN_HERE",
      "Content-Type": "application/json",
    },
  }
);

console.log("Job créé :", response.data.job_id);
```

### 2. Scraping personnalisé

**CURL :**

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "sitemaps": [
      "https://monservicepublic.gouv.mc/sitemap-1.xml",
      "https://monservicepublic.gouv.mc/sitemap-2.xml"
    ],
    "output_folder": "custom_output",
    "thematique": "test",
    "workers": 4,
    "skip_scraping": false,
    "skip_embedding": false
  }'
```

### 3. Suivre un job avec statistiques détaillées

**CURL - Progrès simplifié :**

```bash
# Récupérer le progrès en temps réel (léger)
curl -X GET "http://localhost:8000/jobs/YOUR_JOB_ID/progress" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**CURL - Statistiques complètes :**

```bash
# Récupérer toutes les statistiques détaillées
curl -X GET "http://localhost:8000/jobs/YOUR_JOB_ID/stats" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Python script complet avec suivi détaillé :**

```python
import requests
import time
import json

TOKEN = "YOUR_TOKEN_HERE"
BASE_URL = "http://localhost:8000"

headers = {"Authorization": f"Bearer {TOKEN}"}

# 1. Lancer un job
response = requests.post(
    f"{BASE_URL}/scrape/quick",
    headers=headers,
    json={"workers": 4}
)

job_id = response.json()["job_id"]
print(f"🚀 Job lancé : {job_id}")

# 2. Suivre le progrès avec statistiques détaillées
while True:
    # Récupérer le progrès (version légère)
    response = requests.get(f"{BASE_URL}/jobs/{job_id}/progress", headers=headers)
    progress = response.json()

    status = progress["status"]
    phase = progress["current_phase"]
    percentage = progress["progress_percentage"]
    urls_done = progress["urls_processed"]
    urls_total = progress["urls_total"]
    vectors = progress["vectors_created"]

    print(f"📊 {status.upper()} | {phase} | {percentage}% | URLs: {urls_done}/{urls_total} | Vecteurs: {vectors}")

    if progress["is_completed"]:
        break

    time.sleep(5)  # Vérifier toutes les 5 secondes

# 3. Récupérer les statistiques finales complètes
if status == "completed":
    response = requests.get(f"{BASE_URL}/jobs/{job_id}/stats", headers=headers)
    final_stats = response.json()

    print("\n🎉 SCRAPING TERMINÉ !")
    print("="*50)
    print(f"⏱️  Durée totale : {final_stats['duration']}")

    if final_stats.get('summary'):
        summary = final_stats['summary']
        print(f"📄 URLs scrapées : {summary['urls_scraped']}")
        print(f"❌ URLs échouées : {summary['urls_failed']}")
        print(f"📁 Fichiers créés : {summary['files_created']}")
        print(f"🏢 Services annuaire : {summary['annuaire_services']}")
        print(f"🔢 Vecteurs créés : {summary['vectors_created']}")

    stats = final_stats.get('stats', {})
    print(f"📂 Dossiers créés : {stats.get('directories_created', 0)}")

else:
    print(f"❌ Erreur : {progress.get('error', 'Erreur inconnue')}")
```

**JavaScript/Node.js avec suivi temps réel :**

```javascript
const axios = require("axios");

const TOKEN = "YOUR_TOKEN_HERE";
const BASE_URL = "http://localhost:8000";

const headers = { Authorization: `Bearer ${TOKEN}` };

async function runScrapingJob() {
  try {
    // 1. Lancer le job
    const jobResponse = await axios.post(
      `${BASE_URL}/scrape/quick`,
      { workers: 4 },
      { headers }
    );

    const jobId = jobResponse.data.job_id;
    console.log(`🚀 Job lancé : ${jobId}`);

    // 2. Suivre le progrès
    let isCompleted = false;
    while (!isCompleted) {
      const progressResponse = await axios.get(
        `${BASE_URL}/jobs/${jobId}/progress`,
        { headers }
      );

      const progress = progressResponse.data;

      console.log(
        `📊 ${progress.status.toUpperCase()} | ${progress.current_phase} | ${
          progress.progress_percentage
        }% | URLs: ${progress.urls_processed}/${progress.urls_total}`
      );

      isCompleted = progress.is_completed;

      if (!isCompleted) {
        await new Promise((resolve) => setTimeout(resolve, 5000)); // 5 secondes
      }
    }

    // 3. Statistiques finales
    const statsResponse = await axios.get(`${BASE_URL}/jobs/${jobId}/stats`, {
      headers,
    });

    const finalStats = statsResponse.data;

    if (finalStats.status === "completed") {
      console.log("\n🎉 SCRAPING TERMINÉ !");
      console.log(`⏱️  Durée : ${finalStats.duration}`);

      if (finalStats.summary) {
        const s = finalStats.summary;
        console.log(`📊 Résultats :`);
        console.log(`   URLs scrapées : ${s.urls_scraped}`);
        console.log(`   Fichiers créés : ${s.files_created}`);
        console.log(`   Vecteurs créés : ${s.vectors_created}`);
        console.log(`   Services annuaire : ${s.annuaire_services}`);
      }
    } else {
      console.log(`❌ Erreur : ${finalStats.error}`);
    }
  } catch (error) {
    console.error("Erreur :", error.response?.data || error.message);
  }
}

runScrapingJob();
```

### 4. Jobs actifs seulement

**CURL :**

```bash
# Lister uniquement les jobs en cours
curl -X GET "http://localhost:8000/jobs/active" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 5. Lister tous les jobs

**CURL :**

```bash
curl -X GET "http://localhost:8000/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 6. Supprimer un job

**CURL :**

```bash
curl -X DELETE "http://localhost:8000/jobs/YOUR_JOB_ID" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📊 Réponses de l'API

### Job créé avec succès

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Job de scraping créé et démarré"
}
```

### Progrès d'un job (GET /jobs/{id}/progress)

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "progress_text": "Scraping: 150/1500 URLs (10.0%)",
  "progress_percentage": 10.0,
  "current_phase": "scraping",
  "urls_processed": 150,
  "urls_total": 1500,
  "vectors_created": 0,
  "is_completed": false,
  "error": null
}
```

### Statistiques complètes (GET /jobs/{id}/stats)

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "current_phase": "completed",
  "progress": "✅ Terminé en 15m 32s",
  "duration": "15m 32s",
  "stats": {
    "urls_total": 1500,
    "urls_processed": 1485,
    "urls_failed": 15,
    "annuaire_services": 71,
    "vectors_created": 3247,
    "directories_created": 12,
    "files_created": 1485,
    "total_duration_seconds": 932.5,
    "total_duration_formatted": "15m 32s",
    "current_phase": "completed"
  },
  "summary": {
    "urls_scraped": 1485,
    "urls_failed": 15,
    "files_created": 1485,
    "annuaire_services": 71,
    "vectors_created": 3247,
    "total_time": "15m 32s"
  },
  "error": null
}
```

### Status complet d'un job (GET /jobs/{id})

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "created_at": "2025-07-31T18:30:00.000Z",
  "started_at": "2025-07-31T18:30:05.000Z",
  "progress": "Phase 2/2: Génération des embeddings...",
  "parameters": {
    "sitemaps": ["https://monservicepublic.gouv.mc/sitemap-1.xml", "..."],
    "workers": 8,
    "skip_scraping": false,
    "skip_embedding": false
  },
  "stats": {
    "urls_total": 1500,
    "urls_processed": 1500,
    "urls_failed": 0,
    "vectors_created": 1250,
    "current_phase": "embedding"
  }
}
```

### Jobs actifs (GET /jobs/active)

```json
{
  "active_jobs": [
    {
      "job_id": "123...",
      "status": "running",
      "progress": "Scraping: 500/1500 URLs (33.3%)",
      "current_phase": "scraping",
      "created_at": "2025-07-31T18:30:00.000Z",
      "started_at": "2025-07-31T18:30:05.000Z"
    }
  ],
  "count": 1
}
```

### Job terminé avec erreur

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "failed",
  "progress": "❌ Erreur après 5m 23s: OpenAI API rate limit exceeded",
  "error": "OpenAI API rate limit exceeded",
  "error_type": "RateLimitError",
  "stats": {
    "urls_processed": 450,
    "urls_total": 1500,
    "urls_failed": 1,
    "total_duration_formatted": "5m 23s",
    "current_phase": "failed"
  }
}
```

## ⚠️ Codes d'erreur

- **401 Unauthorized** : Token invalide ou manquant
- **404 Not Found** : Job non trouvé
- **422 Validation Error** : Paramètres invalides
- **500 Internal Error** : Erreur serveur

## 🔒 Sécurité

1. **Token sécurisé** : Utilisez un token long et aléatoire
2. **HTTPS** : En production, utilisez HTTPS uniquement
3. **Firewall** : Limitez l'accès à l'API aux IPs autorisées
4. **Logs** : Surveillez les logs d'accès

## 🐳 Déploiement Docker (optionnel)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python3", "start_api.py"]
```

## 📱 Webhooks (future)

L'API pourrait être étendue pour envoyer des notifications webhook quand un job se termine :

```json
{
  "job_id": "123...",
  "status": "completed",
  "webhook_url": "https://your-app.com/webhook/scraper"
}
```

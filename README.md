# Mon Service Public - Scraper & API

## Setup

1. Python 3.11
2. Create venv and install deps:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Configure token and env:

```bash
python3 api_config.py
# then add OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME to .env if not already
```

## Run API

```bash
source venv/bin/activate
python3 start_api.py
# Docs: http://localhost:8000/docs
```

## Endpoints (Bearer required)

- POST /scrape/full → scrape+embed all sitemaps
- POST /embedding/run → embed only existing files
- GET /status/simple/{job_id} → simplified status
- GET /jobs/{job_id}/progress → progress
- GET /jobs/{job_id}/stats → full stats

## Validate end-to-end

1. Quick scrape+embed:

```bash
curl -X POST "http://localhost:8000/scrape/full" \
  -H "Authorization: Bearer $SCRAPER_API_TOKEN" \
  -H "Content-Type: application/json" -d '{"workers":8}'
```

2. Check progress:

```bash
curl -H "Authorization: Bearer $SCRAPER_API_TOKEN" \
  http://localhost:8000/jobs/active | jq
```

3. Final stats:

```bash
curl -H "Authorization: Bearer $SCRAPER_API_TOKEN" \
  http://localhost:8000/jobs/<JOB_ID>/stats | jq
```

## CLI helpers

- `simple_client.py` interactive client for the 3 main flows.

## Notes

- API only checks SCRAPER_API_TOKEN at startup. Model keys are checked on use.
- Output HTML is simplified for embedding quality (links kept, no CSS attrs).

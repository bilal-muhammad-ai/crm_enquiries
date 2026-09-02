# CRM Enquiry System — FastAPI + CrewAI

Glancy Fawcett enquiry intake, CRM integration, KB-powered email drafting, human approval, calendar scheduling, and Fathom meeting follow-up.

## Quick Start

```bash
cd crm_enquiries
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python scripts/ingest_knowledge.py
uvicorn crm_enquiries.main:app --reload --app-dir src
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/enquiries` | API Key | Submit enquiry form |
| GET | `/api/v1/enquiries/{id}` | API Key | Enquiry status + timeline |
| GET | `/api/v1/enquiries/{id}/draft` | JWT/API Key | Pending email draft |
| POST | `/api/v1/enquiries/{id}/approve` | JWT/API Key | Approve/reject/revise draft |
| GET | `/api/v1/enquiries/{id}/availability` | JWT/API Key | Calendar slots |
| POST | `/api/v1/enquiries/{id}/schedule` | JWT/API Key | Schedule meeting |
| POST | `/api/v1/webhooks/fathom` | Webhook signature | Fathom transcript webhook |
| GET | `/health` | None | Health check |

## Enquiry Intake Fields

Required: `name`, `email`, `enquiry_type`, `message`  
Optional: `phone`, `company`  
Ignored: `terms_accepted`, `newsletter_opt_in`

### Enquiry Types

- `superyacht` — Superyacht Outfitting
- `residential` — Residential Project
- `aircraft` — Private Aircraft
- `general` — General Enquiry

## Architecture

- **FastAPI** — HTTP orchestration, persistence, external integrations
- **CrewAI Crews** — Analysis, Response, Meeting Analysis
- **Flows** — Enquiry lifecycle + Fathom follow-up orchestrators
- **SuiteCRM** — Enquiry/Contact/Account/Meeting records (mock mode for dev)
- **Chroma** — FAQ knowledge base retrieval
- **M365 Graph** — Email + calendar (mock mode for dev)

## Configuration

See `.env.example`. CRM field mapping in `config/crm_field_map.yaml`.

## Tests

```bash
pytest tests/ -v
```

## Knowledge Base

FAQ markdown lives in `knowledge/glancy_faq/`. Ingest with:

```bash
python scripts/ingest_knowledge.py [--force]
```

Generate PDFs (optional):

```bash
pip install fpdf2
python scripts/generate_kb_pdfs.py
```

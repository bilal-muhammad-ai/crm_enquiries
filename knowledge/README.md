# Glancy Fawcett Knowledge Base

Structured knowledge base documents for the **CRM Enquiry System** (FastAPI + CrewAI). Content sourced from the official Glancy Fawcett website.

## Sources

| Page | URL |
|------|-----|
| Company homepage | https://www.glancyfawcett.com/ |
| Global showrooms | https://www.glancyfawcett.com/showrooms |
| FAQs | https://www.glancyfawcett.com/faqs |

## Directory Structure

```
knowledge/
├── glancy_faq/          # Markdown source files (topic-based, for Chroma ingestion)
│   ├── 01_company_overview.md
│   ├── 02_about_and_clients.md
│   ├── 03_starting_your_project.md
│   ├── 04_in_house_product_design.md
│   ├── 05_quality_logistics_delivery.md
│   ├── 06_commercial_payment_terms.md
│   └── 07_showrooms.md
└── pdf/                 # Generated PDF documents (for RAG / CrewAI knowledge)
    ├── 01_company_overview.pdf
    ├── 02_about_and_clients.pdf
    ├── 03_starting_your_project.pdf
    ├── 04_in_house_product_design.pdf
    ├── 05_quality_logistics_delivery.pdf
    ├── 06_commercial_payment_terms.pdf
    ├── 07_showrooms.pdf
    └── glancy_fawcett_knowledge_base_complete.pdf
```

## Regenerating PDFs

```bash
pip install fpdf2
python scripts/generate_kb_pdfs.py
```

## Usage in CRM Enquiry System

These documents feed the **Response Crew** via `KnowledgeBaseService`:

- **KnowledgeRetriever** agent queries KB for payment terms, showroom hours, NDA policy, lead times, Designed by GF, etc.
- **ComplianceValidator** verifies email drafts against KB content only
- **kb_citations** in `EmailDraft` output reference FAQ section titles

### Ingestion Options

1. **Markdown → Chroma** — ingest `knowledge/glancy_faq/*.md` (planned default)
2. **PDF → Chroma** — ingest `knowledge/pdf/*.pdf` (pattern from `resume_ai_assistant`)

## Topic Coverage

| Document | Key Topics |
|----------|------------|
| Company Overview | Track record, services, brands, locations, testimonials |
| About & Clients | Who GF is, client types, partners |
| Starting Your Project | Brief-taking, NDAs, timelines, lead times, presentations |
| Designed by GF | Bespoke product design, motifs, design journey |
| Quality & Delivery | QC process, packing, worldwide shipping |
| Payment Terms | 50/50 terms, payment methods, discounts |
| Showrooms | Manchester, Abu Dhabi, Fort Lauderdale, booking |

## Contact Reference (for agent responses)

- **Email:** sales@glancyfawcett.com
- **Phone:** +44 161 876 5356
- **Showroom hours:** Mon–Fri, 9:00 AM – 5:30 PM (appointment required)

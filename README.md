# OpportunityForge v1

OpportunityForge is an opportunity-intelligence platform for public-data-backed businesses. It discovers datasets, profiles their commercial meaning, identifies valuable decisions, maps buyers and monetization paths, scores opportunities, and generates auditable dossiers.

The product is intentionally **not** a website generator, programmatic SEO platform, or AI content factory. The core workflow is:

```text
Dataset -> Decision -> Buyer -> Revenue
```

## Repository layout

- `backend/` — FastAPI, SQLModel, Alembic-ready backend skeleton.
- `frontend/` — SvelteKit/Tailwind/shadcn-svelte-ready frontend skeleton.
- `docs/` — execution architecture and product principles.

## v1 build order

1. Dataset Catalog
2. Dataset Profiler
3. Decision Agent
4. Buyer Agent
5. Monetization Agent
6. Opportunity Engine
7. Opportunity Graph
8. Dossier Generator
9. Dashboard
10. Outcomes Tracking

## Backend quickstart

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn opportunityforge.main:app --reload
```

# Agentic BI Analyst

An agentic BI analyst that combines natural-language reasoning with governed
SQL, deterministic analytics, a semantic KPI layer, automated validation,
visualization, and evidence-backed business recommendations.

## Run locally with Docker

1. Copy `.env.example` to `.env`.
2. Set `MYSQL_PASSWORD`.
3. Make sure `data/generated/` contains the project dataset.
4. Run:

```powershell
docker compose up --build
```

Then open:

- FastAPI: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Streamlit: http://localhost:8501

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete deployment
workflow, database reset procedure, and troubleshooting commands.

## Important

The generated dataset is intentionally excluded from Docker image builds.
The existing CSV-to-MySQL loader is reused by the one-shot `db-init` service.

Never commit `.env` or credentials.

# Agentic BI Analyst — Docker Deployment

## Stack

The local Docker Compose stack contains:

- MySQL 8.4
- FastAPI
- Streamlit
- A one-shot database initialization service

The existing `scripts/load_data.py` remains the single CSV-to-MySQL loader.

## Prerequisites

- Docker Desktop with Compose support
- The generated dataset under `data/generated/`
- A local `.env` file

Copy `.env.example` to `.env` and set the MySQL password.

Do not commit `.env`.

## Dataset size

The generated dataset is intentionally **not copied into the Docker image**.
The repository's generated CSV dataset is approximately 1 GB, with
`inventory_snapshots.csv` accounting for roughly 995 MB.

Compose mounts the local `data/` directory into the one-shot `db-init`
container as read-only.

## First startup

From the repository root:

```powershell
docker compose up --build
```

The startup order is:

1. MySQL starts.
2. MySQL healthcheck becomes healthy.
3. `db-init` checks the governed tables.
4. If all tables are empty, the existing `scripts/load_data.py` is executed.
5. If the dataset is already complete, `db-init` exits successfully without reloading.
6. FastAPI starts.
7. Streamlit starts.

The initial CSV load can take time because the dataset contains about
16.8 million inventory snapshot rows.

## URLs

After startup:

- FastAPI health: `http://localhost:8000/health`
- FastAPI OpenAPI: `http://localhost:8000/docs`
- Streamlit: `http://localhost:8501`

## Stopping

```powershell
docker compose down
```

This stops and removes containers but preserves the named MySQL volume.

## Full database reset

Only use this when you intentionally want to rebuild the database:

```powershell
docker compose down -v
docker compose up --build
```

Because `db-init` protects against duplicate and partial loads, do not
manually rerun `scripts/load_data.py` against a populated database.

## Useful commands

Check services:

```powershell
docker compose ps
```

View initialization logs:

```powershell
docker compose logs db-init
```

View API logs:

```powershell
docker compose logs api
```

View Streamlit logs:

```powershell
docker compose logs streamlit
```

View MySQL logs:

```powershell
docker compose logs mysql
```

Stop without removing containers:

```powershell
docker compose stop
```

## Security notes

- Keep credentials in `.env`.
- Never commit `.env`.
- Use a dedicated read-only analytical database user for production.
- The Compose configuration is intended for local development/demo deployment.
- Rotate any credential that has been exposed outside the local environment.

## Architecture boundary

This deployment layer does not replace or duplicate:

- semantic-layer rules
- SQL validation
- SQL Analyst Agent
- Insight/Root-Cause/Critic agents
- Visualization/Recommendation/Report Composer
- Orchestrator logic
- FastAPI analytical contracts
- Streamlit analytical flow

Docker only packages and orchestrates the existing system.

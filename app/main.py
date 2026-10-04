from fastapi import FastAPI

from app.agents.orchestrator import Orchestrator
from app.api.routes import build_analysis_router, router


def create_app(orchestrator: Orchestrator | None = None) -> FastAPI:
    """Create the FastAPI application around the existing Orchestrator."""

    app = FastAPI(
        title="Agentic BI Analyst API",
        version="1.0.0",
    )
    app.include_router(router)
    app.include_router(
        build_analysis_router(orchestrator or Orchestrator())
    )
    return app


app = create_app()

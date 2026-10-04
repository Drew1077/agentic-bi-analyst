from fastapi import APIRouter, HTTPException, status

from app.agents.orchestrator import Orchestrator
from app.api.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse, HealthResponse
from app.api.serialization import serialize_orchestrator_response


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return API process health."""

    return HealthResponse(status="ok")


def build_analysis_router(orchestrator: Orchestrator) -> APIRouter:
    """Build the analysis route bound to an Orchestrator instance."""

    analysis_router = APIRouter()

    @analysis_router.post(
        "/api/v1/analyze",
        response_model=AnalyzeResponse,
        responses={500: {"model": ErrorResponse}},
    )
    def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
        try:
            result = orchestrator.run(request.question)
            return serialize_orchestrator_response(result)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal analytical service error.",
            ) from exc

    return analysis_router

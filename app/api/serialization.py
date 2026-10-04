from fastapi.encoders import jsonable_encoder

from app.agents.orchestrator_models import OrchestratorResponse
from app.api.schemas import AnalyzeResponse


def serialize_orchestrator_response(
    response: OrchestratorResponse,
) -> AnalyzeResponse:
    """Adapt the existing Orchestrator contract into the API contract.

    This function only serializes the existing result. It does not calculate,
    reinterpret, or otherwise modify analytical content.
    """

    payload = jsonable_encoder(response)
    return AnalyzeResponse.model_validate(payload)

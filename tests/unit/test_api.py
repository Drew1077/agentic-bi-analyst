from fastapi.testclient import TestClient

from app.agents.orchestrator_models import (
    AgentResult,
    IntentType,
    OrchestratorResponse,
    Plan,
    PlanStep,
    StepStatus,
    WorkflowStatus,
)
from app.main import create_app


class FakeOrchestrator:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.questions = []

    def run(self, question):
        self.questions.append(question)
        if self.error:
            raise self.error
        return self.response


def successful_response():
    return OrchestratorResponse(
        success=True,
        answer="Revenue was 100000.",
        intent=IntentType.ANALYTICAL_QUERY,
        plan=Plan(
            plan_id="plan_1",
            status=WorkflowStatus.COMPLETED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    agent="sql_analyst",
                    action="answer analytical question",
                    status=StepStatus.COMPLETED,
                    input={"question": "What was revenue in 2025?"},
                )
            ],
        ),
        results={
            "step_1": AgentResult(
                agent_name="sql_analyst",
                success=True,
                output={"answer": "Revenue was 100000."},
                metadata={"row_count": 1},
            )
        },
        evidence={"row_count": 1},
        provenance={"source": "fake_sql_agent"},
        errors=[],
    )


def failed_response():
    return OrchestratorResponse(
        success=False,
        answer=None,
        intent=IntentType.ANALYTICAL_QUERY,
        plan=Plan(
            plan_id="plan_1",
            status=WorkflowStatus.FAILED,
        ),
        results={},
        evidence={},
        provenance={},
        errors=["SQL Analyst failed."],
    )


def test_health_endpoint():
    client = TestClient(create_app(FakeOrchestrator()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_success_preserves_structured_result():
    orchestrator = FakeOrchestrator(successful_response())
    client = TestClient(create_app(orchestrator))

    response = client.post(
        "/api/v1/analyze",
        json={"question": "What was revenue in 2025?"},
    )

    body = response.json()
    assert response.status_code == 200
    assert orchestrator.questions == ["What was revenue in 2025?"]
    assert body["success"] is True
    assert body["answer"] == "Revenue was 100000."
    assert body["intent"] == "analytical_query"
    assert body["plan"]["plan_id"] == "plan_1"
    assert body["results"]["step_1"]["agent_name"] == "sql_analyst"
    assert body["evidence"] == {"row_count": 1}
    assert body["provenance"] == {"source": "fake_sql_agent"}
    assert body["errors"] == []


def test_analyze_returns_controlled_analytical_failure():
    client = TestClient(create_app(FakeOrchestrator(failed_response())))

    response = client.post(
        "/api/v1/analyze",
        json={"question": "What was revenue in 2025?"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert body["answer"] is None
    assert body["errors"] == ["SQL Analyst failed."]


def test_analyze_rejects_missing_question():
    client = TestClient(create_app(FakeOrchestrator()))

    response = client.post("/api/v1/analyze", json={})

    assert response.status_code == 422


def test_analyze_rejects_empty_question():
    client = TestClient(create_app(FakeOrchestrator()))

    response = client.post(
        "/api/v1/analyze",
        json={"question": "   "},
    )

    assert response.status_code == 422
    assert "Question must not be empty" in response.text


def test_analyze_rejects_extra_request_fields():
    client = TestClient(create_app(FakeOrchestrator()))

    response = client.post(
        "/api/v1/analyze",
        json={
            "question": "revenue in 2025",
            "sql": "SELECT 1",
        },
    )

    assert response.status_code == 422


def test_analyze_hides_unexpected_internal_error():
    client = TestClient(
        create_app(FakeOrchestrator(error=RuntimeError("secret internal detail")))
    )

    response = client.post(
        "/api/v1/analyze",
        json={"question": "revenue in 2025"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal analytical service error."
    }
    assert "secret internal detail" not in response.text

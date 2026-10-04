from app.agents.orchestrator_models import (
    AgentResult,
    IntentType,
    OrchestratorResponse,
    OrchestratorState,
    Plan,
    PlanStep,
    StepStatus,
    WorkflowStatus,
)


def test_intent_type_values():
    assert IntentType.ANALYTICAL_QUERY.value == "analytical_query"
    assert IntentType.ROOT_CAUSE.value == "root_cause"
    assert IntentType.UNSUPPORTED.value == "unsupported"


def test_plan_step_defaults():
    step = PlanStep(
        step_id="step_1",
        agent="sql_analyst",
        action="answer analytical question",
    )

    assert step.status == StepStatus.PENDING
    assert step.input == {}
    assert step.result_reference is None


def test_plan_defaults():
    plan = Plan(plan_id="plan_1")

    assert plan.steps == []
    assert plan.status == WorkflowStatus.PENDING


def test_agent_result_defaults():
    result = AgentResult(
        agent_name="sql_analyst",
        success=True,
    )

    assert result.output is None
    assert result.errors == []
    assert result.metadata == {}


def test_orchestrator_state_defaults():
    state = OrchestratorState(
        question="revenue by category in 2025"
    )

    assert state.intent is None
    assert state.plan is None
    assert state.status == WorkflowStatus.PENDING
    assert state.current_step is None
    assert state.completed_steps == []
    assert state.agent_results == {}
    assert state.retry_count == 0
    assert state.max_retries == 1
    assert state.errors == []
    assert state.final_output is None


def test_orchestrator_response_contract():
    response = OrchestratorResponse(
        success=True,
        answer="Revenue was calculated successfully.",
        intent=IntentType.ANALYTICAL_QUERY,
        plan=None,
        results={},
        evidence={},
        provenance={},
        errors=[],
    )

    assert response.success is True
    assert response.intent == IntentType.ANALYTICAL_QUERY
    assert response.errors == []
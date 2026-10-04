from app.agents.orchestrator import Orchestrator
from app.agents.orchestrator_models import (
    IntentType,
    OrchestratorState,
    Plan,
    PlanStep,
    StepStatus,
    WorkflowStatus,
)



def test_validate_request_accepts_question():
    orchestrator = Orchestrator()

    errors = orchestrator.validate_request(
        "revenue by category in 2025"
    )

    assert errors == []


def test_validate_request_rejects_empty_question():
    orchestrator = Orchestrator()

    errors = orchestrator.validate_request("   ")

    assert errors == ["Question must not be empty."]


def test_classify_analytical_query():
    orchestrator = Orchestrator()

    intent = orchestrator.classify_intent(
        "revenue by category in 2025"
    )

    assert intent == IntentType.ANALYTICAL_QUERY


def test_classify_root_cause():
    orchestrator = Orchestrator()

    intent = orchestrator.classify_intent(
        "why did revenue decline in 2025?"
    )

    assert intent == IntentType.ROOT_CAUSE


def test_classify_trend():
    orchestrator = Orchestrator()

    intent = orchestrator.classify_intent(
        "show the revenue trend in 2025"
    )

    assert intent == IntentType.TREND


def test_classify_comparison():
    orchestrator = Orchestrator()

    intent = orchestrator.classify_intent(
        "compare revenue between 2024 and 2025"
    )

    assert intent == IntentType.COMPARISON


def test_plan_creates_sql_step_for_analytical_query():
    orchestrator = Orchestrator()

    state = orchestrator.plan(
        "revenue by category in 2025"
    )

    assert state.status == WorkflowStatus.PLANNING
    assert state.intent == IntentType.ANALYTICAL_QUERY
    assert state.plan is not None
    assert len(state.plan.steps) == 1

    step = state.plan.steps[0]

    assert step.agent == "sql_analyst"
    assert step.status == StepStatus.PENDING
    assert step.input["question"] == "revenue by category in 2025"


def test_plan_creates_root_cause_step():
    orchestrator = Orchestrator()

    state = orchestrator.plan(
        "why did revenue decline in 2025?"
    )

    assert state.status == WorkflowStatus.PLANNING
    assert state.intent == IntentType.ROOT_CAUSE
    assert state.plan is not None
    assert len(state.plan.steps) == 1

    step = state.plan.steps[0]

    assert step.agent == "root_cause"
    assert step.status == StepStatus.PENDING
    assert step.input["question"] == "why did revenue decline in 2025?"

class FakeSQLResponse:
    success = True
    answer = "Revenue was 100000."
    sql = "SELECT 100000 AS revenue"
    columns = ["revenue"]
    rows = [{"revenue": 100000}]
    evidence = {"row_count": 1}
    provenance = {"source": "fake_sql_agent"}
    errors = []


class FakeSQLAgent:
    def run(self, request):
        return FakeSQLResponse()

def test_execute_sql_step_success():
    orchestrator = Orchestrator(
        sql_agent=FakeSQLAgent()
    )

    state = OrchestratorState(
        question="What was the revenue in 2025?",
        intent=IntentType.ANALYTICAL_QUERY,
        status=WorkflowStatus.RUNNING,
    )

    step = PlanStep(
        step_id="step_1",
        agent="sql_analyst",
        action="answer analytical question",
        input={
            "question": "What was the revenue in 2025?"
        },
    )

    result = orchestrator.execute_step(
        state,
        step,
    )

    assert result.success is True
    assert result.agent_name == "sql_analyst"
    assert result.output.answer == "Revenue was 100000."
    assert result.metadata["row_count"] == 1


def test_run_sql_analyst_workflow_success():
    orchestrator = Orchestrator(
        sql_agent=FakeSQLAgent()
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is True
    assert response.intent == IntentType.ANALYTICAL_QUERY
    assert response.answer == "Revenue was 100000."
    assert response.plan.status == WorkflowStatus.COMPLETED
    assert response.plan.steps[0].status == StepStatus.COMPLETED
    assert "step_1" in response.results

class FailingSQLResponse:
    success = False
    answer = None
    sql = None
    columns = []
    rows = []
    evidence = {}
    provenance = {}
    errors = ["SQL Analyst failed."]


class FailingSQLAgent:
    def run(self, request):
        return FailingSQLResponse()

def test_run_stops_when_sql_analyst_fails():
    orchestrator = Orchestrator(
        sql_agent=FailingSQLAgent()
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is False
    assert response.answer is None
    assert response.plan.status == WorkflowStatus.FAILED
    assert response.plan.steps[0].status == StepStatus.FAILED
    assert "SQL Analyst failed." in response.errors

class RetrySQLAgent:
    def __init__(self):
        self.calls = 0

    def run(self, request):
        self.calls += 1

        if self.calls == 1:
            return FailingSQLResponse()

        return FakeSQLResponse()


def test_run_retries_failed_sql_analyst_once():
    sql_agent = RetrySQLAgent()

    orchestrator = Orchestrator(
        sql_agent=sql_agent
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is True
    assert response.answer == "Revenue was 100000."
    assert sql_agent.calls == 2

def test_run_fails_after_retry_limit():
    sql_agent = FailingSQLAgent()

    orchestrator = Orchestrator(
        sql_agent=sql_agent
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is False
    assert response.answer is None
    assert response.plan.status == WorkflowStatus.FAILED
    assert response.plan.steps[0].status == StepStatus.FAILED
    assert response.errors.count("SQL Analyst failed.") == 2

def test_run_stops_when_plan_has_no_steps():
    orchestrator = Orchestrator(
        sql_agent=FakeSQLAgent()
    )

    response = orchestrator.run(
        "What is the weather today?"
    )

    assert response.success is False
    assert response.answer is None
    assert response.intent == IntentType.AMBIGUOUS
    assert response.plan is not None
    assert response.errors

def test_run_preserves_sql_evidence_and_provenance():
    orchestrator = Orchestrator(
        sql_agent=FakeSQLAgent()
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is True
    assert response.evidence == {
        "row_count": 1
    }
    assert response.provenance == {
        "source": "fake_sql_agent"
    }

def test_multi_step_plan_executes_steps_sequentially():
    orchestrator = Orchestrator(
        sql_agent=FakeSQLAgent()
    )

    state = OrchestratorState(
        question="What was the revenue in 2025?",
        intent=IntentType.MULTI_STEP,
        status=WorkflowStatus.RUNNING,
        plan=Plan(
            plan_id="multi_step_plan",
            status=WorkflowStatus.RUNNING,
            steps=[
                PlanStep(
                    step_id="step_1",
                    agent="sql_analyst",
                    action="answer analytical question",
                    input={
                        "question": "What was the revenue in 2025?"
                    },
                ),
                PlanStep(
                    step_id="step_2",
                    agent="sql_analyst",
                    action="answer analytical question",
                    input={
                        "question": "What was the revenue in 2025?"
                    },
                ),
            ],
        ),
    )

    for step in state.plan.steps:
        step.status = StepStatus.RUNNING

        result = orchestrator.execute_step(
            state,
            step,
        )

        state.agent_results[step.step_id] = result

        if result.success:
            step.status = StepStatus.COMPLETED
            state.completed_steps.append(step.step_id)

    assert len(state.completed_steps) == 2
    assert state.completed_steps == [
        "step_1",
        "step_2",
    ]
    assert state.agent_results["step_1"].success is True
    assert state.agent_results["step_2"].success is True

class TrackingSQLAgent:
    def __init__(self):
        self.calls = 0

    def run(self, request):
        self.calls += 1
        return FakeSQLResponse()


def test_ambiguous_request_does_not_call_sql_analyst():
    sql_agent = TrackingSQLAgent()

    orchestrator = Orchestrator(
        sql_agent=sql_agent
    )

    response = orchestrator.run(
        "Tell me something interesting."
    )

    assert response.success is False
    assert response.intent == IntentType.AMBIGUOUS
    assert sql_agent.calls == 0

class FakeRootCauseResponse:
    success = True
    answer = "Revenue decreased by 8.4% because Accessories contributed 62% of the decline."
    findings = [
        {
            "type": "evidence_backed",
            "statement": "Accessories contributed 62% of the decline.",
            "supporting_evidence": [
                {
                    "type": "contribution",
                    "dimension": "category",
                    "group": "Accessories",
                    "contribution_percentage": 62.0,
                }
            ],
        }
    ]
    evidence = [
        {
            "type": "comparison",
            "metric": "net_revenue",
            "percentage_change": -8.4,
        }
    ]
    provenance = [
        {
            "agent": "root_cause_agent",
            "source": "fake_root_cause_agent",
        }
    ]
    errors = []


class FakeRootCauseAgent:
    def run(self, request):
        return FakeRootCauseResponse()


def test_execute_root_cause_step_success(monkeypatch):
    monkeypatch.setattr(
        "app.agents.orchestrator.RootCauseAgent",
        FakeRootCauseAgent,
    )

    orchestrator = Orchestrator()

    state = OrchestratorState(
        question="why did revenue decline in 2025?",
        intent=IntentType.ROOT_CAUSE,
        status=WorkflowStatus.RUNNING,
    )

    step = PlanStep(
        step_id="step_1",
        agent="root_cause",
        action="analyze root cause",
        input={
            "question": "why did revenue decline in 2025?"
        },
    )

    result = orchestrator.execute_step(
        state,
        step,
    )

    assert result.success is True
    assert result.agent_name == "root_cause"
    assert result.output.answer == (
        "Revenue decreased by 8.4% because Accessories "
        "contributed 62% of the decline."
    )
    assert result.metadata["finding_count"] == 1
    assert result.metadata["evidence_count"] == 1

def test_run_root_cause_workflow_success(monkeypatch):
    monkeypatch.setattr(
        "app.agents.orchestrator.RootCauseAgent",
        FakeRootCauseAgent,
    )

    orchestrator = Orchestrator()

    response = orchestrator.run(
        "why did revenue decline in 2025?"
    )

    assert response.success is True
    assert response.intent == IntentType.ROOT_CAUSE
    assert response.answer == (
        "Revenue decreased by 8.4% because Accessories "
        "contributed 62% of the decline."
    )
    assert response.plan.status == WorkflowStatus.COMPLETED
    assert response.plan.steps[0].status == StepStatus.COMPLETED
    assert "step_1" in response.results

class FailingRootCauseResponse:
    success = False
    answer = None
    findings = []
    evidence = []
    provenance = []
    errors = ["Root-Cause Agent failed."]


class FailingRootCauseAgent:
    def run(self, request):
        return FailingRootCauseResponse()


def test_run_stops_when_root_cause_agent_fails(monkeypatch):
    monkeypatch.setattr(
        "app.agents.orchestrator.RootCauseAgent",
        FailingRootCauseAgent,
    )

    orchestrator = Orchestrator()

    response = orchestrator.run(
        "why did revenue decline in 2025?"
    )

    assert response.success is False
    assert response.answer is None
    assert response.intent == IntentType.ROOT_CAUSE
    assert response.plan.status == WorkflowStatus.FAILED
    assert response.plan.steps[0].status == StepStatus.FAILED
    assert "Root-Cause Agent failed." in response.errors

class FakeCriticResponse:
    success = True
    passed = True
    issues = []
    checks = [
        {
            "name": "result_exists",
            "passed": True,
        }
    ]
    provenance = [
        {
            "agent": "critic_agent",
            "source": "fake_critic",
        }
    ]
    errors = []


class FakeCriticAgent:
    def __init__(self):
        self.calls = 0

    def run(self, request):
        self.calls += 1
        return FakeCriticResponse()


def test_run_passes_successful_result_through_critic():
    critic_agent = FakeCriticAgent()

    orchestrator = Orchestrator(
        sql_agent=FakeSQLAgent(),
        critic_agent=critic_agent,
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is True
    assert critic_agent.calls == 1
    assert response.plan.status == WorkflowStatus.COMPLETED

    result = response.results["step_1"]

    assert result.success is True
    assert result.metadata["critic"]["passed"] is True


class RejectingCriticResponse:
    success = True
    passed = False
    issues = [
        "Critic rejected the analytical result."
    ]
    checks = [
        {
            "name": "result_consistency",
            "passed": False,
        }
    ]
    provenance = [
        {
            "agent": "critic_agent",
            "source": "rejecting_fake_critic",
        }
    ]
    errors = []


class RejectingCriticAgent:
    def __init__(self):
        self.calls = 0

    def run(self, request):
        self.calls += 1
        return RejectingCriticResponse()


class RetryThenPassingCriticAgent:
    def __init__(self):
        self.calls = 0

    def run(self, request):
        self.calls += 1

        if self.calls == 1:
            return RejectingCriticResponse()

        return FakeCriticResponse()


def test_run_retries_when_critic_rejects_result():
    sql_agent = FakeSQLAgent()
    critic_agent = RetryThenPassingCriticAgent()

    orchestrator = Orchestrator(
        sql_agent=sql_agent,
        critic_agent=critic_agent,
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is True
    assert critic_agent.calls == 2
    assert response.plan.status == WorkflowStatus.COMPLETED
    assert response.answer == "Revenue was 100000."


def test_run_fails_when_critic_rejects_after_retry():
    critic_agent = RejectingCriticAgent()

    orchestrator = Orchestrator(
        sql_agent=FakeSQLAgent(),
        critic_agent=critic_agent,
    )

    response = orchestrator.run(
        "What was the revenue in 2025?"
    )

    assert response.success is False
    assert critic_agent.calls == 2
    assert response.plan.status == WorkflowStatus.FAILED
    assert response.errors.count(
        "Critic rejected the analytical result."
    ) == 2
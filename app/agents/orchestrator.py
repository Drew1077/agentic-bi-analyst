import logging
import time
import base64

from app.agents.sql_agent import SQLAgentRequest, SQLAnalystAgent
from app.agents.root_cause_agent import (
    RootCauseAgent,
    RootCauseAgentRequest,
)
from app.agents.critic_agent import (
    CriticAgent,
    CriticAgentRequest,
)
from app.agents.observability import (
    finish_run,
    record_step,
    start_run,
)
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
from app.agents.visualization_agent import (
    VisualizationAgent,
    VisualizationAgentRequest,
)


logger = logging.getLogger("agentic_bi_analyst.orchestrator")


class Orchestrator:
    """Workflow manager for routing analytical requests to agents."""

    REGISTERED_AGENTS = {
        "sql_analyst",
        "root_cause",
        "visualization",
    }

    def __init__(
        self,
        sql_agent=None,
        critic_agent=None,
        visualization_agent=None,
    ):
        self.sql_agent = sql_agent
        self.critic_agent = critic_agent
        self.visualization_agent = visualization_agent

    def validate_request(self, question: str) -> list[str]:
        """Validate the basic orchestrator request."""

        errors = []

        if not isinstance(question, str):
            errors.append("Question must be a string.")
            return errors

        if not question.strip():
            errors.append("Question must not be empty.")

        return errors

    def classify_intent(self, question: str) -> IntentType:
        """Classify a question into a controlled workflow intent."""

        normalized = question.strip().lower()

        if not normalized:
            return IntentType.AMBIGUOUS

        root_cause_terms = (
            "why did",
            "why has",
            "why have",
            "reason for",
            "root cause",
            "what caused",
        )

        anomaly_terms = (
            "anomaly",
            "anomalies",
            "unusual",
            "unusually",
            "outlier",
            "outliers",
        )

        trend_terms = (
            "trend",
            "over time",
            "month over month",
            "monthly trend",
            "year over year",
        )

        comparison_terms = (
            "compare",
            "comparison",
            "versus",
            "vs ",
            "against",
            "difference between",
        )

        ranking_terms = (
            "top ",
            "bottom ",
            "highest",
            "lowest",
            "rank",
            "ranking",
        )

        drill_down_terms = (
            "drill down",
            "drilldown",
            "break down further",
            "breakdown",
        )

        multi_step_terms = (
            "and then",
            "followed by",
            "after that",
            "step by step",
        )

        if any(term in normalized for term in root_cause_terms):
            return IntentType.ROOT_CAUSE

        if any(term in normalized for term in anomaly_terms):
            return IntentType.ANOMALY

        if any(term in normalized for term in multi_step_terms):
            return IntentType.MULTI_STEP

        if any(term in normalized for term in drill_down_terms):
            return IntentType.DRILL_DOWN

        if any(term in normalized for term in trend_terms):
            return IntentType.TREND

        if any(term in normalized for term in comparison_terms):
            return IntentType.COMPARISON

        if any(term in normalized for term in ranking_terms):
            return IntentType.RANKING

        analytical_terms = (
            "revenue",
            "sales",
            "profit",
            "margin",
            "orders",
            "units",
            "customers",
            "inventory",
            "stock",
            "returns",
            "refund",
            "discount",
            "aov",
            "average",
        )

        if any(term in normalized for term in analytical_terms):
            return IntentType.ANALYTICAL_QUERY

        return IntentType.AMBIGUOUS

    def create_plan(
        self,
        intent: IntentType,
        question: str,
    ) -> Plan:
        """Create a controlled execution plan for the classified intent."""

        plan = Plan(
            plan_id="plan_1",
            status=WorkflowStatus.PENDING,
        )

        if intent == IntentType.ANALYTICAL_QUERY:
            plan.steps.append(
                PlanStep(
                    step_id="step_1",
                    agent="sql_analyst",
                    action="answer analytical question",
                    status=StepStatus.PENDING,
                    input={"question": question},
                )
            )

        if intent == IntentType.ROOT_CAUSE:
            plan.steps.append(
                PlanStep(
                    step_id="step_1",
                    agent="root_cause",
                    action="analyze root cause",
                    status=StepStatus.PENDING,
                    input={"question": question},
                )
            )

        return plan

    def execute_step(
        self,
        state: OrchestratorState,
        step: PlanStep,
    ) -> AgentResult:
        """Execute one supported plan step."""

        if step.agent not in self.REGISTERED_AGENTS:
            return AgentResult(
                agent_name=step.agent,
                success=False,
                errors=[
                    f"Agent is not registered: {step.agent}"
                ],
            )

        if step.agent == "sql_analyst":
            question = step.input.get("question")

            if not isinstance(question, str) or not question.strip():
                return AgentResult(
                    agent_name="sql_analyst",
                    success=False,
                    errors=[
                        "SQL Analyst step requires a non-empty question."
                    ],
                )

            if self.sql_agent is None:
                self.sql_agent = SQLAnalystAgent()

            response = self.sql_agent.run(
                SQLAgentRequest(question=question)
            )

            return AgentResult(
                agent_name="sql_analyst",
                success=response.success,
                output=response,
                errors=response.errors,
                metadata={
                    "sql": response.sql,
                    "columns": response.columns,
                    "row_count": len(response.rows),
                },
            )

        if step.agent == "root_cause":
            question = step.input.get("question")

            if not isinstance(question, str) or not question.strip():
                return AgentResult(
                    agent_name="root_cause",
                    success=False,
                    errors=[
                        "Root-Cause step requires a non-empty question."
                    ],
                )

            root_cause_agent = RootCauseAgent()

            response = root_cause_agent.run(
                RootCauseAgentRequest(
                    question=question
                )
            )

            return AgentResult(
                agent_name="root_cause",
                success=response.success,
                output=response,
                errors=response.errors,
                metadata={
                    "finding_count": len(response.findings),
                    "evidence_count": len(response.evidence),
                },
            )

        return AgentResult(
            agent_name=step.agent,
            success=False,
            errors=[
                f"No execution handler exists for agent: {step.agent}"
            ],
        )

    def validate_result(
        self,
        state: OrchestratorState,
        result: AgentResult,
    ) -> AgentResult:
        """Validate a successful agent result through the Critic Agent."""

        if not result.success:
            return result

        if self.critic_agent is None:
            self.critic_agent = CriticAgent()

        critic_response = self.critic_agent.run(
            CriticAgentRequest(
                question=state.question,
                result=result.output,
            )
        )

        result.metadata["critic"] = {
            "passed": critic_response.passed,
            "issues": critic_response.issues,
            "checks": critic_response.checks,
        }

        if not critic_response.success:
            result.success = False
            result.errors.extend(critic_response.errors)
            return result

        if not critic_response.passed:
            result.success = False
            result.errors = list(critic_response.issues)

        return result

    def run(self, question: str) -> OrchestratorResponse:
        """Run the orchestrator workflow for a user question."""

        trace = start_run(question if isinstance(question, str) else str(question))
        state = self.plan(question)
        state.run_id = trace["run_id"]
        state.observability = trace
        logger.info("analysis_run_started run_id=%s", trace["run_id"])

        def failure_response() -> OrchestratorResponse:
            public_trace = finish_run(
                trace,
                status=state.status.value,
                success=False,
                answer=None,
                errors=state.errors,
            )
        
            return OrchestratorResponse(
                success=False, answer=None, intent=state.intent, plan=state.plan,
                results=state.agent_results, evidence={}, provenance={},
                errors=state.errors, run_id=trace["run_id"],
                observability=public_trace,
                
            )

        if state.status != WorkflowStatus.PLANNING:
            return failure_response()
        if state.plan is None or not state.plan.steps:
            state.status = WorkflowStatus.STOPPED
            state.errors.append("No executable plan was created.")
            return failure_response()

        state.status = WorkflowStatus.RUNNING
        state.plan.status = WorkflowStatus.RUNNING

        for step in state.plan.steps:
            state.current_step = step.step_id
            while True:
                step.status = StepStatus.RUNNING
                step_started = time.perf_counter()
                result = self.execute_step(state, step)

                if result.success:
                    result = self.validate_result(state, result)

                state.agent_results[step.step_id] = result
                record_step(
                    trace, step_id=step.step_id, agent=step.agent,
                    status="completed" if result.success else "failed",
                    duration_ms=(time.perf_counter() - step_started) * 1000,
                    metadata=result.metadata, errors=result.errors,
                )

                if result.success:
                    step.status = StepStatus.COMPLETED
                    state.completed_steps.append(step.step_id)
                    break

                step.status = StepStatus.FAILED
                state.errors.extend(result.errors)
                if state.retry_count < state.max_retries:
                    state.retry_count += 1
                    trace["retries"] = state.retry_count
                    state.status = WorkflowStatus.RETRYING
                    state.plan.status = WorkflowStatus.RETRYING
                    continue

                state.status = WorkflowStatus.FAILED
                state.plan.status = WorkflowStatus.FAILED
                return failure_response()

        state.status = WorkflowStatus.COMPLETED
        state.plan.status = WorkflowStatus.COMPLETED
        final_result = state.agent_results[state.completed_steps[-1]]
        final_output = final_result.output

        if hasattr(final_output, "answer"):
            answer = final_output.answer
        elif isinstance(final_output, str):
            answer = final_output
        else:
            answer = str(final_output)

        evidence = final_output.evidence if hasattr(final_output, "evidence") else {}
        provenance = final_output.provenance if hasattr(final_output, "provenance") else {}
        state.final_output = answer
        visualization = None

        if final_result.agent_name == "sql_analyst" and final_result.success:
            if self.visualization_agent is None:
                self.visualization_agent = VisualizationAgent()

            visualization_started = time.perf_counter()

            visualization_response = self.visualization_agent.run(
                VisualizationAgentRequest(
                    question=state.question,
                    result=final_output,
                )
            )

            rendered_chart_base64 = None

            if visualization_response.rendered_chart is not None:
                rendered_chart_base64 = base64.b64encode(
                    visualization_response.rendered_chart
                ).decode("ascii")

            visualization = {
                "success": visualization_response.success,
                "chart_spec": visualization_response.chart_spec,
                "rendered_chart_base64": rendered_chart_base64,
                "chart_format": visualization_response.chart_format,
                "validation": visualization_response.validation,
                "errors": visualization_response.errors,
            }

            record_step(
                trace,
                step_id="visualization",
                agent="visualization_agent",
                status=(
                    "completed"
                    if visualization_response.success
                    else "failed"
                ),
                duration_ms=(
                    time.perf_counter() - visualization_started
                ) * 1000,
                metadata={
                    "chart_type": (
                        visualization_response.chart_spec or {}
                    ).get("chart_type"),
                    "rendered": (
                        visualization_response.rendered_chart is not None
                    ),
                },
                errors=visualization_response.errors,
            )
        public_trace = finish_run(
            trace, status=state.status.value, success=True,
            answer=answer, errors=[],
        )

        return OrchestratorResponse(
            success=True, answer=answer, intent=state.intent, plan=state.plan,
            results=state.agent_results, evidence=evidence, provenance=provenance,
            errors=[], run_id=trace["run_id"], observability=public_trace,
            visualization=visualization,
        )

    def plan(self, question: str) -> OrchestratorState:
        """Validate, classify, and create an initial workflow state."""

        request_errors = self.validate_request(question)

        if request_errors:
            return OrchestratorState(
                question=question
                if isinstance(question, str)
                else str(question),
                status=WorkflowStatus.FAILED,
                errors=request_errors,
            )

        intent = self.classify_intent(question)

        state = OrchestratorState(
            question=question,
            intent=intent,
            status=WorkflowStatus.PLANNING,
        )

        if intent in {
            IntentType.ANALYTICAL_QUERY,
            IntentType.ROOT_CAUSE,
        }:
            state.plan = self.create_plan(
                intent,
                question,
            )
            return state

        state.plan = self.create_plan(
            intent,
            question,
        )

        state.status = WorkflowStatus.STOPPED
        state.errors.append(
            f"No registered agent is available for intent: {intent.value}"
        )

        return state
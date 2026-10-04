from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    """Controlled analytical intent categories."""

    ANALYTICAL_QUERY = "analytical_query"
    COMPARISON = "comparison"
    TREND = "trend"
    RANKING = "ranking"
    DRILL_DOWN = "drill_down"
    ROOT_CAUSE = "root_cause"
    ANOMALY = "anomaly"
    MULTI_STEP = "multi_step"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


class StepStatus(str, Enum):
    """Lifecycle status of an individual plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """Lifecycle status of the complete orchestrator workflow."""

    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class PlanStep:
    """One executable step in an orchestrator plan."""

    step_id: str
    agent: str
    action: str
    status: StepStatus = StepStatus.PENDING
    input: dict[str, Any] = field(default_factory=dict)
    result_reference: str | None = None


@dataclass
class Plan:
    """Structured execution plan produced by the orchestrator."""

    plan_id: str
    steps: list[PlanStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING


@dataclass
class AgentResult:
    """Normalized record of an agent execution result."""

    agent_name: str
    success: bool
    output: Any = None
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorState:
    """Runtime state of the complete orchestrator workflow."""

    question: str
    intent: IntentType | None = None
    plan: Plan | None = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str | None = None
    completed_steps: list[str] = field(default_factory=list)
    agent_results: dict[str, AgentResult] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 1
    errors: list[str] = field(default_factory=list)
    final_output: Any = None


@dataclass
class OrchestratorResponse:
    """Output contract for the Orchestrator."""

    success: bool
    answer: str | None
    intent: IntentType | None
    plan: Plan | None
    results: dict[str, AgentResult]
    evidence: dict[str, Any]
    provenance: dict[str, Any]
    errors: list[str]
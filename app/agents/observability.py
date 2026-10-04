"""Lightweight run-level observability for the BI workflow."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

logger = logging.getLogger("agentic_bi_analyst.orchestrator")


def new_run_id() -> str:
    return uuid.uuid4().hex


def start_run(question: str) -> dict[str, Any]:
    return {
        "run_id": new_run_id(),
        "question": question,
        "started_at_monotonic": time.perf_counter(),
        "agent_sequence": [],
        "steps": [],
        "retries": 0,
        "errors": [],
    }


def record_step(trace: dict[str, Any], *, step_id: str, agent: str, status: str,
                duration_ms: float, metadata: dict[str, Any] | None = None,
                errors: list[str] | None = None) -> None:
    trace["agent_sequence"].append(agent)
    trace["steps"].append({
        "step_id": step_id,
        "agent": agent,
        "status": status,
        "duration_ms": round(duration_ms, 3),
        "metadata": metadata or {},
        "errors": list(errors or []),
    })


def finish_run(trace: dict[str, Any], *, status: str, success: bool,
               answer: str | None, errors: list[str]) -> dict[str, Any]:
    trace["status"] = status
    trace["success"] = success
    trace["answer_present"] = answer is not None
    trace["errors"] = list(errors)
    trace["duration_ms"] = round(
        (time.perf_counter() - trace.pop("started_at_monotonic")) * 1000, 3
    )
    public = dict(trace)
    logger.info(
        "analysis_run_completed run_id=%s status=%s success=%s duration_ms=%s retries=%s",
        public["run_id"], public["status"], public["success"],
        public["duration_ms"], public["retries"],
    )
    return public

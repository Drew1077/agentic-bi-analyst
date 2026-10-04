from app.agents.observability import finish_run, record_step, start_run


def test_start_run_creates_trace_metadata():
    trace = start_run("revenue in 2025")

    assert trace["run_id"]
    assert len(trace["run_id"]) == 32
    assert trace["question"] == "revenue in 2025"
    assert trace["agent_sequence"] == []
    assert trace["retries"] == 0


def test_record_step_captures_agent_timing_metadata():
    trace = start_run("revenue in 2025")

    record_step(
        trace,
        step_id="step_1",
        agent="sql_analyst",
        status="completed",
        duration_ms=12.3456,
        metadata={"row_count": 1},
    )

    assert trace["agent_sequence"] == ["sql_analyst"]
    assert trace["steps"] == [
        {
            "step_id": "step_1",
            "agent": "sql_analyst",
            "status": "completed",
            "duration_ms": 12.346,
            "metadata": {"row_count": 1},
            "errors": [],
        }
    ]


def test_finish_run_returns_public_trace_without_monotonic_clock_value():
    trace = start_run("revenue in 2025")
    result = finish_run(
        trace,
        status="completed",
        success=True,
        answer="Revenue was 100000.",
        errors=[],
    )

    assert result["status"] == "completed"
    assert result["success"] is True
    assert result["answer_present"] is True
    assert result["duration_ms"] >= 0
    assert "started_at_monotonic" not in result

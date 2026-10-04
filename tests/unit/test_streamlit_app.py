from unittest.mock import MagicMock, patch


import pytest

from app.ui.streamlit_app import (
    ANALYZE_PATH,
    ApiResult,
    build_analyze_url,
    normalize_api_base_url,
    render_analysis,
    validate_question,
)

@pytest.fixture
def mock_streamlit():
    with patch("app.ui.streamlit_app.st") as mock:
        expander = MagicMock()
        mock.expander.return_value.__enter__.return_value = expander
        yield mock


def test_normalize_api_base_url_removes_whitespace_and_trailing_slash():
    assert normalize_api_base_url("  http://localhost:8000/// ") == (
        "http://localhost:8000"
    )


def test_build_analyze_url():
    assert build_analyze_url("http://localhost:8000/") == (
        f"http://localhost:8000{ANALYZE_PATH}"
    )


def test_validate_question_accepts_normal_question():
    assert validate_question("What was the revenue in 2025?") is None


def test_validate_question_rejects_empty_question():
    assert validate_question("   ") == "Please enter an analytical question."


def test_validate_question_rejects_question_over_4000_characters():
    error = validate_question("x" * 4001)

    assert error == "The question must be 4000 characters or fewer."


@patch("app.ui.streamlit_app.urlopen")
def test_analyze_question_constructs_expected_api_request(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = (
        b'{"success":true,"answer":"Revenue was 100.","intent":"revenue",'
        b'"plan":{},"results":{},"evidence":{},"provenance":{},"errors":[]}'
    )
    mock_urlopen.return_value.__enter__.return_value = mock_response

    from app.ui.streamlit_app import analyze_question

    result = analyze_question(
        "http://localhost:8000",
        "What was the revenue in 2025?",
    )

    assert result.ok is True
    assert result.status_code == 200
    assert result.data["success"] is True

    request = mock_urlopen.call_args.args[0]

    assert request.full_url == "http://localhost:8000/api/v1/analyze"
    assert request.method == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert request.data == (
        b'{"question": "What was the revenue in 2025?"}'
    )


@patch("app.ui.streamlit_app.urlopen")
def test_analyze_question_handles_api_failure(mock_urlopen):
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        url="http://localhost:8000/api/v1/analyze",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    from app.ui.streamlit_app import analyze_question

    result = analyze_question(
        "http://localhost:8000",
        "What was the revenue in 2025?",
    )

    assert result.ok is False
    assert result.status_code == 500
    assert result.data is None
    assert result.error == "The analytical service is temporarily unavailable."


@patch("app.ui.streamlit_app.urlopen")
def test_analyze_question_handles_network_failure(mock_urlopen):
    from urllib.error import URLError

    mock_urlopen.side_effect = URLError("connection refused")

    from app.ui.streamlit_app import analyze_question

    result = analyze_question(
        "http://localhost:8000",
        "What was the revenue in 2025?",
    )

    assert result.ok is False
    assert result.status_code is None
    assert result.data is None
    assert result.error == "Could not connect to the analytical API."


def test_render_analysis_success(mock_streamlit):
    response = {
        "success": True,
        "answer": "Revenue was 100.",
        "intent": "revenue",
        "plan": {"step": "calculate revenue"},
        "results": {"revenue": 100},
        "evidence": {"source": "orders"},
        "provenance": {"tool": "sql_analyst"},
        "errors": [],
    }

    render_analysis(response)

    mock_streamlit.success.assert_called_once_with("Analysis completed.")
    mock_streamlit.subheader.assert_any_call("Answer")


def test_render_analysis_controlled_failure(mock_streamlit):
    response = {
        "success": False,
        "answer": None,
        "intent": "revenue",
        "plan": None,
        "results": {},
        "evidence": {},
        "provenance": {},
        "errors": ["Insufficient data."],
    }

    render_analysis(response)

    mock_streamlit.warning.assert_called_once_with(
        "The analysis could not be completed."
    )
    mock_streamlit.error.assert_any_call("Insufficient data.")


def test_api_result_dataclass():
    result = ApiResult(
        ok=True,
        status_code=200,
        data={"success": True},
        error=None,
    )

    assert result.ok is True
    assert result.status_code == 200
    assert result.data == {"success": True}
    assert result.error is None
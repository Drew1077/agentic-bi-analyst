"""Streamlit UI for the Agentic BI Analyst FastAPI service."""

from __future__ import annotations
import base64
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st



DEFAULT_API_BASE_URL = os.getenv("AGENTIC_BI_API_BASE_URL", "http://127.0.0.1:8000")
ANALYZE_PATH = "/api/v1/analyze"
REQUEST_TIMEOUT_SECONDS = 60


@dataclass
class ApiResult:
    """Result returned by the UI API client."""

    ok: bool
    status_code: int | None
    data: dict[str, Any] | None
    error: str | None


def normalize_api_base_url(base_url: str) -> str:
    """Normalize a configured API base URL."""

    return base_url.strip().rstrip("/")


def build_analyze_url(base_url: str) -> str:
    """Build the analyze endpoint URL."""

    return f"{normalize_api_base_url(base_url)}{ANALYZE_PATH}"


def validate_question(question: str) -> str | None:
    """Validate UI input before making an API request."""

    if not question.strip():
        return "Please enter an analytical question."

    if len(question) > 4000:
        return "The question must be 4000 characters or fewer."

    return None


def analyze_question(
    base_url: str,
    question: str,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> ApiResult:
    """Call the FastAPI analyze endpoint without performing analysis locally."""

    payload = json.dumps({"question": question}).encode("utf-8")

    request = Request(
        build_analyze_url(base_url),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
            data = json.loads(raw_body)

            if not isinstance(data, dict):
                return ApiResult(
                    ok=False,
                    status_code=response.status,
                    data=None,
                    error="The API returned an unexpected response format.",
                )

            return ApiResult(
                ok=True,
                status_code=response.status,
                data=data,
                error=None,
            )

    except HTTPError as exc:
        if exc.code == 422:
            message = "The API rejected the request. Please check the question."
        elif exc.code >= 500:
            message = "The analytical service is temporarily unavailable."
        else:
            message = f"The API request failed with status {exc.code}."

        return ApiResult(
            ok=False,
            status_code=exc.code,
            data=None,
            error=message,
        )

    except (URLError, TimeoutError):
        return ApiResult(
            ok=False,
            status_code=None,
            data=None,
            error="Could not connect to the analytical API.",
        )

    except (json.JSONDecodeError, UnicodeDecodeError):
        return ApiResult(
            ok=False,
            status_code=None,
            data=None,
            error="The API returned an invalid response.",
        )

    except OSError:
        return ApiResult(
            ok=False,
            status_code=None,
            data=None,
            error="Could not communicate with the analytical API.",
        )


def render_value(value: Any) -> None:
    """Render an API-provided value without changing its analytical meaning."""

    if isinstance(value, (dict, list)):
        st.json(value)
    elif value is None:
        st.caption("No data provided.")
    else:
        st.write(value)


def render_analysis(response: dict[str, Any]) -> None:
    """Render the structured API response."""

    success = response.get("success", False)

    if success:
        st.success("Analysis completed.")
    else:
        st.warning("The analysis could not be completed.")

    answer = response.get("answer")

    st.subheader("Answer")
    if answer:
        st.write(answer)
    else:
        st.caption("No answer was returned by the analytical service.")

    if not success:
        errors = response.get("errors") or []
        if errors:
            st.subheader("Errors")
            for error in errors:
                st.error(str(error))

    visualization = response.get("visualization")

    if isinstance(visualization, dict):
        chart_type = (
            (visualization.get("chart_spec") or {})
            .get("chart_type")
        )

        chart_data = visualization.get("rendered_chart_base64")

        if chart_type and chart_type != "none" and chart_data:
            try:
                chart_bytes = base64.b64decode(chart_data)

                st.subheader("Visualization")

                st.image(
                    chart_bytes,
                    caption=f"{chart_type.title()} chart",
                    use_container_width=True,
                )

            except (ValueError, TypeError):
                st.warning(
                    "The visualization artifact could not be rendered."
                )

    with st.expander("Analysis details"):
        st.markdown("**Intent**")
        render_value(response.get("intent"))

        st.markdown("**Plan**")
        render_value(response.get("plan"))

        st.markdown("**Results**")
        render_value(response.get("results"))

    with st.expander("Evidence"):
        render_value(response.get("evidence"))

    with st.expander("Provenance"):
        render_value(response.get("provenance"))


def main() -> None:
    """Run the Streamlit application."""

    st.set_page_config(
        page_title="Agentic BI Analyst",
        page_icon="📊",
        layout="wide",
    )

    st.title("Agentic BI Analyst")
    st.caption(
        "Ask a business question and receive an evidence-backed analysis "
        "through the Agentic BI Analyst API."
    )

    with st.sidebar:
        st.header("API Configuration")
        api_base_url = st.text_input(
            "API base URL",
            value=DEFAULT_API_BASE_URL,
            help="Base URL of the running FastAPI service.",
        )

        st.divider()
        st.caption("The UI communicates only with the FastAPI analysis endpoint.")

    st.subheader("Ask a business question")

    question = st.text_area(
        "Analytical question",
        placeholder="Example: What was the revenue by category in 2025?",
        height=120,
    )

    analyze_clicked = st.button(
        "Analyze",
        type="primary",
        use_container_width=True,
    )

    if not analyze_clicked:
        return

    validation_error = validate_question(question)

    if validation_error:
        st.warning(validation_error)
        return

    with st.spinner("Analyzing your question..."):
        result = analyze_question(api_base_url, question)

    if not result.ok:
        st.error(result.error or "The analytical request failed.")
        return

    if result.data is None:
        st.error("The API returned no analysis data.")
        return

    render_analysis(result.data)


if __name__ == "__main__":
    main()
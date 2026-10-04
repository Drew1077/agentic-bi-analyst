# FastAPI API Contract

## Purpose

The FastAPI layer is a thin adapter around the existing Agentic BI Analyst
Orchestrator. It validates HTTP input, delegates analytical execution to the
existing Orchestrator, and serializes the Orchestrator's structured result into
JSON. It does not perform analytical computation itself.

## Endpoints

### `GET /health`

Returns a lightweight process-health response.

Successful response:

```json
{"status": "ok"}
```

### `POST /api/v1/analyze`

Accepts one analytical question and delegates it to the existing Orchestrator.

Request:

```json
{"question": "What was the revenue in 2025?"}
```

`question` must be a non-empty string after trimming whitespace and is limited
to 4000 characters. Unknown request fields are rejected.

Successful or controlled analytical responses use the existing Orchestrator
contract:

- `success`
- `answer`
- `intent`
- `plan`
- `results`
- `evidence`
- `provenance`
- `errors`

The API serialization layer converts the existing dataclass/enumeration
objects into JSON-safe structures without recalculating or redefining their
contents.

## Analytical failures

A controlled analytical failure from the Orchestrator is returned as the same
structured response contract with `success: false`, a nullable `answer`, and
its existing `errors`. The API does not fabricate an answer or convert a
controlled analytical failure into a fake success.

## Request validation errors

Malformed requests, missing required fields, empty questions, and forbidden
extra fields are rejected by FastAPI/Pydantic with HTTP `422` validation
responses.

## Unexpected internal errors

Unexpected exceptions are returned as HTTP `500` with a generic message:

```json
{"detail": "Internal analytical service error."}
```

Internal exception details, stack traces, secrets, SQL, prompts, and other
implementation details are not exposed through this response.

## Evidence and provenance

`evidence` and `provenance` are passed through from the existing Orchestrator
result. The API layer does not create, modify, or reinterpret analytical
evidence or provenance.

## Current scope

This API currently exposes the workflow that is actually integrated into the
Orchestrator. Recommendation Agent, Visualization Agent, and Report Composer
remain separate downstream components established in Chat 12; Chat 13 does not
silently redesign or integrate them into the Orchestrator.

The API does not directly query MySQL, invoke the SQL Tool Layer directly,
calculate KPIs, redefine semantic metrics, generate SQL independently, or
create findings/recommendations independently.

The following endpoints are intentionally outside the Chat 13 implementation:

- run-history endpoints
- schema metadata endpoints
- metric metadata endpoints
- authentication
- deployment/cloud infrastructure
- Streamlit UI

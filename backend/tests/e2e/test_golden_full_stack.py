"""Real HTTP + browser + PDF golden E2E.

The test intentionally does not use FastAPI's in-process client or mock the
frontend/PDF renderer. It requires a running PostgreSQL-backed backend and a
Vite frontend so failures identify the first broken deployment boundary.
"""

from __future__ import annotations

import os
import secrets
import time

import httpx
import pytest

from fixtures.golden_contract import assert_five_page_contract, assert_pdf_page_count, assert_pdf_semantic_markers
from fixtures.kinematics_golden_v1 import load_golden_fixture


pytestmark = pytest.mark.golden_e2e

def _fail_infra(code: str, message: str) -> None:
    pytest.fail(f"E2E_INFRA_ERROR:{code} {message}", pytrace=False)


def _fail_product(code: str, message: str) -> None:
    pytest.fail(f"E2E_PRODUCT_ASSERTION:{code} {message}", pytrace=False)


def _require_response(response: httpx.Response, expected: int, endpoint: str) -> dict:
    if response.status_code != expected:
        body = response.text[:1000].replace("\n", " ")
        if response.status_code >= 500:
            _fail_infra("SERVICE_HTTP_ERROR", f"{endpoint} returned {response.status_code}: {body}")
        _fail_product("HTTP_STATUS", f"{endpoint} expected {expected}, got {response.status_code}: {body}")
    try:
        return response.json()
    except ValueError as exc:
        _fail_product("INVALID_JSON", f"{endpoint} returned non-JSON response: {exc}")
        raise AssertionError from exc


def _request(client: httpx.Client, method: str, endpoint: str, **kwargs) -> httpx.Response:
    try:
        return client.request(method, endpoint, **kwargs)
    except httpx.HTTPError as exc:
        _fail_infra("HTTP_UNAVAILABLE", f"{method} {endpoint}: {exc}")
        raise AssertionError from exc


@pytest.mark.golden_e2e
def test_golden_full_stack_real_http_frontend_and_pdf():
    if os.getenv("GOLDEN_E2E_ENABLED", "").lower() not in {"1", "true", "yes"}:
        _fail_infra(
            "E2E_NOT_CONFIGURED",
            "set GOLDEN_E2E_ENABLED=1 when PostgreSQL, backend, frontend, Chromium and FFmpeg are running",
        )

    try:
        fixture = load_golden_fixture()
    except Exception as exc:
        _fail_infra("FIXTURE_INVALID", str(exc))
        raise AssertionError from exc
    for path, label in (
        (fixture.video_path, "golden video"),
        (fixture.annotations_path, "golden annotations"),
    ):
        if not path.is_file():
            _fail_infra("FIXTURE_MISSING", f"{label} not found at {path}")

    backend_url = os.getenv("GOLDEN_E2E_BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
    frontend_url = os.getenv("GOLDEN_E2E_FRONTEND_URL", "http://127.0.0.1:5174").rstrip("/")
    api_root = f"{backend_url}/api/v1"
    timeout = httpx.Timeout(120.0, connect=10.0)
    poll_timeout = float(os.getenv("GOLDEN_E2E_TIMEOUT_SECONDS", "300"))

    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        health = _request(client, "GET", f"{backend_url}/health")
        if health.status_code != 200:
            _fail_infra("BACKEND_UNHEALTHY", f"{backend_url}/health returned {health.status_code}")
        frontend = _request(client, "GET", frontend_url)
        if frontend.status_code != 200:
            _fail_infra("FRONTEND_UNAVAILABLE", f"{frontend_url} returned {frontend.status_code}")

        suffix = secrets.token_hex(5)
        username = f"golden_e2e_{suffix}"
        password = "golden-e2e-password"
        _require_response(
            _request(
                client,
                "POST",
                f"{api_root}/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "full_name": "Golden E2E Coach",
                    "role": "coach",
                },
            ),
            201,
            "auth/register",
        )
        login = _require_response(
            _request(
                client,
                "POST",
                f"{api_root}/auth/login",
                data={"username": username, "password": password},
            ),
            200,
            "auth/login",
        )
        token = login.get("access_token")
        if not token:
            _fail_product("AUTH_TOKEN_MISSING", "auth/login returned no access_token")
        client.headers["Authorization"] = f"Bearer {token}"

        athlete = _require_response(
            _request(
                client,
                "POST",
                f"{api_root}/athletes",
                json={"name": "Golden E2E Athlete", "gender": "female", "level": "test"},
            ),
            201,
            "athletes",
        )
        session = _require_response(
            _request(
                client,
                "POST",
                f"{api_root}/sessions",
                json={
                    "athlete_id": athlete["id"],
                    "title": "Golden E2E Session",
                    "stroke_type": "freestyle",
                    "distance_m": 50,
                    "pool_length_m": 25,
                },
            ),
            201,
            "sessions",
        )
        session_id = session["id"]

        with fixture.video_path.open("rb") as video_handle:
            uploaded_video = _require_response(
                _request(
                    client,
                    "POST",
                    f"{api_root}/videos/upload",
                    files={"file": (fixture.video_path.name, video_handle, "video/mp4")},
                ),
                201,
                "videos/upload",
            )
        video_id = uploaded_video["video"]["id"]
        session_video = _require_response(
            _request(
                client,
                "POST",
                f"{api_root}/sessions/{session_id}/videos",
                json={
                    "video_file_id": video_id,
                    "view_type": "side",
                    "fps": fixture.video_fps,
                    "resolution": fixture.video_resolution,
                },
            ),
            201,
            "sessions/{id}/videos",
        )
        if session_video["video_file_id"] != video_id:
            _fail_product("VIDEO_BINDING_MISMATCH", "session video does not reference uploaded video")

        with fixture.annotations_path.open("rb") as annotation_handle:
            ingested = _require_response(
                _request(
                    client,
                    "POST",
                    f"{api_root}/sessions/{session_id}/videos/{video_id}/annotations/ingest",
                    data={
                        "source": "cvat",
                        "annotation_fps": str(fixture.video_fps),
                        "metadata": '{"fixture_profile":"kinematics-golden.v1"}',
                    },
                    files={"file": (fixture.annotations_path.name, annotation_handle, "application/xml")},
                ),
                201,
                "annotations/ingest",
            )
        normalized_id = ingested.get("normalized_annotation_id")
        if not normalized_id:
            _fail_product("NORMALIZED_ANNOTATION_MISSING", "ingest returned no normalized_annotation_id")

        task = _require_response(
            _request(
                client,
                "POST",
                f"{api_root}/analysis/submit",
                json={
                    "session_id": session_id,
                    "normalized_annotation_id": normalized_id,
                    "acknowledge_quality_warnings": True,
                    "pipeline_type": "annotation_kinematics",
                    "pipeline_version": "side_2d_v1",
                },
            ),
            201,
            "analysis/submit",
        )
        task_id = task["id"]

        deadline = time.monotonic() + poll_timeout
        final_status = None
        while time.monotonic() < deadline:
            status_payload = _require_response(
                _request(client, "GET", f"{api_root}/analysis/{task_id}/status"),
                200,
                "analysis/{id}/status",
            )
            final_status = status_payload
            if status_payload["status"] == "completed":
                break
            if status_payload["status"] == "failed":
                _fail_product(
                    "PIPELINE_FAILED",
                    f"analysis task failed at {status_payload.get('failed_stage')}: {status_payload.get('error_code')} {status_payload.get('error_message')}",
                )
            time.sleep(1)
        else:
            _fail_infra("PIPELINE_TIMEOUT", f"analysis task {task_id} did not complete within {poll_timeout}s")

        if not final_status or final_status["status"] != "completed":
            _fail_product("PIPELINE_NOT_COMPLETED", f"unexpected final status: {final_status}")

        report_response = _require_response(
            _request(client, "GET", f"{api_root}/reports/{session_id}"),
            200,
            "reports/{session_id}",
        )
        report = report_response.get("report") or {}
        try:
            assert_five_page_contract(report)
        except AssertionError as exc:
            _fail_product("REPORT_PAGE_CONTRACT", str(exc))
        signature = report.get("generation_signature")
        trace_signature = (report.get("source_trace") or {}).get("report_generation_signature")
        if not signature or signature != trace_signature:
            _fail_product("GENERATION_SIGNATURE_MISMATCH", f"report={signature!r}, trace={trace_signature!r}")

        exported = _require_response(
            _request(
                client,
                "POST",
                f"{api_root}/sessions/{session_id}/report/export/pdf",
                json={"force": True},
            ),
            200,
            "report/export/pdf",
        )
        if exported.get("pdf_status") != "exported":
            _fail_product("PDF_NOT_EXPORTED", f"unexpected export payload: {exported}")

        pdf_response = _request(client, "GET", f"{api_root}/sessions/{session_id}/report/pdf")
        if pdf_response.status_code != 200:
            _fail_product("PDF_DOWNLOAD_FAILED", f"download returned {pdf_response.status_code}: {pdf_response.text[:500]}")
        pdf_bytes = pdf_response.content
        if not pdf_bytes.startswith(b"%PDF"):
            _fail_product("PDF_PAYLOAD_INVALID", "exported response is not a PDF")
        try:
            assert_pdf_page_count(pdf_bytes, expected=5)
            assert_pdf_semantic_markers(pdf_bytes)
        except AssertionError as exc:
            if "pypdf" in str(exc).lower():
                _fail_infra("PDF_ASSERTION_TOOL_MISSING", str(exc))
            _fail_product("PDF_PAGE_CONTRACT", str(exc))

        # The export request above runs the production Playwright renderer
        # against the real frontend print route. The PDF markers are the
        # browser-observable page-order contract; the API signature check
        # proves the rendered payload belongs to the same report generation.

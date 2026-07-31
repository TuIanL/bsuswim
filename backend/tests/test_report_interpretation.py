import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.models import AnalysisTask, ReportInterpretation, ReportMetadata
from app.models import User
from app.core.deps import get_current_user
from app.main import app
from app.schemas.report_interpretation import CurveSummary, EvidenceExclusion, EvidenceItem, ProviderRequest
from app.services.report_interpretation.knowledge import KnowledgeRegistry
from app.services.report_interpretation.evidence import build_evidence_bundle
from app.services.report_interpretation.projector import input_hash, project_report
from app.services.report_interpretation.provider import (
    FakeProvider,
    OpenAICompatibleProvider,
    ProviderError,
)
from app.services.report_interpretation.prompt import SYSTEM_POLICY
from app.services.report_interpretation.service import (
    _fit_evidence_to_input_budget,
    create_or_reuse_interpretation,
    execute_interpretation,
    prepare_input,
    resolve_interpretation_envelope,
)
from app.services.report_interpretation.signature import generation_signature
from app.services.report_interpretation.telemetry import summarize_observability
from app.services.report_interpretation.validator import (
    InterpretationValidationError,
    complete_numeric_fact_refs,
    parse_output,
    validate_output,
)


def sample_report(signature: str = "report-sig-1") -> dict:
    return {
        "schema_version": "swim-report.v1",
        "report_profile": "side_2d_kinematics_5page_v1",
        "generation_signature": signature,
        "context": {
            "athlete": {"id": 10, "name": "Private Name", "level": "beginner"},
            "session": {"id": 20, "stroke_type": "freestyle", "distance_m": 50},
            "video": {"view_type": "side", "original_filename": "private.mp4", "storage_path": "/tmp/private.mp4"},
        },
        "source_trace": {"annotation_revision": 3},
        "sections": [
            {
                "page_number": 1,
                "page_type": "analysis_overview",
                "content": {"analysis_boundaries": ["本报告基于侧面二维骨架生成。"]},
                "metrics": [], "findings": [], "quality_notes": [],
            },
            {
                "page_number": 2,
                "page_type": "body_posture_control",
                "metrics": [
                    {"key": "body_angle_std_deg", "label": "身体轴角波动", "value": 4.2, "unit": "deg", "availability": "available", "confidence": 0.91},
                    {"key": "hip_vertical_range_px", "label": "髋部波动", "value": 0, "unit": "px", "availability": "unavailable", "confidence": 0.0},
                ],
                "findings": [{
                    "code": "body_axis_variation_review",
                    "rule_id": "KRF001",
                    "title": "疑似身体轴角波动较大",
                    "status": "review_required",
                    "confidence": 0.9,
                    "threshold_basis": "project_heuristic_v1",
                    "limitations": ["未识别具体泳姿阶段"],
                    "evidence_frames": [{"metric_key": "body_angle_std_deg", "annotation_frame": 12, "source_video_frame": 15, "mapping_status": "verified", "role": "maximum"}],
                }],
                "quality_notes": [],
            },
            {"page_number": 3, "page_type": "upper_limb_kinematics", "metrics": [], "findings": [], "quality_notes": []},
            {"page_number": 4, "page_type": "lower_limb_kinematics", "metrics": [], "findings": [], "quality_notes": []},
            {
                "page_number": 5,
                "page_type": "review_and_retest",
                "metrics": [], "findings": [], "quality_notes": [],
                "content": {"retest_metrics": [{"metric_key": "body_angle_std_deg", "label": "身体轴角波动", "current_value": 4.2, "unit": "deg", "reason": "复核稳定性"}]},
            },
        ],
    }


def fake_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "ai_interpretation_enabled": True,
        "ai_interpretation_provider": "fake",
        "ai_interpretation_model": "deterministic-test",
        "ai_interpretation_rate_limit_per_hour": 100,
    }
    values.update(overrides)
    return Settings(**values)


def test_projector_is_stable_private_and_preserves_unavailable():
    first = project_report(sample_report())
    second = project_report(sample_report())
    assert input_hash(first) == input_hash(second)
    serialized = json.dumps(first.model_dump(mode="json"), ensure_ascii=False)
    for forbidden in ("Private Name", "private.mp4", "/tmp/private.mp4", '"id": 10', '"id": 20'):
        assert forbidden not in serialized
    unavailable = next(f for f in first.facts if f.fact_id == "metric:hip_vertical_range_px")
    assert unavailable.value is None
    assert unavailable.availability == "unavailable"
    assert unavailable.limitations
    assert next(f for f in first.facts if f.fact_id == "frame:body_axis_variation_review:0").value == 15


def test_knowledge_registry_is_reviewed_stable_and_relevant():
    registry = KnowledgeRegistry()
    projected = project_report(sample_report())
    selected = registry.retrieve(projected, limit=2)
    assert selected
    assert all(item.review_status == "active" for item in selected)
    assert selected == registry.retrieve(projected, limit=2)
    assert selected[0].knowledge_id == "freestyle-body-line-observation"
    assert len(registry.version) == 64


def test_signature_changes_with_model_or_knowledge():
    settings = fake_settings()
    projected, registry, first, current_hash = prepare_input(sample_report(), settings)
    second, second_hash = generation_signature(projected, fake_settings(ai_interpretation_model="other"), registry.version)
    third, _ = generation_signature(projected, settings, "different-knowledge")
    fourth, _ = generation_signature(
        projected,
        fake_settings(ai_interpretation_thinking_enabled=False),
        registry.version,
    )
    assert current_hash == second_hash
    assert len({first, second, third, fourth}) == 4


def test_input_and_cost_budgets_fail_before_provider_call():
    with pytest.raises(ProviderError) as too_large:
        prepare_input(sample_report(), fake_settings(ai_interpretation_max_input_chars=10))
    assert too_large.value.code == "interpretation_input_too_large"

    with pytest.raises(ProviderError) as too_expensive:
        prepare_input(
            sample_report(),
            fake_settings(
                ai_interpretation_max_estimated_cost_usd=0.000001,
                ai_interpretation_input_cost_per_million_tokens=100,
            ),
        )
    assert too_expensive.value.code == "interpretation_cost_limit_exceeded"


def _provider_request(report=None):
    projected = project_report(report or sample_report())
    registry = KnowledgeRegistry()
    projected.knowledge = registry.retrieve(projected)
    return ProviderRequest(policy=SYSTEM_POLICY, input=projected, output_schema={})


def test_fake_provider_contract_and_guardrails():
    request = _provider_request()
    valid = parse_output(FakeProvider().generate(request).output)
    result = validate_output(valid, request.input)
    assert result["valid"] is True

    with pytest.raises(InterpretationValidationError) as extra:
        parse_output(FakeProvider("extra_field").generate(request).output)
    assert extra.value.code == "output_schema_invalid"

    assertive = parse_output(FakeProvider("assertive").generate(request).output)
    with pytest.raises(InterpretationValidationError) as claim:
        validate_output(assertive, request.input)
    assert claim.value.code == "assertive_claim_forbidden"


def test_evidence_bundle_uses_current_report_assets_only(tmp_path):
    image = tmp_path / "kinematic-artifacts" / "demo.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png-evidence")
    report = sample_report()
    report["sections"][1]["assets"] = [{
        "key": "body_posture.keyframe.body_axis_min",
        "url": "/uploads/kinematic-artifacts/demo.png",
        "artifact_type": "annotated_keyframe",
        "mime_type": "image/png",
        "checksum_sha256": __import__("hashlib").sha256(b"png-evidence").hexdigest(),
        "module_key": "body_posture",
        "metric_keys": ["body_angle_std_deg"],
        "width": 100,
        "height": 100,
        "source_annotation_revision": 3,
        "annotation_frame": 12,
    }]
    input_data = project_report(report)
    settings = fake_settings(upload_dir=tmp_path)
    bundle = build_evidence_bundle(report, input_data, settings)
    assert [item.asset_key for item in bundle.items] == ["body_posture.keyframe.body_axis_min"]
    assert "metric:body_angle_std_deg" in bundle.items[0].fact_refs
    assert bundle.image_data_urls["evidence:body_posture_head_trunk:body_posture.keyframe.body_axis_min"].startswith("data:image/png;base64,")


def test_validator_rejects_unknown_or_fact_free_visual_reference():
    request = _provider_request()
    raw = FakeProvider().generate(request).output
    raw["plain_language_summary"]["evidence_refs"] = ["evidence:not-present"]
    with pytest.raises(InterpretationValidationError) as unknown:
        validate_output(parse_output(raw), request.input)
    assert unknown.value.code == "grounding_reference_invalid"


def test_deepseek_provider_uses_official_json_object_contract(monkeypatch):
    request = _provider_request()
    request.output_schema = {"type": "object", "required": ["schema_version"]}
    valid_output = FakeProvider().generate(request).output
    captured = {}

    class Response:
        status_code = 200
        headers = {"x-request-id": "deepseek-request-1"}

        def json(self):
            return {
                "id": "deepseek-response-1",
                "choices": [{"message": {"content": json.dumps(valid_output)}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            }

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "payload": json, "timeout": timeout})
        return Response()

    monkeypatch.setattr("app.services.report_interpretation.provider.httpx.post", fake_post)
    settings = fake_settings(
        ai_interpretation_provider="deepseek",
        ai_interpretation_base_url="https://api.deepseek.com",
        ai_interpretation_model="deepseek-v4-flash",
        ai_interpretation_api_key="test-only-key",
    )
    response = OpenAICompatibleProvider(settings).generate(request)

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["payload"]["model"] == "deepseek-v4-flash"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert "max_tokens" not in captured["payload"]
    assert captured["payload"]["thinking"] == {"type": "enabled"}
    user_payload = json.loads(captured["payload"]["messages"][1]["content"])
    assert user_payload["required_output_json_schema"] == request.output_schema
    assert response.provider_request_id == "deepseek-request-1"


def test_qwen_visual_request_uses_multipart_content(monkeypatch):
    request = _provider_request()
    request.evidence_images = {"evidence:upper_limb:frame": "data:image/png;base64,cG5n"}
    request.visual_mode = True
    valid_output = FakeProvider().generate(request).output
    captured = {}

    class Response:
        status_code = 200
        headers = {}

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(valid_output)}}], "usage": {}}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "payload": json})
        return Response()

    monkeypatch.setattr("app.services.report_interpretation.provider.httpx.post", fake_post)
    settings = fake_settings(
        ai_interpretation_provider="qwen",
        ai_interpretation_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ai_interpretation_model="qwen-vl-test",
        ai_interpretation_api_key="test-only-key",
        ai_interpretation_visual_enabled=True,
        ai_interpretation_model_supports_vision=True,
        ai_interpretation_model_supports_structured_output=True,
    )
    OpenAICompatibleProvider(settings).generate(request)
    content = captured["payload"]["messages"][1]["content"]
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert isinstance(content, list)
    assert any(part.get("type") == "image_url" for part in content)


@pytest.mark.parametrize(
    "finish_reason,content,expected_code,retryable",
    [
        ("length", '{"schema_version":', "provider_output_truncated", False),
        ("stop", "", "provider_empty_response", True),
    ],
)
def test_provider_classifies_truncated_and_empty_content(
    monkeypatch, finish_reason, content, expected_code, retryable
):
    class Response:
        status_code = 200
        headers = {}

        def json(self):
            return {
                "choices": [
                    {"finish_reason": finish_reason, "message": {"content": content}}
                ]
            }

    monkeypatch.setattr(
        "app.services.report_interpretation.provider.httpx.post",
        lambda *args, **kwargs: Response(),
    )
    settings = fake_settings(
        ai_interpretation_provider="deepseek",
        ai_interpretation_base_url="https://api.deepseek.com",
        ai_interpretation_model="deepseek-v4-flash",
        ai_interpretation_api_key="test-only-key",
        ai_interpretation_max_retries=0,
    )

    with pytest.raises(ProviderError) as exc:
        OpenAICompatibleProvider(settings).generate(_provider_request())
    assert exc.value.code == expected_code
    assert exc.value.retryable is retryable


@pytest.mark.parametrize("mode,code,retryable", [
    ("timeout", "provider_timeout", True),
    ("rate_limit", "provider_unavailable", True),
])
def test_fake_provider_classifies_errors(mode, code, retryable):
    with pytest.raises(ProviderError) as exc:
        FakeProvider(mode).generate(_provider_request())
    assert exc.value.code == code
    assert exc.value.retryable is retryable


def test_validator_rejects_unknown_refs_numbers_and_knowledge_free_training():
    request = _provider_request()
    raw = FakeProvider().generate(request).output
    raw["plain_language_summary"]["fact_refs"] = ["metric:invented"]
    with pytest.raises(InterpretationValidationError) as ref_error:
        validate_output(parse_output(raw), request.input)
    assert ref_error.value.code == "grounding_reference_invalid"

    raw = FakeProvider().generate(request).output
    raw["plain_language_summary"]["text"] = "本次综合值为 99 分。"
    with pytest.raises(InterpretationValidationError) as number_error:
        validate_output(parse_output(raw), request.input)
    assert number_error.value.code == "numeric_claim_ungrounded"

    raw = FakeProvider().generate(request).output
    raw["training_suggestions"][0]["knowledge_refs"] = []
    with pytest.raises(InterpretationValidationError) as knowledge_error:
        validate_output(parse_output(raw), request.input)
    assert knowledge_error.value.code == "training_knowledge_reference_required"


def test_validator_accepts_grounded_rounding_and_confidence_percentage():
    report = sample_report()
    report["sections"][1]["metrics"][0]["value"] = 4.234
    request = _provider_request(report)
    raw = FakeProvider().generate(request).output
    raw["plain_language_summary"] = {
        "text": "身体轴角波动约为4.2 deg，当前事实置信度为91%。",
        "fact_refs": ["metric:body_angle_std_deg"],
        "knowledge_refs": [],
    }
    result = validate_output(parse_output(raw), request.input)
    assert result["valid"] is True


def test_validator_accepts_referenced_nested_metric_values_and_distance_context():
    report = sample_report()
    report["sections"][2]["metrics"] = [
        {
            "key": "bilateral_elbow_rom_deg",
            "label": "双侧肘关节活动范围",
            "value": {"left": 64.85, "right": 124.38},
            "unit": "deg",
            "availability": "available",
            "confidence": 0.83,
        }
    ]
    request = _provider_request(report)
    raw = FakeProvider().generate(request).output
    raw["plain_language_summary"] = {
        "text": "本次50米测试中，左右数值分别为64.85 deg和124.38 deg。",
        "fact_refs": ["metric:bilateral_elbow_rom_deg"],
        "knowledge_refs": [],
    }
    result = validate_output(parse_output(raw), request.input)
    assert result["valid"] is True


def test_validator_accepts_referenced_frame_list_count():
    report = sample_report()
    report["sections"][1]["metrics"].append(
        {
            "key": "head_motion_spike_frames",
            "label": "头部运动突增帧",
            "value": [29, 42, 72, 83],
            "unit": "frame",
            "availability": "available",
            "confidence": 0.83,
        }
    )
    request = _provider_request(report)
    raw = FakeProvider().generate(request).output
    raw["plain_language_summary"] = {
        "text": "本次识别到4个头部运动突增帧。",
        "fact_refs": ["metric:head_motion_spike_frames"],
        "knowledge_refs": [],
    }
    result = validate_output(parse_output(raw), request.input)
    assert result["valid"] is True


def test_numeric_reference_completion_is_conservative():
    report = sample_report()
    report["sections"][2]["metrics"] = [
        {
            "key": "bilateral_elbow_rom_deg",
            "label": "双侧肘关节活动范围",
            "value": {"left": 64.85, "right": 124.38},
            "unit": "deg",
            "availability": "available",
            "confidence": 0.83,
        }
    ]
    request = _provider_request(report)
    raw = FakeProvider().generate(request).output
    raw["plain_language_summary"] = {
        "text": "双侧数值约为64.9 deg和124.4 deg。",
        "fact_refs": ["finding:body_axis_variation_review"],
        "knowledge_refs": [],
    }
    output = parse_output(raw)
    completed = complete_numeric_fact_refs(output, request.input)
    assert completed[0]["fact_ref"] == "metric:bilateral_elbow_rom_deg"
    assert validate_output(output, request.input)["valid"] is True

    output.plain_language_summary.text += " 建议完成99组。"
    complete_numeric_fact_refs(output, request.input)
    with pytest.raises(InterpretationValidationError) as error:
        validate_output(output, request.input)
    assert error.value.code == "numeric_claim_ungrounded"


def test_module_explanation_allows_global_quality_but_not_cross_module_metrics():
    request = _provider_request()
    quality_fact = request.input.facts[0].model_copy(
        update={
            "fact_id": "quality:low_confidence_metrics_present",
            "kind": "quality",
            "module_key": "analysis_overview",
            "source_key": "low_confidence_metrics_present",
            "label": "存在低置信度指标",
            "value": True,
        }
    )
    request.input.facts.append(quality_fact)
    raw = FakeProvider().generate(request).output
    raw["module_explanations"] = [
        {
            "module_key": "body_posture_head_trunk",
            "text": "该模块需要结合全局质量限制解读。",
            "fact_refs": [
                "metric:body_angle_std_deg",
                "quality:low_confidence_metrics_present",
            ],
            "knowledge_refs": [],
        }
    ]
    assert validate_output(parse_output(raw), request.input)["valid"] is True

    raw["module_explanations"][0]["fact_refs"] = ["metric:body_angle_std_deg"]
    raw["module_explanations"][0]["module_key"] = "upper_limb"
    with pytest.raises(InterpretationValidationError) as mismatch:
        validate_output(parse_output(raw), request.input)
    assert mismatch.value.code == "module_reference_mismatch"


@pytest.fixture
def report_record(db_session, test_session):
    task = AnalysisTask(session_id=test_session.id)
    db_session.add(task)
    db_session.flush()
    report = ReportMetadata(
        session_id=test_session.id,
        task_id=task.id,
        source="annotation_kinematics",
        report_data=sample_report(),
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


def test_domain_service_reuses_ready_and_force_failure_does_not_replace_it(db_session, report_record, test_coach):
    settings = fake_settings()
    first, reused = create_or_reuse_interpretation(
        db_session, report_record, requested_by_user_id=test_coach.id, settings=settings
    )
    assert first and reused is False and first.status == "pending"
    ready = execute_interpretation(first.id, db=db_session, settings=settings, provider=FakeProvider())
    assert ready.status == "ready"

    same, reused = create_or_reuse_interpretation(
        db_session, report_record, requested_by_user_id=test_coach.id, settings=settings
    )
    assert same.id == ready.id and reused is True

    forced, reused = create_or_reuse_interpretation(
        db_session, report_record, requested_by_user_id=test_coach.id, force=True, settings=settings
    )
    assert forced.id != ready.id and forced.attempt == 2 and reused is False
    failed = execute_interpretation(forced.id, db=db_session, settings=settings, provider=FakeProvider("assertive"))
    assert failed.status == "failed"
    envelope = resolve_interpretation_envelope(db_session, report_record, settings=settings)
    assert envelope.status == "ready"
    assert envelope.trace.generation_signature == ready.generation_signature


def test_input_budget_downsamples_dense_curves_before_json_serialization():
    settings = fake_settings()
    projected, _, _, _ = prepare_input(sample_report(), settings)
    projected.evidence = [
        EvidenceItem(
            evidence_id="evidence-dense-curve",
            asset_key="body_posture.chart.dense",
            module_key="body_posture_head_trunk",
            media_type="time_series",
            mime_type="image/svg+xml",
            selection_reason="budget regression fixture",
            curve_summaries=[
                CurveSummary(
                    metric_key="body_angle_std_deg",
                    unit="deg",
                    points=[{"frame": index, "value": float(index)} for index in range(20_000)],
                    source_point_count=20_000,
                )
            ],
        )
    ]

    _fit_evidence_to_input_budget(projected, 24_000)

    curve = projected.evidence[0].curve_summaries[0]
    assert len(curve.points) <= 64
    assert curve.points[-1] == {"frame": 19_999, "value": 19_999.0}

    _fit_evidence_to_input_budget(projected, 1)

    assert projected.evidence == []
    assert all(isinstance(item, EvidenceExclusion) for item in projected.evidence_exclusions)


def test_envelope_not_configured_and_stale(db_session, report_record, test_coach):
    disabled = Settings(_env_file=None)
    assert resolve_interpretation_envelope(db_session, report_record, settings=disabled).status == "not_configured"

    settings = fake_settings()
    record, _ = create_or_reuse_interpretation(
        db_session, report_record, requested_by_user_id=test_coach.id, settings=settings
    )
    execute_interpretation(record.id, db=db_session, settings=settings, provider=FakeProvider())
    report_record.report_data = sample_report("new-report-signature")
    db_session.add(report_record)
    db_session.commit()
    envelope = resolve_interpretation_envelope(db_session, report_record, settings=settings)
    assert envelope.status == "stale"
    assert envelope.content is None


def test_failed_output_is_not_persisted_as_partial(db_session, report_record, test_coach):
    settings = fake_settings()
    record, _ = create_or_reuse_interpretation(
        db_session, report_record, requested_by_user_id=test_coach.id, settings=settings
    )
    result = execute_interpretation(record.id, db=db_session, settings=settings, provider=FakeProvider("extra_field"))
    assert result.status == "failed"
    assert result.content is None
    assert result.error_code == "output_schema_invalid"
    assert db_session.get(ReportInterpretation, record.id).content is None


def test_report_and_interpretation_api_degrade_when_not_configured(
    client, auth_headers, report_record, monkeypatch
):
    disabled = Settings(_env_file=None, ai_interpretation_enabled=False)
    monkeypatch.setattr(
        "app.services.report_interpretation.service.get_settings", lambda: disabled
    )
    report_response = client.get(f"/api/v1/reports/{report_record.session_id}")
    assert report_response.status_code == 200
    payload = report_response.json()
    assert payload["report"]["generation_signature"] == "report-sig-1"
    assert payload["ai_interpretation"]["status"] == "not_configured"

    status_response = client.get(
        f"/api/v1/sessions/{report_record.session_id}/report/interpretation"
    )
    assert status_response.status_code == 200
    assert status_response.json() == {
        "status": "not_configured",
        "content": None,
        "trace": None,
        "error": None,
        "can_regenerate": False,
    }

    generate_response = client.post(
        f"/api/v1/sessions/{report_record.session_id}/report/interpretation/generate",
        json={"force": False},
    )
    assert generate_response.status_code == 202
    assert generate_response.json()["status"] == "not_configured"


def test_interpretation_api_enforces_report_ownership(
    client, db_session, report_record, auth_headers
):
    stranger = User(
        username="other_coach",
        email="other@test.com",
        password_hash="dummy",
        role="coach",
        is_active=True,
    )
    db_session.add(stranger)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: stranger
    try:
        response = client.get(
            f"/api/v1/sessions/{report_record.session_id}/report/interpretation"
        )
        assert response.status_code == 404
        assert "generation_signature" not in response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_generation_api_is_non_blocking_and_returns_sanitized_state(
    client, db_session, report_record, auth_headers, monkeypatch
):
    settings = fake_settings()
    scheduled: list[int] = []
    monkeypatch.setattr(
        "app.services.report_interpretation.service.get_settings", lambda: settings
    )
    monkeypatch.setattr(
        "app.api.routes.report_interpretations.schedule_interpretation",
        lambda interpretation_id: scheduled.append(interpretation_id),
    )

    response = client.post(
        f"/api/v1/sessions/{report_record.session_id}/report/interpretation/generate",
        json={"force": False},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert scheduled == [payload["interpretation_id"]]
    assert "api_key" not in response.text
    assert "policy" not in response.text

    execute_interpretation(
        payload["interpretation_id"], db=db_session, settings=settings, provider=FakeProvider()
    )
    monkeypatch.setattr(
        "app.api.routes.report_interpretations.resolve_interpretation_envelope",
        lambda db, report: resolve_interpretation_envelope(db, report, settings=settings),
    )
    ready = client.get(
        f"/api/v1/sessions/{report_record.session_id}/report/interpretation"
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["trace"]["generation_signature"] == payload["generation_signature"]


def test_generation_api_deduplicates_and_records_force_retry(
    client, db_session, report_record, auth_headers, monkeypatch
):
    settings = fake_settings()
    scheduled = []
    monkeypatch.setattr("app.services.report_interpretation.service.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.api.routes.report_interpretations.schedule_interpretation", scheduled.append
    )

    url = f"/api/v1/sessions/{report_record.session_id}/report/interpretation/generate"
    first = client.post(url, json={"force": False})
    duplicate = client.post(url, json={"force": False})
    forced = client.post(url, json={"force": True})

    assert first.status_code == duplicate.status_code == forced.status_code == 202
    assert duplicate.json()["interpretation_id"] == first.json()["interpretation_id"]
    assert duplicate.json()["reused"] is True
    assert forced.json()["interpretation_id"] != first.json()["interpretation_id"]
    assert scheduled == [first.json()["interpretation_id"], forced.json()["interpretation_id"]]
    forced_record = db_session.get(ReportInterpretation, forced.json()["interpretation_id"])
    assert forced_record.force_requested is True
    assert forced_record.attempt == 2


def test_generation_api_rate_limit_and_timeout_state(
    client, db_session, report_record, auth_headers, monkeypatch
):
    settings = fake_settings(ai_interpretation_rate_limit_per_hour=1)
    scheduled = []
    monkeypatch.setattr("app.services.report_interpretation.service.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.api.routes.report_interpretations.schedule_interpretation", scheduled.append
    )
    url = f"/api/v1/sessions/{report_record.session_id}/report/interpretation/generate"

    first = client.post(url, json={"force": False})
    reused = client.post(url, json={"force": False})
    limited = client.post(url, json={"force": True})
    assert first.status_code == 202
    assert reused.status_code == 202
    assert reused.json()["reused"] is True
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "interpretation_rate_limited"

    failed = execute_interpretation(
        first.json()["interpretation_id"],
        db=db_session,
        settings=settings,
        provider=FakeProvider("timeout"),
    )
    assert failed.status == "failed"
    assert failed.usage["latency_ms"] >= 0
    monkeypatch.setattr(
        "app.api.routes.report_interpretations.resolve_interpretation_envelope",
        lambda db, report: resolve_interpretation_envelope(db, report, settings=settings),
    )
    status_response = client.get(
        f"/api/v1/sessions/{report_record.session_id}/report/interpretation"
    )
    assert status_response.status_code == 200
    assert status_response.json()["error"]["code"] == "provider_timeout"
    assert status_response.json()["error"]["retryable"] is True


def test_generation_api_reports_busy_queue_instead_of_waiting(
    client, report_record, auth_headers, monkeypatch
):
    def raise_busy(*args, **kwargs):
        raise ProviderError(
            "interpretation_queue_busy",
            "报告正在被另一项操作占用，请稍后重新生成 AI 解读",
            True,
        )

    monkeypatch.setattr(
        "app.api.routes.report_interpretations.create_or_reuse_interpretation",
        raise_busy,
    )

    response = client.post(
        f"/api/v1/sessions/{report_record.session_id}/report/interpretation/generate",
        json={"force": True},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "interpretation_queue_busy",
        "message": "报告正在被另一项操作占用，请稍后重新生成 AI 解读",
        "retryable": True,
    }


def test_fixed_evaluation_cases_cover_required_risk_profiles(tmp_path):
    fixture_path = Path(__file__).parent / "fixtures" / "report_interpretation_eval_v1.json"
    evaluation = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = evaluation["cases"]
    assert {case["scenario"] for case in cases} == {
        "normal",
        "low_confidence",
        "unavailable",
        "no_assets",
        "stale_asset",
        "visual_text_capability_mismatch",
        "empty_findings",
        "high_risk_wording",
        "adversarial_visual_hallucination",
    }

    for case in cases:
        report = json.loads(json.dumps(evaluation["base_report"]))
        metric = report["sections"][0]["metrics"][0]
        metric.update(case.get("metric_overrides", {}))
        if case.get("empty_findings"):
            report["sections"][0]["findings"] = []
        request = _provider_request(report)

        if case["scenario"] == "no_assets":
            bundle = build_evidence_bundle(report, request.input, fake_settings(upload_dir=tmp_path))
            assert bundle.items == []
            assert bundle.image_data_urls == {}
            continue

        if case["scenario"] == "stale_asset":
            image = tmp_path / "stale.png"
            image.write_bytes(b"stale-evidence")
            report["sections"][0]["assets"] = [{
                "key": "body_posture.keyframe.stale",
                "url": "/uploads/stale.png",
                "artifact_type": "annotated_keyframe",
                "mime_type": "image/png",
                "checksum_sha256": __import__("hashlib").sha256(b"stale-evidence").hexdigest(),
                "source_annotation_revision": 2,
            }]
            bundle = build_evidence_bundle(report, request.input, fake_settings(upload_dir=tmp_path))
            assert bundle.items == []
            assert [item.reason for item in bundle.exclusions] == [case["expected"]["exclusion_reason"]]
            continue

        if case["scenario"] == "visual_text_capability_mismatch":
            request.visual_mode = True
            request.evidence_images = {"evidence:fixture": "data:image/png;base64,cG5n"}
            with pytest.raises(ProviderError) as rejected:
                OpenAICompatibleProvider(
                    fake_settings(ai_interpretation_api_key="test-only-key")
                ).generate(request)
            assert rejected.value.code == case["expected"]["error_code"]
            continue

        raw = FakeProvider(case.get("provider_mode", "valid")).generate(request).output
        if case["scenario"] == "adversarial_visual_hallucination":
            raw["plain_language_summary"]["text"] += " 图像显示为99度。"
        output = parse_output(raw)
        if case["expected"]["accepted"]:
            metrics = validate_output(output, request.input)
            assert metrics["fact_reference_count"] >= case["expected"]["minimum_fact_refs"]
        else:
            with pytest.raises(InterpretationValidationError) as rejected:
                validate_output(output, request.input)
            assert rejected.value.code == case["expected"]["error_code"]


def test_observability_metrics_include_grounding_guardrails_latency_tokens_and_cost(
    db_session, report_record, test_coach
):
    settings = fake_settings()
    ready_record, _ = create_or_reuse_interpretation(
        db_session, report_record, requested_by_user_id=test_coach.id, settings=settings
    )
    execute_interpretation(
        ready_record.id, db=db_session, settings=settings, provider=FakeProvider()
    )
    failed_record, _ = create_or_reuse_interpretation(
        db_session,
        report_record,
        requested_by_user_id=test_coach.id,
        force=True,
        settings=settings,
    )
    execute_interpretation(
        failed_record.id, db=db_session, settings=settings, provider=FakeProvider("assertive")
    )

    db_session.refresh(ready_record)
    db_session.refresh(failed_record)
    assert ready_record.validation_result["grounding_coverage"] == 1.0
    assert ready_record.validation_result["fact_consistency"] == 1.0
    assert ready_record.usage["total_tokens"] == 2
    assert ready_record.usage["estimated_cost_usd"] > 0
    assert failed_record.validation_result["guardrail_rejected"] is True

    summary = summarize_observability([ready_record, failed_record])
    assert summary["guardrail_rejection_rate"] == 0.5
    assert summary["average_grounding_coverage"] == 1.0
    assert summary["total_tokens"] == 2
    assert summary["average_latency_ms"] >= 0

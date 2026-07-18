"""复核发现生成服务。

负责：
- 解析并校验 AnnotationMetric（calculator / schema / source revision）
- 计算 source_metric_hash 与 generation_signature
- 重建 canonical frames（供 KRF002 等回读标注选帧，不重算触发值）
- 调用 KinematicReviewFindingsEngine
- 幂等生成 + force 原地覆盖（compute-then-overwrite，保留旧 ready 数据）
- 持久化到 kinematic_review_finding_sets
"""

import hashlib
import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnnotationMetric, KinematicReviewFindingSet, NormalizedAnnotation, User
from app.services.diagnostics.registry import RuleRegistry
from app.services.diagnostics.review_findings.adapter import Side2DKinematicsReviewAdapter
from app.services.diagnostics.review_findings.engine import KinematicReviewFindingsEngine
from app.services.metrics.kinematics.frame_resolver import resolve_frames
from app.schemas.metrics import (
    CALCULATOR_SIDE_2D_KINEMATICS,
    SCHEMA_SIDE_2D_KINEMATICS,
)
from app.schemas.kinematic_review_finding import (
    REVIEW_FINDINGS_SCHEMA,
    THRESHOLD_BASIS_DEFAULT,
)

_DEFAULT_RULE_SET = "side_2d_kinematics_v1"
_ENGINE_VERSION = "review-engine.v1"


def _stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ReviewFindingsGenerationError(Exception):
    def __init__(self, code: str, message: str, http_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _resolve_annotation_metric(db: Session, annotation_metric_id: int, current_user: User) -> AnnotationMetric:
    record = db.get(AnnotationMetric, annotation_metric_id)
    if record is None:
        raise ReviewFindingsGenerationError("metric_unavailable", "annotation_metrics 不存在", status.HTTP_404_NOT_FOUND)
    # ownership: 通过所属标注的 owner 校验
    ann = db.get(NormalizedAnnotation, record.normalized_annotation_id)
    if ann is None:
        raise ReviewFindingsGenerationError("metric_unavailable", "关联标注不存在", status.HTTP_404_NOT_FOUND)
    session = ann.session_video.session if ann.session_video else None
    if session is None or session.coach_id != current_user.id:
        raise ReviewFindingsGenerationError("metric_unavailable", "无权限", status.HTTP_404_NOT_FOUND)
    return record


def _verify_input(record: AnnotationMetric, ann: NormalizedAnnotation) -> None:
    if record.calculator != CALCULATOR_SIDE_2D_KINEMATICS:
        raise ReviewFindingsGenerationError(
            "unsupported_metric_schema", f"不支持的 calculator: {record.calculator}"
        )
    if record.schema_version != SCHEMA_SIDE_2D_KINEMATICS:
        raise ReviewFindingsGenerationError(
            "unsupported_metric_schema", f"不支持的 schema: {record.schema_version}"
        )
    if not isinstance(record.metrics, dict) or "summary" not in record.metrics:
        raise ReviewFindingsGenerationError(
            "invalid_metric_payload", "metrics 顶层结构损坏（缺少 summary）"
        )
    if record.source_revision is not None and record.source_revision != ann.revision:
        raise ReviewFindingsGenerationError(
            "metric_revision_stale",
            f"metric source_revision {record.source_revision} 与标注 revision {ann.revision} 不一致",
            status.HTTP_409_CONFLICT,
        )


def _compute_signature(
    annotation_metric_id: int,
    source_revision: int | None,
    metric_hash: str,
    rule_set: str,
    rule_file_hash: str,
    engine_version: str,
    threshold_basis: str,
) -> str:
    raw = "||".join(
        [
            str(annotation_metric_id),
            str(source_revision),
            metric_hash,
            rule_set,
            rule_file_hash,
            engine_version,
            threshold_basis,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_review_findings(
    db: Session,
    annotation_metric_id: int,
    current_user: User,
    rule_set: str = _DEFAULT_RULE_SET,
    force: bool = False,
) -> tuple[KinematicReviewFindingSet, bool]:
    record = _resolve_annotation_metric(db, annotation_metric_id, current_user)
    ann = db.get(NormalizedAnnotation, record.normalized_annotation_id)

    _verify_input(record, ann)

    registry = RuleRegistry()
    try:
        parsed = registry.load(rule_set)
    except FileNotFoundError:
        raise ReviewFindingsGenerationError("invalid_rule_set", f"规则集不存在: {rule_set}")
    if parsed["meta"].get("output_kind") != "review_finding":
        raise ReviewFindingsGenerationError(
            "rule_output_kind_mismatch", f"规则集 {rule_set} 不是 review_finding 类型"
        )

    rule_version = parsed["meta"]["schema_version"]
    rule_file_hash = parsed["meta"].get("rule_file_hash", "")
    threshold_basis = (parsed["meta"].get("threshold_basis") or {}).get("id") or THRESHOLD_BASIS_DEFAULT

    metric_hash = _stable_hash(record.metrics)
    signature = _compute_signature(
        record.id,
        record.source_revision,
        metric_hash,
        rule_set,
        rule_file_hash,
        _ENGINE_VERSION,
        threshold_basis,
    )

    existing = db.scalar(
        select(KinematicReviewFindingSet).where(
            KinematicReviewFindingSet.annotation_metric_id == record.id,
            KinematicReviewFindingSet.generation_signature == signature,
        )
    )

    if existing is not None and not force:
        return existing, False

    # 重建 canonical frames（供证据帧回读标注；不重算触发值）
    canonical_frames = resolve_frames(ann.keypoint_frames or [])
    mapping_status = "verified" if (ann.annotation_metadata or {}).get("frame_mapping", {}).get("verified") else "unknown"

    # 计算（先内存完成，再覆盖持久化）
    try:
        adapter = Side2DKinematicsReviewAdapter()
        adapter_result = adapter.adapt(record.metrics)
        engine = KinematicReviewFindingsEngine(registry)
        output = engine.run(
            adapter_result,
            rule_set=rule_set,
            metric_dict=record.metrics,
            canonical_frames=canonical_frames,
            mapping_status=mapping_status,
            threshold_basis=threshold_basis,
        )
    except Exception as exc:  # 生成失败：保留旧 ready 数据，不破坏
        raise ReviewFindingsGenerationError(
            "review_findings_generation_failed", f"生成失败: {exc}", status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    findings_json = [f.model_dump(mode="json") for f in output.findings]
    summary_json = output.summary.model_dump(mode="json")

    if existing is not None and force:
        target = existing
        target.status = "ready"
    else:
        target = KinematicReviewFindingSet(
            annotation_metric_id=record.id,
            normalized_annotation_id=ann.id,
            session_video_id=record.session_video_id,
            generation_signature=signature,
            status="generating",
        )
        db.add(target)
        db.flush()

    target.schema_version = REVIEW_FINDINGS_SCHEMA
    target.rule_set = rule_set
    target.rule_version = rule_version
    target.engine_version = _ENGINE_VERSION
    target.threshold_basis = threshold_basis
    target.source_annotation_revision = record.source_revision
    target.source_metric_schema_version = record.schema_version
    target.source_metric_calculator = record.calculator
    target.source_metric_calculator_version = record.calculator_version
    target.source_metric_hash = metric_hash
    target.findings = findings_json
    target.summary = summary_json
    target.skipped_rules = output.skipped_rules
    target.warnings = output.warnings
    target.created_by = current_user.id
    target.status = "ready"

    db.add(target)
    db.commit()
    db.refresh(target)
    return target, existing is None or force


def get_current_review_findings(
    db: Session,
    annotation_metric_id: int,
    current_user: User,
    rule_set: str = _DEFAULT_RULE_SET,
) -> KinematicReviewFindingSet:
    """按 expected signature 返回当前有效结果（R5），不按 created_at 取最新。"""
    record = _resolve_annotation_metric(db, annotation_metric_id, current_user)
    ann = db.get(NormalizedAnnotation, record.normalized_annotation_id)

    registry = RuleRegistry()
    try:
        parsed = registry.load(rule_set)
    except FileNotFoundError:
        raise ReviewFindingsGenerationError("invalid_rule_set", f"规则集不存在: {rule_set}")
    if parsed["meta"].get("output_kind") != "review_finding":
        raise ReviewFindingsGenerationError(
            "rule_output_kind_mismatch", f"规则集 {rule_set} 不是 review_finding 类型"
        )

    rule_file_hash = parsed["meta"].get("rule_file_hash", "")
    threshold_basis = (parsed["meta"].get("threshold_basis") or {}).get("id") or THRESHOLD_BASIS_DEFAULT

    metric_hash = _stable_hash(record.metrics)
    signature = _compute_signature(
        record.id,
        record.source_revision,
        metric_hash,
        rule_set,
        rule_file_hash,
        _ENGINE_VERSION,
        threshold_basis,
    )

    target = db.scalar(
        select(KinematicReviewFindingSet).where(
            KinematicReviewFindingSet.annotation_metric_id == record.id,
            KinematicReviewFindingSet.generation_signature == signature,
        )
    )
    if target is None or target.status != "ready":
        raise ReviewFindingsGenerationError(
            "review_findings_not_generated", "尚未生成当前规则/版本的复核发现", status.HTTP_404_NOT_FOUND
        )
    return target

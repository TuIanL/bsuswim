import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationFile, AnnotationFileStatus
from app.models.normalized_annotation import NormalizedAnnotation
from app.repositories.normalized_annotation_repository import get_by_annotation_file
from app.schemas.normalized_annotation import AnnotationQuality, NormalizedAnnotationCreate
from app.services.quality_checker import evaluate_quality


def update_annotation_file_status(
    db: Session, annotation_file: AnnotationFile, success: bool, error_message: str | None = None
) -> None:
    """联动更新 annotation_files.status：成功 → parsed，失败 → parse_failed + parse_error。"""
    if success:
        annotation_file.status = AnnotationFileStatus.PARSED
        annotation_file.parse_error = None
    else:
        annotation_file.status = AnnotationFileStatus.PARSE_FAILED
        annotation_file.parse_error = error_message or "解析失败"
    db.add(annotation_file)
    db.commit()


def create_normalized_annotation(
    db: Session,
    *,
    session_video_id: int,
    data: NormalizedAnnotationCreate,
    created_by: int,
) -> NormalizedAnnotation:
    """从 JSON 数据创建标准化标注记录。"""
    quality = evaluate_quality(
        fps=data.fps,
        events=[e.model_dump() for e in data.events],
        keypoint_frames=[k.model_dump() for k in data.keypoint_frames],
        scale=data.scale.model_dump() if data.scale else None,
        frame_count=data.frame_count,
    )

    ann = NormalizedAnnotation(
        session_video_id=session_video_id,
        annotation_file_id=data.annotation_file_id,
        source=data.source.value,
        fps=data.fps,
        frame_count=data.frame_count,
        duration_sec=data.duration_sec,
        scale=data.scale.model_dump() if data.scale else None,
        coordinate_system=data.coordinate_system.model_dump(),
        events=[e.model_dump() for e in data.events],
        keypoint_frames=[k.model_dump() for k in data.keypoint_frames],
        trajectories=[t.model_dump() for t in data.trajectories],
        manual_tags=[t.model_dump() for t in data.manual_tags],
        quality=quality.model_dump(),
        created_by=created_by,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


def parse_annotation_file(
    db: Session,
    annotation_file_id: int,
    created_by: int,
) -> NormalizedAnnotation:
    """解析 annotation_file 生成 normalized annotation（MVP 骨架版）。"""
    ann_file = db.get(AnnotationFile, annotation_file_id)
    if not ann_file:
        raise HTTPException(status_code=404, detail="标注文件不存在")

    # 尝试解析：只对 manual_json / json 类型做简单 JSON 读取
    if ann_file.file_type == "json":
        try:
            file_path = ann_file.storage_path
            with open(file_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            update_annotation_file_status(db, ann_file, success=False, error_message=str(exc))
            raise HTTPException(status_code=400, detail=f"标注文件读取或解析失败: {exc}")
    elif ann_file.file_type == "csv":
        # CSV 解析留到 Change 2.5
        update_annotation_file_status(
            db, ann_file, success=False,
            error_message="Kinovea CSV parser will be implemented in Change 2.5"
        )
        raise HTTPException(
            status_code=501,
            detail="Kinovea CSV parser not implemented yet. Will be available in Change 2.5.",
        )
    else:
        # 尝试作为 JSON 读取
        try:
            file_path = ann_file.storage_path
            with open(file_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception:
            update_annotation_file_status(
                db, ann_file, success=False,
                error_message=f"不支持的文件类型: {ann_file.file_type}"
            )
            raise HTTPException(status_code=400, detail=f"无法解析此文件类型: {ann_file.file_type}")

    # 从 JSON 提取数据
    session_video_id = ann_file.session_video_id
    fps = raw.get("fps", float(ann_file.annotation_fps or 60))
    events = raw.get("events", [])
    keypoint_frames = raw.get("keypoint_frames", [])
    scale = raw.get("scale")
    frame_count = raw.get("frame_count") or raw.get("video", {}).get("frame_count")

    quality = evaluate_quality(
        fps=fps,
        events=events,
        keypoint_frames=keypoint_frames,
        scale=scale,
        frame_count=frame_count,
    )

    # upsert
    existing = get_by_annotation_file(db, annotation_file_id)
    if existing:
        existing.revision += 1
        existing.source = ann_file.source.value
        existing.fps = fps
        existing.frame_count = frame_count
        existing.scale = scale
        existing.events = events
        existing.keypoint_frames = keypoint_frames
        existing.trajectories = raw.get("trajectories", [])
        existing.manual_tags = raw.get("manual_tags", [])
        existing.quality = quality.model_dump()
        existing.annotation_metadata = raw.get("metadata", {})
        ann = existing
        db.add(ann)
    else:
        ann = NormalizedAnnotation(
            session_video_id=session_video_id,
            annotation_file_id=annotation_file_id,
            source=ann_file.source.value,
            fps=fps,
            frame_count=frame_count,
            duration_sec=float(ann_file.duration_sec) if ann_file.duration_sec else None,
            scale=scale,
            events=events,
            keypoint_frames=keypoint_frames,
            trajectories=raw.get("trajectories", []),
            manual_tags=raw.get("manual_tags", []),
            quality=quality.model_dump(),
            annotation_metadata=raw.get("metadata", {}),
            created_by=created_by,
        )
        db.add(ann)

    db.commit()
    db.refresh(ann)

    # 联动更新 annotation_files.status
    update_annotation_file_status(db, ann_file, success=True)
    return ann

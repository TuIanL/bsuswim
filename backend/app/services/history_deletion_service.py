"""Hard-delete a coach-owned training history and its registered upload artifacts."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AnalysisResult,
    AnalysisTask,
    AnalysisTaskStatus,
    AnnotationFile,
    AnnotationMetric,
    KinematicArtifact,
    KinematicArtifactSet,
    KinematicReviewFindingSet,
    NormalizedAnnotation,
    ReportMetadata,
    SessionVideo,
    StorageCleanupFailure,
    TrainingSession,
    VideoFile,
)


class HistoryNotFoundError(Exception):
    pass


class ActiveAnalysisTaskError(Exception):
    pass


class UnsafeStoragePathError(Exception):
    pass


class StorageCleanupError(Exception):
    def __init__(self, failure_ids: list[int]):
        self.failure_ids = failure_ids
        super().__init__("关联文件未能全部删除")


@dataclass(frozen=True)
class CleanupPath:
    path: Path


def _upload_root() -> Path:
    return get_settings().upload_dir.resolve()


def resolve_upload_path(storage_path: str) -> Path:
    """Resolve a persisted path only when it remains inside the upload root."""
    if not storage_path or "\x00" in storage_path:
        raise UnsafeStoragePathError("存储路径无效")
    root = _upload_root()
    raw_path = Path(storage_path)
    candidate = raw_path.resolve() if raw_path.is_absolute() else (root / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise UnsafeStoragePathError("存储路径位于上传目录之外") from exc
    return candidate


def _paths(values: Iterable[str | None]) -> list[CleanupPath]:
    unique: dict[Path, CleanupPath] = {}
    for value in values:
        if value:
            path = resolve_upload_path(value)
            unique[path] = CleanupPath(path)
    return list(unique.values())


def _remove_path(path: Path) -> None:
    if path.is_dir():
        path.rmdir()
    elif path.exists() or path.is_symlink():
        path.unlink()


def _prune_empty_parents(path: Path) -> None:
    root = _upload_root()
    protected = {root, root / "kinematic-artifacts", root / "reports"}
    parent = path.parent
    while parent not in protected and parent != root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _record_cleanup_failures(db: Session, coach_id: int, session_id: int, failures: list[tuple[Path, Exception]]) -> list[int]:
    records = [
        StorageCleanupFailure(
            coach_id=coach_id,
            session_id=session_id,
            storage_path=str(path.relative_to(_upload_root())),
            error_message=str(error),
            status="pending",
            retry_count=1,
            last_attempt_at=datetime.now(timezone.utc),
        )
        for path, error in failures
    ]
    db.add_all(records)
    db.commit()
    return [record.id for record in records]


def _delete_registered_files(db: Session, coach_id: int, session_id: int, paths: list[CleanupPath]) -> None:
    failures: list[tuple[Path, Exception]] = []
    for entry in paths:
        try:
            _remove_path(entry.path)
            _prune_empty_parents(entry.path)
        except OSError as exc:
            failures.append((entry.path, exc))
    if failures:
        raise StorageCleanupError(_record_cleanup_failures(db, coach_id, session_id, failures))


def delete_training_history(db: Session, session_id: int, coach_id: int) -> None:
    session = db.scalar(
        select(TrainingSession).where(TrainingSession.id == session_id, TrainingSession.coach_id == coach_id)
    )
    if session is None:
        raise HistoryNotFoundError()

    tasks = list(db.scalars(select(AnalysisTask).where(AnalysisTask.session_id == session.id)).all())
    terminal = {AnalysisTaskStatus.COMPLETED, AnalysisTaskStatus.FAILED}
    if any(task.status not in terminal for task in tasks):
        raise ActiveAnalysisTaskError()

    links = list(db.scalars(select(SessionVideo).where(SessionVideo.session_id == session.id)).all())
    video_ids = [link.video_file_id for link in links]
    annotations = list(db.scalars(select(AnnotationFile).where(AnnotationFile.session_video_id.in_([link.id for link in links]))).all()) if links else []
    normalized = list(db.scalars(select(NormalizedAnnotation).where(NormalizedAnnotation.session_video_id.in_([link.id for link in links]))).all()) if links else []
    normalized_ids = [item.id for item in normalized]
    metrics = list(db.scalars(select(AnnotationMetric).where(AnnotationMetric.normalized_annotation_id.in_(normalized_ids))).all()) if normalized_ids else []
    metric_ids = [item.id for item in metrics]
    artifact_sets = list(db.scalars(select(KinematicArtifactSet).where(KinematicArtifactSet.annotation_metric_id.in_(metric_ids))).all()) if metric_ids else []
    artifact_set_ids = [item.id for item in artifact_sets]
    artifacts = list(db.scalars(select(KinematicArtifact).where(KinematicArtifact.artifact_set_id.in_(artifact_set_ids))).all()) if artifact_set_ids else []
    findings = list(db.scalars(select(KinematicReviewFindingSet).where(KinematicReviewFindingSet.annotation_metric_id.in_(metric_ids))).all()) if metric_ids else []
    reports = list(db.scalars(select(ReportMetadata).where(ReportMetadata.session_id == session.id)).all())
    results = list(db.scalars(select(AnalysisResult).where(AnalysisResult.task_id.in_([task.id for task in tasks]))).all()) if tasks else []

    # Validate every registered path before any database record is removed.
    file_paths = _paths(
        [annotation.storage_path for annotation in annotations]
        + [artifact.storage_path for artifact in artifacts]
        + [report.pdf_path for report in reports]
    )
    # Validate video paths up front even though shared videos are not scheduled for removal.
    # This prevents a malformed record from partially deleting a session before it is noticed.
    _paths([video.storage_path for video in (db.get(VideoFile, video_id) for video_id in set(video_ids)) if video])

    try:
        for report in reports:
            db.delete(report)
        for result in results:
            db.delete(result)
        for finding in findings:
            db.delete(finding)
        for artifact in artifacts:
            db.delete(artifact)
        for artifact_set in artifact_sets:
            db.delete(artifact_set)
        for metric in metrics:
            db.delete(metric)
        for annotation in normalized:
            db.delete(annotation)
        for annotation in annotations:
            db.delete(annotation)
        for task in tasks:
            db.delete(task)
        for link in links:
            db.delete(link)
        db.flush()

        orphan_videos: list[VideoFile] = []
        for video_id in set(video_ids):
            if db.scalar(select(func.count()).select_from(SessionVideo).where(SessionVideo.video_file_id == video_id)) == 0:
                video = db.get(VideoFile, video_id)
                if video is not None:
                    file_paths.extend(_paths([video.storage_path]))
                    orphan_videos.append(video)
        for video in orphan_videos:
            db.delete(video)
        db.delete(session)
        db.commit()
    except Exception:
        db.rollback()
        raise

    _delete_registered_files(db, coach_id, session_id, file_paths)


def retry_storage_cleanup(db: Session, failure_id: int, coach_id: int) -> bool:
    failure = db.scalar(
        select(StorageCleanupFailure).where(
            StorageCleanupFailure.id == failure_id,
            StorageCleanupFailure.coach_id == coach_id,
            StorageCleanupFailure.resolved_at.is_(None),
        )
    )
    if failure is None:
        raise HistoryNotFoundError()
    try:
        path = resolve_upload_path(failure.storage_path)
        _remove_path(path)
        _prune_empty_parents(path)
    except (OSError, UnsafeStoragePathError) as exc:
        failure.retry_count += 1
        failure.last_attempt_at = datetime.now(timezone.utc)
        failure.error_message = str(exc)
        failure.status = "pending"
        db.commit()
        return False

    failure.retry_count += 1
    failure.last_attempt_at = datetime.now(timezone.utc)
    failure.resolved_at = datetime.now(timezone.utc)
    failure.status = "resolved"
    db.commit()
    return True

"""API routes for kinematic visual artifacts."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.models.annotation_metric import AnnotationMetric
from app.models.kinematic_artifact import KinematicArtifactSet
from app.schemas.kinematic_artifact import (
    GenerateResponse,
    KinematicArtifactSetRead,
)
from app.services.kinematic_artifacts.generation_service import GenerationError, generate

router = APIRouter()


@router.post(
    "/annotation-metrics/{annotation_metric_id}/artifacts/generate",
    response_model=GenerateResponse,
)
def generate_artifacts(
    annotation_metric_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        artifact_set, created = generate(
            db, annotation_metric_id, force=force, current_user_id=current_user.id
        )
    except GenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code})
    except Exception as exc:  # systemic failure
        raise HTTPException(status_code=500, detail={"code": "render_failed", "message": str(exc)})
    return GenerateResponse(
        artifact_set_id=artifact_set.id,
        status=artifact_set.status,
        created=created,
    )


@router.get(
    "/annotation-metrics/{annotation_metric_id}/artifacts",
    response_model=KinematicArtifactSetRead,
)
def get_artifacts(
    annotation_metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metric = db.get(AnnotationMetric, annotation_metric_id)
    if metric is None:
        raise HTTPException(status_code=404, detail={"code": "metric_unavailable"})

    artifact_set = (
        db.query(KinematicArtifactSet)
        .filter_by(annotation_metric_id=annotation_metric_id)
        .order_by(KinematicArtifactSet.created_at.desc())
        .first()
    )
    if artifact_set is None:
        raise HTTPException(status_code=404, detail={"code": "metric_unavailable"})
    return artifact_set.manifest

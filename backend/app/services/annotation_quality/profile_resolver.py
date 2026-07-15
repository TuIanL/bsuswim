from app.models.annotation import AnnotationSource


def resolve_quality_profile_id(
    source: str | AnnotationSource,
) -> str:
    value = getattr(source, "value", source)
    if value == AnnotationSource.CVAT.value:
        return "side_technical_v1_cvat"
    return "side_technical_v1"

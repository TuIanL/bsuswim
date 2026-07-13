"""Annotation parsers.

Pure-data parsers that turn annotation exports (Kinovea JSON/CSV, CVAT XML)
into normalized data objects. They never touch the database.
"""

from app.services.parsers.kinovea_parser import (
    KinoveaParseError,
    ParsedKinoveaAnnotation,
    build_parse_summary,
    build_semantic_warnings,
    parse_kinovea_annotation,
    parse_kinovea_csv,
    parse_kinovea_json,
    resolve_time_sec,
)

from app.services.parsers.cvat_xml import (
    CvatParseError,
    ParsedCvatAnnotation,
    parse_cvat_xml,
)

from app.services.parsers.frame_mapping import (
    FrameMapping,
    FrameMappingEntry,
    FrameMappingResolver,
)

from app.services.parsers.cvat_normalizer import (
    CvatAnnotationNormalizer,
)

__all__ = [
    "KinoveaParseError",
    "ParsedKinoveaAnnotation",
    "build_parse_summary",
    "build_semantic_warnings",
    "parse_kinovea_annotation",
    "parse_kinovea_csv",
    "parse_kinovea_json",
    "resolve_time_sec",
    "CvatParseError",
    "ParsedCvatAnnotation",
    "parse_cvat_xml",
    "FrameMapping",
    "FrameMappingEntry",
    "FrameMappingResolver",
    "CvatAnnotationNormalizer",
]

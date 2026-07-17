from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any, Literal

from app.schemas.normalized_annotation import (
    ParsedCvatAnnotation,
    RawCvatKeypointFrame,
    RawCvatPoint,
)


class CvatParseError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        frame: int | None = None,
        track_ids: list[str] | None = None,
    ):
        self.code = code
        self.frame = frame
        self.track_ids = track_ids
        self.message = message
        super().__init__(message)


MAX_XML_FILE_SIZE_BYTES = 100 * 1024 * 1024
MAX_SKELETON_RECORDS = 50000
MAX_ACTIVE_FRAMES = 20000
MAX_POINTS_PER_SKELETON = 150
MAX_WARNINGS = 100

COCO_SKELETON_KEYPOINTS: set[str] = {
    "nose", "left-eye", "right-eye", "left-ear", "right-ear",
    "left-shoulder", "right-shoulder",
    "left-elbow", "right-elbow",
    "left-wrist", "right-wrist",
    "left-hip", "right-hip",
    "left-knee", "right-knee",
    "left-ankle", "right-ankle",
}


def _normalize_point_name(name: str) -> str:
    return name.strip().lower().replace("-", "_")


def _is_safe_coordinate(value: str) -> bool:
    try:
        f = float(value)
        if f != f or f == float("inf") or f == float("-inf") or f < 0:
            return False
        return True
    except (ValueError, TypeError):
        return False


def _has_dtd_or_entities(file_path: str) -> bool:
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        head = fh.read(4096)
    if "<!ENTITY" in head.upper() or "<!DOCTYPE" in head.upper():
        return True
    return False


def parse_cvat_xml(file_path: str) -> ParsedCvatAnnotation:
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise CvatParseError("EMPTY_FILE", "Empty XML file")
    if file_size > MAX_XML_FILE_SIZE_BYTES:
        raise CvatParseError(
            "FILE_TOO_LARGE",
            f"XML file size ({file_size}) exceeds limit {MAX_XML_FILE_SIZE_BYTES}",
        )
    if _has_dtd_or_entities(file_path):
        raise CvatParseError(
            "SECURITY_REJECTED",
            "XML contains DTD or entity declarations, rejected for security",
        )

    meta: dict[str, Any] = {}
    raw_tracks: list[dict[str, Any]] = []
    warnings: list[str] = []
    skeleton_count = 0
    version = "unknown"

    try:
        for event, elem in ET.iterparse(file_path, events=("start", "end")):
            tag = elem.tag

            if event == "start" and tag == "annotations":
                version = elem.get("version", "unknown")

            if event == "end" and tag == "annotations":
                version_el = elem.find("version")
                if version_el is not None and version_el.text:
                    version = version_el.text

            if event == "end" and tag == "meta":
                meta = _extract_meta_from_element(elem)

            if event == "end" and tag == "track":
                for skel in elem.findall("skeleton"):
                    skeleton_count += 1
                    if skeleton_count > MAX_SKELETON_RECORDS:
                        warnings.append(
                            f"skeleton record count exceeds limit {MAX_SKELETON_RECORDS}"
                        )
                        elem.clear()
                        continue

                    frame_str = skel.get("frame", "")
                    try:
                        frame = int(frame_str)
                    except (ValueError, TypeError):
                        continue

                    label = elem.get("label", "")
                    track_id = elem.get("id", "")
                    source = elem.get("source", "manual")

                    points_list: list[dict[str, Any]] = []
                    for pt in skel.findall("points"):
                        pt_label = pt.get("label", "")
                        outside = pt.get("outside", "0")
                        occluded = pt.get("occluded", "0")
                        points_str = pt.get("points", "")
                        points_list.append({
                            "label": pt_label,
                            "outside": outside,
                            "occluded": occluded,
                            "points": points_str,
                        })

                    raw_tracks.append({
                        "track_id": track_id,
                        "label": label,
                        "source": source,
                        "frame": frame,
                        "points": points_list,
                    })

                elem.clear()

    except ET.ParseError as exc:
        raise CvatParseError("XML_PARSE_ERROR", f"XML parse error: {exc}")

    if skeleton_count > MAX_SKELETON_RECORDS:
        raise CvatParseError(
            "SKELETON_LIMIT_EXCEEDED",
            f"skeleton record count ({skeleton_count}) exceeds limit {MAX_SKELETON_RECORDS}",
        )

    keypoint_frames, agg_warnings = _aggregate_by_frame(raw_tracks)
    all_warnings = warnings + agg_warnings

    if len(keypoint_frames) > MAX_ACTIVE_FRAMES:
        raise CvatParseError(
            "ACTIVE_FRAME_LIMIT_EXCEEDED",
            f"active frame count ({len(keypoint_frames)}) exceeds limit {MAX_ACTIVE_FRAMES}",
        )

    parsed_frames: list[RawCvatKeypointFrame] = []
    for raw_skel in keypoint_frames:
        kf = _skeleton_to_raw_frame(raw_skel)
        if len(kf.points) > MAX_POINTS_PER_SKELETON:
            raise CvatParseError(
                "POINTS_LIMIT_EXCEEDED",
                f"Frame {kf.annotation_frame} has {len(kf.points)} points, "
                f"exceeds limit {MAX_POINTS_PER_SKELETON}",
                frame=kf.annotation_frame,
            )
        if any(p.visibility != "missing" for p in kf.points.values()):
            parsed_frames.append(kf)

    if len(all_warnings) > MAX_WARNINGS:
        all_warnings = all_warnings[:MAX_WARNINGS]
        all_warnings.append("Warning count exceeded limit, truncated")

    native_metadata = {
        "version": version,
        "meta": meta,
        "parsed_track_count": len(raw_tracks),
        "parsed_frame_count": len(parsed_frames),
    }

    return ParsedCvatAnnotation(
        raw_keypoint_frames=parsed_frames,
        native_metadata=native_metadata,
        warnings=all_warnings,
    )


def _extract_meta_from_element(meta_el: ET.Element) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    job_el = meta_el.find("job")
    if job_el is not None:
        for field in ("id", "size", "start_frame", "stop_frame", "mode"):
            el = job_el.find(field)
            if el is not None and el.text:
                try:
                    meta[field] = int(el.text)
                except ValueError:
                    meta[field] = el.text
        labels_el = job_el.find("labels")
        if labels_el is not None:
            label_names: list[str] = []
            for label_el in labels_el.findall("label"):
                name_el = label_el.find("name")
                if name_el is not None and name_el.text:
                    label_names.append(name_el.text)
            meta["labels"] = label_names
        owner_el = job_el.find("owner")
        if owner_el is not None:
            username_el = owner_el.find("username")
            if username_el is not None:
                meta["owner"] = username_el.text or ""
    dumped_el = meta_el.find("dumped")
    if dumped_el is not None and dumped_el.text:
        meta["dumped"] = dumped_el.text
    return meta


def _aggregate_by_frame(
    tracks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    frames_map: dict[int, list[dict[str, Any]]] = {}
    warnings: list[str] = []

    for t in tracks:
        frame = t["frame"]
        outside_all = all(p["outside"] == "1" for p in t["points"])
        if outside_all:
            continue
        frames_map.setdefault(frame, []).append(t)

    result: list[dict[str, Any]] = []
    for frame in sorted(frames_map.keys()):
        skeletons = frames_map[frame]
        active = [s for s in skeletons if not all(
            p["outside"] == "1" for p in s["points"]
        )]
        if not active:
            continue
        if len(active) > 1:
            track_ids = [a["track_id"] for a in active]
            raise CvatParseError(
                "MULTIPLE_ACTIVE_SKELETONS",
                f"Multiple active skeletons at frame {frame}: "
                f"tracks {', '.join(track_ids)}. "
                "Multiple active skeletons in one frame are not supported.",
                frame=frame,
                track_ids=track_ids,
            )
        result.append(active[0])
    return result, warnings


def _skeleton_to_raw_frame(
    skeleton: dict[str, Any],
) -> RawCvatKeypointFrame:
    frame = skeleton["frame"]
    points: dict[str, RawCvatPoint] = {}
    source_track_ids: list[str] = [skeleton["track_id"]]

    for pt in skeleton["points"]:
        raw_label = pt.get("label", "")
        norm_name = _normalize_point_name(raw_label)
        outside = pt.get("outside", "0")
        occluded = pt.get("occluded", "0")

        if outside == "1":
            points[norm_name] = RawCvatPoint(
                x=None, y=None, visibility="missing"
            )
            continue

        points_str = pt.get("points", "")
        if not points_str:
            points[norm_name] = RawCvatPoint(
                x=None, y=None, visibility="missing"
            )
            continue

        parts = points_str.split(",")
        if len(parts) != 2:
            continue
        x_str, y_str = parts[0].strip(), parts[1].strip()
        if not _is_safe_coordinate(x_str) or not _is_safe_coordinate(y_str):
            raise CvatParseError(
                "INVALID_COORDINATE",
                f"Invalid coordinate at frame {frame}, "
                f"point {raw_label}: ({x_str}, {y_str})",
                frame=frame,
            )
        x, y = float(x_str), float(y_str)

        if occluded == "1":
            visibility: Literal["visible", "occluded", "missing"] = "occluded"
        else:
            visibility = "visible"

        points[norm_name] = RawCvatPoint(x=x, y=y, visibility=visibility)

    return RawCvatKeypointFrame(
        annotation_frame=frame,
        points=points,
        source_track_ids=source_track_ids,
    )

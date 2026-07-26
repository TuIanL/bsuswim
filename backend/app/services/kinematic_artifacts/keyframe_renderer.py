"""Annotated keyframe renderer (OpenCV).

Draws the COCO17 skeleton, body axis, joint-angle arcs and objective metric
values onto an extracted video frame. Crops around the skeleton bbox with a
15% margin and preserves aspect ratio.
"""

import math
from pathlib import Path

import cv2
import numpy as np

from app.services.kinematic_artifacts.constants import KEYFRAME_WIDTH, KEYFRAME_HEIGHT
from app.services.metrics.kinematics.frame_resolver import CanonicalKinematicFrame

# COCO17 keypoint name order (subset used for edges).
COCO17_KEYPOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

# Skeleton edges by keypoint name.
SKELETON_EDGES = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    ("left_shoulder", "left_hip"),  # torso axis helper
    ("right_shoulder", "right_hip"),
]

CROP_MARGIN = 0.15
VISIBLE_COLOR = (0, 200, 255)
OCCLUDED_COLOR = (80, 120, 160)
ESTIMATED_COLOR = (200, 200, 60)
BODY_AXIS_COLOR = (0, 255, 0)


def _font_path() -> str | None:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    return next((path for path in candidates if Path(path).is_file()), None)


def _draw_text(img, text: str, xy: tuple[int, int], size: int, color=(20, 20, 20)):
    """Draw Unicode text with Pillow, falling back to OpenCV for ASCII-only text."""
    if not text:
        return
    font_path = _font_path()
    if font_path:
        from PIL import Image, ImageDraw, ImageFont

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        canvas = Image.fromarray(rgb)
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(font_path, size=size)
        draw.text(xy, text, fill=tuple(reversed(color)), font=font)
        img[:] = cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)
        return
    if any(ord(char) > 127 for char in text):
        text = "Reference: screen horizontal" if "水平" in text else "Diagnostic keyframe"
    cv2.putText(img, text, xy, cv2.FONT_HERSHEY_SIMPLEX, max(size / 32, 0.5), color, 2)


def _point_xy(p) -> tuple[float, float] | None:
    if p is None or not getattr(p, "available", False) or p.x is None or p.y is None:
        return None
    return (float(p.x), float(p.y))


def _draw_joint(img, p, color):
    xy = _point_xy(p)
    if xy is None:
        return
    x, y = int(round(xy[0])), int(round(xy[1]))
    cv2.circle(img, (x, y), 6, color, -1)


def _color_for(p):
    if not getattr(p, "available", False):
        return None
    mode = getattr(p, "mode", "bilateral_midpoint")
    if mode == "unavailable":
        return None
    if mode == "estimated" or mode == "single_side_proxy":
        return ESTIMATED_COLOR
    return VISIBLE_COLOR


def _draw_skeleton(img, frame: CanonicalKinematicFrame):
    pts = frame.points
    for a, b in SKELETON_EDGES:
        pa, pb = pts.get(a), pts.get(b)
        xy_a, xy_b = _point_xy(pa), _point_xy(pb)
        if xy_a is None or xy_b is None:
            continue
        color_a = _color_for(pa)
        color = color_a or _color_for(pb) or OCCLUDED_COLOR
        cv2.line(img, (int(xy_a[0]), int(xy_a[1])), (int(xy_b[0]), int(xy_b[1])), color, 2)
    for name in COCO17_KEYPOINTS:
        p = pts.get(name)
        if p is None:
            continue
        c = _color_for(p)
        if c:
            _draw_joint(img, p, c)


def _draw_body_axis(img, frame: CanonicalKinematicFrame):
    sh, hip = frame.shoulder_mid, frame.hip_mid
    a, b = _point_xy(sh), _point_xy(hip)
    if a is None or b is None:
        return
    cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), BODY_AXIS_COLOR, 3)


def _draw_angle_arc(img, p_center, p_a, p_b, label: str | None = None):
    c, a, b = _point_xy(p_center), _point_xy(p_a), _point_xy(p_b)
    if c is None or a is None or b is None:
        return
    ang = math.degrees(math.atan2(b[1] - c[1], b[0] - c[0]) - math.atan2(a[1] - c[1], a[0] - c[0]))
    ang = abs(ang) if ang >= 0 else abs(ang + 360)
    cv2.ellipse(img, (int(c[0]), int(c[1])), (24, 24), 0, 0, int(ang), (255, 255, 255), 2)
    if label:
        cv2.putText(img, label, (int(c[0]) + 28, int(c[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def _skeleton_bbox(frame: CanonicalKinematicFrame) -> tuple[int, int, int, int] | None:
    xs, ys = [], []
    for p in list(frame.points.values()) + [frame.shoulder_mid, frame.hip_mid, frame.ankle_mid, frame.head_center]:
        xy = _point_xy(p)
        if xy is not None:
            xs.append(xy[0])
            ys.append(xy[1])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def render_keyframe(
    image: np.ndarray,
    frame: CanonicalKinematicFrame,
    *,
    angle_overlay: dict | None = None,
    reference_basis_label: str = "相对画面水平线",
    value_label: str | None = None,
    title_label: str | None = None,
) -> np.ndarray:
    """Render an annotated keyframe. Returns a KEYFRAME_WIDTH x KEYFRAME_HEIGHT BGR image."""
    h, w = image.shape[:2]
    bbox = _skeleton_bbox(frame)
    if bbox is None:
        raise ValueError("no skeleton points to crop")
    x0, y0, x1, y1 = bbox
    mw, mh = (x1 - x0) * CROP_MARGIN, (y1 - y0) * CROP_MARGIN
    x0, y0, x1, y1 = max(0, int(x0 - mw)), max(0, int(y0 - mh)), min(w, int(x1 + mw)), min(h, int(y1 + mh))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("empty crop region")
    crop = image[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    if cw <= 0 or ch <= 0:
        raise ValueError("empty crop region")
    scale = min(KEYFRAME_WIDTH / cw, KEYFRAME_HEIGHT / ch)
    tw, th = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    resized = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA)
    canvas = np.full((KEYFRAME_HEIGHT, KEYFRAME_WIDTH, 3), 240, dtype=np.uint8)
    off_x = (KEYFRAME_WIDTH - resized.shape[1]) // 2
    off_y = (KEYFRAME_HEIGHT - resized.shape[0]) // 2
    canvas[off_y:off_y + resized.shape[0], off_x:off_x + resized.shape[1]] = resized

    # Build a shifted frame so overlay coords match canvas.
    shifted = _shift_frame(frame, -x0 * scale + off_x, -y0 * scale + off_y, scale)
    _draw_skeleton(canvas, shifted)
    _draw_body_axis(canvas, shifted)
    if angle_overlay:
        _draw_angle_arc(canvas, shifted.points.get(angle_overlay["center"]),
                        shifted.points.get(angle_overlay["a"]), shifted.points.get(angle_overlay["b"]),
                        angle_overlay.get("label"))

    _draw_text(canvas, reference_basis_label, (20, KEYFRAME_HEIGHT - 55), 28)
    if value_label:
        _draw_text(canvas, value_label, (20, 78), 32)
    if title_label:
        _draw_text(canvas, title_label, (20, 42), 36)
    return canvas


def _shift_frame(frame: CanonicalKinematicFrame, dx: float, dy: float, scale: float):
    """Return a shallow copy of the frame with all coordinates transformed for cropping."""
    import copy

    f = copy.copy(frame)
    def shift(p):
        if p is None:
            return None
        np_copy = copy.copy(p)
        if np_copy.x is not None:
            np_copy.x = np_copy.x * scale + dx
        if np_copy.y is not None:
            np_copy.y = np_copy.y * scale + dy
        return np_copy
    f.points = {k: shift(v) for k, v in frame.points.items()}
    f.shoulder_mid = shift(frame.shoulder_mid)
    f.hip_mid = shift(frame.hip_mid)
    f.ankle_mid = shift(frame.ankle_mid)
    f.head_center = shift(frame.head_center)
    return f

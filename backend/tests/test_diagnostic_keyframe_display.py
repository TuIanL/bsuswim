import cv2
import numpy as np

from app.schemas.kinematics_report import ReportAsset
from app.services.kinematic_artifacts.frame_provider import KinematicFrameSequenceProvider
from app.services.kinematic_artifacts.keyframe_renderer import render_keyframe
from app.services.kinematic_artifacts.presentation import keyframe_presentation
from app.services.metrics.kinematics.frame_resolver import resolve_frames
from fixtures.synthetic_kinematics import build_golden_annotation


def test_keyframe_presentation_is_factual_and_localized():
    presentation = keyframe_presentation("upper_limb.keyframe.left_elbow_min")

    assert presentation.title == "左肘角最小"
    assert presentation.metric_label == "左肘角"
    assert presentation.unit == "°"
    assert "动作阶段" not in presentation.caption


def test_report_asset_keeps_keyframe_trace_fields():
    asset = ReportAsset(
        key="upper_limb.keyframe.left_elbow_min",
        type="annotated_frame",
        title="左肘角最小",
        url="/uploads/keyframe.png",
        artifact_type="annotated_keyframe",
        module_key="upper_limb",
        metric_keys=["left_elbow_angle_deg"],
        metric_label="左肘角",
        unit="°",
        value="82.5",
        annotation_frame=12,
        source_video_frame=44,
        source_annotation_revision=3,
    )

    assert asset.metric_label == "左肘角"
    assert asset.annotation_frame == 12
    assert asset.source_video_frame == 44
    assert asset.source_annotation_revision == 3


def test_keyframe_renderer_returns_fixed_size_without_question_mark_text():
    annotation = build_golden_annotation()
    normalized = type(
        "Annotation",
        (),
        {"keypoint_frames": annotation["keypoint_frames"]},
    )()
    frame = KinematicFrameSequenceProvider().build(normalized)[0]
    image = render_keyframe(
        np.zeros((480, 640, 3), dtype=np.uint8),
        frame,
        reference_basis_label="相对画面水平线",
        title_label="左肘角最小",
        value_label="82.5 °",
    )

    assert image.shape == (900, 1600, 3)
    ok, encoded = cv2.imencode(".png", image)
    assert ok and len(encoded) > 0
    assert encoded.tobytes()

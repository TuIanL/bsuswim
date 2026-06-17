from app.schemas import AnalysisRequest, AnalysisResponse


class SwimModelRuntime:
    """Runtime boundary for future YOLO/MMPose inference."""

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        primary_video = request.videos[0] if request.videos else None
        view_type = primary_video.view_type if primary_video else "unknown"
        return AnalysisResponse(
            detections=[
                {
                    "time": 0.0,
                    "bbox": [0.18, 0.36, 0.34, 0.18],
                    "label": "swimmer",
                    "confidence": 0.93,
                    "view_type": view_type,
                },
                {
                    "time": 1.5,
                    "bbox": [0.28, 0.34, 0.35, 0.2],
                    "label": "swimmer",
                    "confidence": 0.91,
                    "view_type": view_type,
                },
                {
                    "time": 3.0,
                    "bbox": [0.42, 0.35, 0.33, 0.19],
                    "label": "swimmer",
                    "confidence": 0.9,
                    "view_type": view_type,
                },
            ],
            keypoint_frames=[
                {
                    "time": 0.0,
                    "video_file_id": primary_video.video_file_id if primary_video else None,
                    "points": [
                        {"name": "head", "x": 0.28, "y": 0.39, "score": 0.92},
                        {"name": "shoulder", "x": 0.36, "y": 0.43, "score": 0.9},
                        {"name": "hip", "x": 0.48, "y": 0.48, "score": 0.88},
                        {"name": "knee", "x": 0.6, "y": 0.5, "score": 0.85},
                    ],
                },
                {
                    "time": 1.5,
                    "video_file_id": primary_video.video_file_id if primary_video else None,
                    "points": [
                        {"name": "head", "x": 0.38, "y": 0.38, "score": 0.91},
                        {"name": "shoulder", "x": 0.45, "y": 0.43, "score": 0.9},
                        {"name": "hip", "x": 0.57, "y": 0.47, "score": 0.86},
                        {"name": "knee", "x": 0.68, "y": 0.5, "score": 0.84},
                    ],
                },
            ],
            phases=[
                {"start": 0.0, "end": 1.2, "label": "入水与前伸"},
                {"start": 1.2, "end": 2.6, "label": "抱水与推水"},
                {"start": 2.6, "end": 3.8, "label": "换气与恢复"},
            ],
            metrics={
                "overall_score": 81,
                "body_line_score": 78,
                "rhythm_score": 83,
                "symmetry_score": 74,
                "kick_score": 76,
                "stroke_rate": 34,
                "body_angle_stability": 82,
                "breathing_timing": 79,
                "video_count": len(request.videos),
            },
            diagnostics=[
                {
                    "title": "身体中线轻微摆动",
                    "severity": "medium",
                    "evidence": "髋部关键点在推水阶段出现横向波动",
                    "suggestion": "增加侧身打腿和单臂划水练习，稳定核心控制",
                    "expected_improvement": "减少阻力并提高划水连续性",
                    "priority": 1,
                },
                {
                    "title": "换气节奏略早",
                    "severity": "low",
                    "evidence": "头部关键点在推水完成前提前抬升",
                    "suggestion": "用三划一换气节奏练习保持动作同步",
                    "expected_improvement": "改善身体线和呼吸稳定性",
                    "priority": 2,
                },
            ],
            error_message=None,
        )

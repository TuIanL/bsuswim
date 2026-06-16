from datetime import datetime

from app.models import AnalysisResult, AnalysisTask


def build_report_data(task: AnalysisTask, result: AnalysisResult | None = None) -> dict:
    result = result or task.result
    metrics = result.metrics if result else {}
    diagnostics = result.diagnostics if result else []

    return {
        "summary": {
            "title": task.session_metadata.get("session_title", "游泳训练分析"),
            "stroke_type": task.session_metadata.get("stroke_type", "freestyle"),
            "overall_score": metrics.get("overall_score", 0),
            "headline": "基于模型服务输出生成的第一版 HTML 报告",
        },
        "metrics": metrics,
        "diagnostics": diagnostics,
        "recommendations": [
            {
                "title": "保持身体中线稳定",
                "target": "降低左右摆动，提高划水效率",
                "linked_issue": diagnostics[0]["title"] if diagnostics else "body_line",
            },
            {
                "title": "分段复盘呼吸节奏",
                "target": "让呼吸动作与划水阶段更稳定同步",
                "linked_issue": "breathing_timing",
            },
        ],
        "charts": {
            "radar": [
                {"name": "身体线", "value": metrics.get("body_line_score", 78)},
                {"name": "节奏", "value": metrics.get("rhythm_score", 82)},
                {"name": "对称性", "value": metrics.get("symmetry_score", 74)},
                {"name": "打腿", "value": metrics.get("kick_score", 76)},
            ]
        },
        "provenance": {
            "task_id": task.id,
            "source": "model_service",
            "generated_at": datetime.utcnow().isoformat(),
            "schema_version": result.schema_version if result else None,
        },
    }

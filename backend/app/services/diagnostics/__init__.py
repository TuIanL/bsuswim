"""规则诊断引擎服务包。

分层：
- ``adapter``：DiagnosticsMetricsAdapter（annotation_metrics → DiagnosticMetricsContext 契约层）
- ``registry``：RuleRegistry（加载 YAML 规则）
- ``evaluator``：结构化 all/any 条件评估
- ``severity``：severity 解析 + priority_score + 排序
- ``engine``：RuleBasedDiagnosticsEngine（编排）
- ``bridge``：run_diagnostics_for_analysis_result（analysis_result 接线桥）
"""

from app.services.diagnostics.adapter import DiagnosticsMetricsAdapter
from app.services.diagnostics.engine import RuleBasedDiagnosticsEngine
from app.services.diagnostics.registry import RuleRegistry

__all__ = [
    "DiagnosticsMetricsAdapter",
    "RuleBasedDiagnosticsEngine",
    "RuleRegistry",
]

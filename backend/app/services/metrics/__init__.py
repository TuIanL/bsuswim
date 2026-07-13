"""Side-view metrics engine.

纯函数计算层，只读取 normalized annotation（dict 形式），不修改它，也不触碰数据库。
所有指标为事实测量值，不含诊断结论。
"""

from app.services.metrics.engine import calculate_side_view_metrics

__all__ = ["calculate_side_view_metrics"]

"""二维运动学复核发现模块。

包含：
- ``Side2DKinematicsReviewAdapter``：MetricEnvelope → 稳定标量上下文 + 元信息
- ``EvidenceResolver``：证据帧定位（持久化序列优先，标注回退仅用于找帧）
- ``KinematicReviewFindingsEngine``：复用结构化条件评估器生成待复核发现
"""

from app.services.diagnostics.review_findings.adapter import (
    ReviewAdapterResult,
    ReviewMetricMeta,
    Side2DKinematicsReviewAdapter,
)

__all__ = [
    "ReviewAdapterResult",
    "ReviewMetricMeta",
    "Side2DKinematicsReviewAdapter",
]

"""建议映射：为诊断项补充 drill_refs，并保证 recommendation_tags 非空。

规则 YAML 已携带 ``recommendation_tags``；本映射按 category 补充常用训练手段
（drill_refs），使报告与训练计划能直接引用具体 drills。属于展示增强层，不改变诊断逻辑。
"""

from app.services.diagnostics.models import DiagnosticItem

# category → 推荐 drills（参考训练手段库）
_CATEGORY_DRILLS: dict[str, list[str]] = {
    "body_position": ["core_activation", "hip_float_hold", "side_kick_balance"],
    "catch_pull": ["single_arm_freestyle", "paddle_catch", "sculling"],
    "arm_entry": ["finger_tip_entry", "extension_hold"],
    "leg_kick": ["ankle_mobility", "hip_driven_kick", "compact_kick"],
    "efficiency": ["tempo_trainer", "stroke_length_hold"],
}

# category → 默认 recommendation_tags（当规则未指定时回填）
_CATEGORY_TAGS: dict[str, list[str]] = {
    "body_position": ["core_control", "hip_support", "streamline"],
    "catch_pull": ["high_elbow", "catch_area", "propulsion"],
    "arm_entry": ["front_extension", "entry_control"],
    "leg_kick": ["ankle_mobility", "kick_rhythm"],
    "efficiency": ["stroke_efficiency", "tempo_control"],
}


class RecommendationMapper:
    def enrich(self, item: DiagnosticItem) -> DiagnosticItem:
        if not item.recommendation_tags:
            item.recommendation_tags = list(_CATEGORY_TAGS.get(item.category, []))
        if not item.drill_refs:
            item.drill_refs = list(_CATEGORY_DRILLS.get(item.category, []))
        return item

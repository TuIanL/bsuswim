"""建议模板降级文案（按 code）。

当 YAML 未提供 ``suggestion_template``，或渲染后为空时回退，保证每条诊断都有可读建议。
"""

FALLBACKS: dict[str, str] = {
    "low_body_position": "加强核心控制、髋部支撑与低速阶段身体稳定训练。",
    "hip_drop": "强化髋部支撑、核心抗伸展能力和打腿连续性。",
    "body_position_improves_with_speed": "继续巩固高速阶段的身体控制，并向低速阶段迁移。",
    "forearm_press_down": "进行指尖斜插入水、前伸保持和前端支撑稳定性训练。",
    "insufficient_front_reach": "加强前伸保持、单臂前伸和身体流线型控制训练。",
    "insufficient_high_elbow_catch": "进行高肘抱水专项、单臂划水和 Paddle 抓水训练。",
    "insufficient_catch_area": "强化前臂垂直阶段控制，增加有效迎水面积。",
    "low_propulsive_efficiency": "加强抱水—推水衔接训练，提高单次划水推进质量。",
    "excessive_knee_flexion": "进行踝关节柔韧性、髋主导打腿和小幅连续打腿训练。",
    "unstable_kick_rhythm": "进行固定节奏打腿、节拍器配合和分段配速训练。",
    "stroke_rate_compensation": "优化抱水推进效率，提升高速状态下的划幅保持能力。",
    "low_swim_efficiency": "优化划幅保持、抱水推进和节奏稳定性，降低单位距离能量消耗。",
}

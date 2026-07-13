"""原因模板降级文案（按 code）。

当 YAML 未提供 ``reason_template``，或渲染后为空时回退，保证每条诊断都有可读原因。
"""

FALLBACKS: dict[str, str] = {
    "low_body_position": "身体未能保持接近水平的流线型姿态，可能增加迎水阻力。",
    "hip_drop": "髋位下沉会破坏身体流线型，增加身体中后段阻力。",
    "body_position_improves_with_speed": "随着配合节奏提升，下肢支撑和身体流线型有所改善。",
    "forearm_press_down": "前臂过早下压会缩短有效前伸距离，影响后续抱水阶段效率。",
    "insufficient_front_reach": "前端延伸不足会限制入水后的支撑建立，影响后续抱水效率。",
    "insufficient_high_elbow_catch": "肘关节角度偏大时，前臂难以形成稳定有效迎水面，推进效率下降。",
    "insufficient_catch_area": "有效抓水面积不足会降低单次划水推进距离。",
    "low_propulsive_efficiency": "单次划水推进距离不足，可能与抱水面积不足和推水发力不充分有关。",
    "excessive_knee_flexion": "膝关节屈曲过大可能增加迎水阻力，影响打腿推进效率。",
    "unstable_kick_rhythm": "打腿节奏不稳定会影响身体支撑和划水节奏衔接。",
    "stroke_rate_compensation": "速度提升主要依靠提高划频，而非单次划水推进质量提升。",
    "low_swim_efficiency": "当前速度与划水效率之间的平衡不足，可能存在能量消耗偏高问题。",
}

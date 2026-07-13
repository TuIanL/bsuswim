"""证据模板降级文案（按 code）。

当 YAML 未提供 ``evidence_template``，或渲染后为空时，引擎回退到本表，保证
每条诊断都有可读证据，不抛异常。
"""

FALLBACKS: dict[str, str] = {
    "low_body_position": "身体与水平面夹角偏大，提示身体位置偏低。",
    "hip_drop": "髋部低于参考水平线，提示髋位下沉。",
    "body_position_improves_with_speed": "高速阶段身体角度较低速阶段改善。",
    "forearm_press_down": "入水后前臂下压，前伸支撑不足。",
    "insufficient_front_reach": "有效前伸距离不足。",
    "insufficient_high_elbow_catch": "抱水阶段肘关节角度偏大，高肘支撑不足。",
    "insufficient_catch_area": "抓水面积评分偏低。",
    "low_propulsive_efficiency": "单次划幅偏低，上肢推进效率不足。",
    "excessive_knee_flexion": "打腿阶段膝关节角度偏小，屈曲较大。",
    "unstable_kick_rhythm": "打腿间隔变异较大，节奏不稳定。",
    "stroke_rate_compensation": "速度提升主要依靠划频增加。",
    "low_swim_efficiency": "SWOLF 偏高或技术效率评分偏低。",
}

import json

from app.schemas.report_interpretation import PROMPT_POLICY_VERSION, InterpretationInput, InterpretationOutput


SYSTEM_POLICY = f"""你是游泳运动学报告的辅助解释器。策略版本：{PROMPT_POLICY_VERSION}。
只能使用输入 facts、knowledge 与 evidence manifest。不得重算或修改指标，不得把 unavailable 当作 0。
不得生成综合技术评分、运动员等级、伤病判断、能力缺陷或确定性因果结论。
review_required 只能写成需要结合原视频和教练观察复核的现象。
每个技术含义块必须引用 fact_refs；视觉观察可引用 evidence_refs，但不可替代 fact_refs；训练建议必须使用条件式语气并引用 knowledge_refs。
引用指标时可做常规显示精度舍入，confidence 可换算为百分比，但必须对应当前 fact_ref。
除上述等价显示外，不得添加输入事实或知识中不存在的数字、周期、次数或阈值。
输出前逐块检查：text 中每个阿拉伯数字对应的 metric/frame/retest fact_id 必须出现在同一块的 fact_refs。
不得只引用 finding 或 evidence 来代替数值所属的 metric fact；无法提供对应 fact_ref 时，省略该数字。
只返回符合给定 JSON Schema 的对象，不要 Markdown，不要额外字段。"""


def build_provider_payload(interpretation_input: InterpretationInput) -> tuple[str, str, dict]:
    user_payload = json.dumps(
        interpretation_input.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return SYSTEM_POLICY, user_payload, InterpretationOutput.model_json_schema()

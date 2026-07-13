"""结构化条件评估器（仅支持 ``all`` / ``any`` + ``metric`` / ``manual_tag`` 子句）。

设计约束（Change #5）：**不支持任何字符串表达式**（如 ``"swolf > 90 or efficiency_score < 60"``），
避免解析/安全坑。规则 condition 与 severity 分支都用同一种结构化条件表达。

条件节点（递归）：
    {"all": [clause, ...]}          # 全部满足
    {"any": [clause, ...]}          # 任一满足
    {"metric": "body_angle_deg", "op": ">=", "value": 12}   # 指标比较
    {"manual_tag": "前臂下压"}        # 手动标签命中

两套语义：
- ``evaluate_trigger``：用于规则是否触发。缺失指标 → 视为“条件不满足”（False），不报错。
- ``evaluate_severity_branch``：用于 severity 分级。缺失指标的子句被**跳过**（记入 warnings），
  不使整条分支失败（满足 R012 在 efficiency_score 缺失时仍能用 swolf_value 判级）。
"""

from typing import Any

from app.services.diagnostics.models import DiagnosticMetricsContext

_OPS: dict[str, object] = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _metric_present(context: DiagnosticMetricsContext, key: str) -> bool:
    return key in context.metrics and context.metrics[key] is not None


def _eval_metric_clause(clause: dict, context: DiagnosticMetricsContext) -> bool:
    key = clause["metric"]
    op = clause["op"]
    target = clause["value"]
    if key not in context.metrics or context.metrics[key] is None:
        return False
    actual = context.metrics[key]
    if not _is_number(actual) or not _is_number(target):
        return False
    fn = _OPS.get(op)
    if fn is None:
        return False
    try:
        return bool(fn(actual, target))
    except TypeError:
        return False


def _eval_manual_tag_clause(clause: dict, context: DiagnosticMetricsContext) -> bool:
    tag = clause["manual_tag"]
    return tag in context.manual_tags


def _eval_clause(clause: dict, context: DiagnosticMetricsContext) -> bool:
    if "all" in clause:
        return all(_eval_clause(c, context) for c in clause["all"])
    if "any" in clause:
        return any(_eval_clause(c, context) for c in clause["any"])
    if "metric" in clause:
        return _eval_metric_clause(clause, context)
    if "manual_tag" in clause:
        return _eval_manual_tag_clause(clause, context)
    return False


def evaluate_trigger(condition: dict, context: DiagnosticMetricsContext) -> bool:
    """规则是否触发。缺失指标 → 条件不满足（False）。"""
    if not condition:
        return False
    return _eval_clause(condition, context)


def _eval_severity_clause(clause: dict, context: DiagnosticMetricsContext, warnings: list[str]) -> bool:
    """severity 子句评估；缺失指标返回 (False, 且记 warning)，但由上层决定是否忽略。"""
    if "metric" in clause:
        key = clause["metric"]
        if not _metric_present(context, key):
            warnings.append(f"missing_metric_for_severity:{key}")
            return False
        return _eval_metric_clause(clause, context)
    if "manual_tag" in clause:
        return _eval_manual_tag_clause(clause, context)
    if "all" in clause:
        return all(_eval_severity_clause(c, context, warnings) for c in clause["all"])
    if "any" in clause:
        return any(_eval_severity_clause(c, context, warnings) for c in clause["any"])
    return False


def evaluate_severity_branch(condition: dict, context: DiagnosticMetricsContext) -> tuple[bool, list[str]]:
    """severity 分支评估。

    - ``all``：所有子句必须 present 且匹配（任一缺失 → 该分支不满足，warning 记录）
    - ``any``：任一 present 且匹配即满足（缺失子句被忽略，仅记 warning）

    返回 (matched, warnings)。
    """
    warnings: list[str] = []
    if not condition:
        return False, warnings
    if "all" in condition:
        # all 要求全部 present 且匹配
        for c in condition["all"]:
            if not _eval_severity_clause(c, context, warnings):
                return False, warnings
        return True, warnings
    if "any" in condition:
        for c in condition["any"]:
            if _eval_severity_clause(c, context, warnings):
                return True, warnings
        return False, warnings
    # 单子句
    return _eval_severity_clause(condition, context, warnings), warnings

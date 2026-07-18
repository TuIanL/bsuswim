"""规则注册表：加载 / 校验 YAML 规则文件。

每条规则用结构化 condition 表达触发与 severity，并带 ``status``（active/dormant）
与 ``required_metrics``。注册表只负责读取与轻量校验，不实现评估逻辑。

Change 5 扩展：支持 ``output_kind`` 声明（``diagnostic`` / ``review_finding``）。
review_finding 规则集需声明 ``attention_level`` 与 ``evidence_frame_strategy``
（resolver 枚举），且文件 checksum 计入规则版本元数据。
"""

import hashlib
from pathlib import Path
from typing import Any

import yaml

from app.services.diagnostics.models import DiagnosticMetricsContext

DEFAULT_RULES_DIR = Path(__file__).parent / "rules"

SUPPORTED_OUTPUT_KINDS = {"diagnostic", "review_finding"}
RESOLVER_NAMES = {
    "body_axis_max_deviation",
    "hip_high_low",
    "elbow_min_max_triggering_side",
    "elbow_asymmetry_bounds",
    "knee_minimum_triggering_side",
    "ankle_peak_trough",
    "head_spike_first_n",
    "head_trunk_sync_max",
}


class RuleRegistry:
    """加载指定 rule_set 的 YAML 规则。"""

    def __init__(self, rules_dir: Path | None = None):
        self.rules_dir = rules_dir or DEFAULT_RULES_DIR
        self._cache: dict[str, dict] = {}

    def _path(self, rule_set: str) -> Path:
        return self.rules_dir / f"{rule_set}.yaml"

    def load(self, rule_set: str = "side_freestyle_v1") -> dict[str, Any]:
        """加载规则集，返回 {meta, rules, groups}。"""
        if rule_set in self._cache:
            return self._cache[rule_set]

        path = self._path(rule_set)
        if not path.exists():
            raise FileNotFoundError(f"规则集不存在: {path}")

        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        if not isinstance(data, dict) or "rules" not in data:
            raise ValueError(f"规则文件格式错误（缺少 rules）: {path}")

        meta = {
            "rule_set": rule_set,
            "schema_version": data.get("schema_version", "swim-diagnostics-rules.v1"),
            "stroke": data.get("stroke", "freestyle"),
            "camera_view": data.get("camera_view", "side"),
            "output_kind": data.get("output_kind", "diagnostic"),
            "threshold_basis": data.get("threshold_basis"),
            "rule_file_hash": _file_sha256(path),
        }
        rules = data.get("rules", []) or []
        groups = data.get("diagnostic_groups", []) or []

        self._validate(rules, meta["output_kind"])

        parsed = {"meta": meta, "rules": rules, "groups": groups}
        self._cache[rule_set] = parsed
        return parsed

    def rule_version(self, rule_set: str) -> str:
        """用于 diagnostics_meta.rule_version 的稳定标识（文件 schema_version）。"""
        return self.load(rule_set)["meta"]["schema_version"]

    @staticmethod
    def _validate(rules: list[dict], output_kind: str = "diagnostic") -> None:
        if output_kind not in SUPPORTED_OUTPUT_KINDS:
            raise ValueError(f"不支持的 output_kind: {output_kind}")
        for rule in rules:
            if "id" not in rule or "code" not in rule:
                raise ValueError(f"规则缺少 id/code: {rule}")
            if "condition" not in rule:
                raise ValueError(f"规则 {rule['id']} 缺少 condition")
            if output_kind == "diagnostic":
                if "severity" not in rule:
                    raise ValueError(f"规则 {rule['id']} 缺少 severity")
            elif output_kind == "review_finding":
                if "attention_level" not in rule:
                    raise ValueError(f"review 规则 {rule['id']} 缺少 attention_level")
                ef = rule.get("evidence_frame_strategy")
                if not isinstance(ef, dict) or "resolver" not in ef:
                    raise ValueError(f"review 规则 {rule['id']} 的 evidence_frame_strategy 必须声明 resolver")
                if ef.get("resolver") not in RESOLVER_NAMES:
                    raise ValueError(f"review 规则 {rule['id']} 的 resolver 未知: {ef.get('resolver')}")
                # evidence_metric_keys 校验
                if not rule.get("evidence_metric_keys"):
                    raise ValueError(f"review 规则 {rule['id']} 缺少 evidence_metric_keys")
                if not rule.get("limitations"):
                    raise ValueError(f"review 规则 {rule['id']} 缺少 limitations")
                if not rule.get("review_question"):
                    raise ValueError(f"review 规则 {rule['id']} 缺少 review_question")


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

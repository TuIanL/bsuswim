import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings
from app.schemas.report_interpretation import (
    InterpretationOutput,
    ProviderRequest,
    ProviderResponse,
)


@dataclass
class ProviderError(Exception):
    code: str
    message: str
    retryable: bool = False
    retry_count: int = 0

    def __str__(self) -> str:
        return self.message


class InterpretationProvider(Protocol):
    def generate(self, request: ProviderRequest) -> ProviderResponse: ...


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        key = self.settings.ai_interpretation_api_key
        if key is None or not key.get_secret_value():
            raise ProviderError("provider_not_configured", "AI provider 凭据未配置", False)
        url = self.settings.ai_interpretation_base_url.rstrip("/") + "/chat/completions"
        provider_name = self.settings.ai_interpretation_provider
        is_deepseek = provider_name == "deepseek"
        is_json_object_provider = provider_name in ("deepseek", "qwen")
        user_content: dict = {"report_input": request.input.model_dump(mode="json")}
        if is_json_object_provider:
            user_content["required_output_json_schema"] = request.output_schema
        message_content: str | list[dict] = json.dumps(user_content, ensure_ascii=False)
        if request.visual_mode:
            if not self.settings.ai_interpretation_visual_configured:
                raise ProviderError("provider_visual_capability_missing", "当前模型未配置图片输入与结构化输出能力", False)
            parts: list[dict] = [{"type": "text", "text": message_content}]
            for evidence_id, data_url in request.evidence_images.items():
                parts.append({"type": "text", "text": f"证据图 ID：{evidence_id}"})
                parts.append({"type": "image_url", "image_url": {"url": data_url}})
            message_content = parts
        payload = {
            "model": self.settings.ai_interpretation_model,
            "temperature": self.settings.ai_interpretation_temperature,
            "messages": [
                {"role": "system", "content": request.policy},
                {"role": "user", "content": message_content},
            ],
            "response_format": {"type": "json_object"}
            if is_json_object_provider
            else {
                "type": "json_schema",
                "json_schema": {
                    "name": "swim_report_interpretation",
                    "strict": True,
                    "schema": request.output_schema,
                },
            },
        }
        if self.settings.ai_interpretation_max_output_tokens is not None:
            payload["max_tokens"] = self.settings.ai_interpretation_max_output_tokens
        if is_deepseek:
            payload["thinking"] = {
                "type": "enabled"
                if self.settings.ai_interpretation_thinking_enabled
                else "disabled"
            }
        last_error: ProviderError | None = None
        for attempt in range(self.settings.ai_interpretation_max_retries + 1):
            try:
                response = httpx.post(
                    url,
                    headers={"Authorization": f"Bearer {key.get_secret_value()}"},
                    json=payload,
                    timeout=self.settings.ai_interpretation_timeout_seconds,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise ProviderError("provider_unavailable", f"provider HTTP {response.status_code}", True)
                if response.status_code >= 400:
                    raise ProviderError("provider_rejected", f"provider HTTP {response.status_code}", False)
                data = response.json()
                choice = data["choices"][0]
                if choice.get("finish_reason") == "length":
                    raise ProviderError(
                        "provider_output_truncated",
                        "AI provider 输出达到服务端长度限制，请稍后重试或收紧提示词",
                        False,
                    )
                content = choice["message"]["content"]
                if not isinstance(content, (str, dict)) or not content:
                    raise ProviderError(
                        "provider_empty_response", "AI provider 返回空内容", True
                    )
                output = json.loads(content) if isinstance(content, str) else content
                usage = dict(data.get("usage") or {})
                usage["retry_count"] = attempt
                return ProviderResponse(
                    output=output,
                    usage=usage,
                    provider_request_id=response.headers.get("x-request-id") or data.get("id"),
                )
            except ProviderError as exc:
                last_error = exc
                exc.retry_count = attempt
                if not exc.retryable or attempt >= self.settings.ai_interpretation_max_retries:
                    raise
            except httpx.TimeoutException as exc:
                last_error = ProviderError(
                    "provider_timeout", "AI provider 调用超时", True, retry_count=attempt
                )
                if attempt >= self.settings.ai_interpretation_max_retries:
                    raise last_error from exc
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ProviderError("provider_invalid_response", "AI provider 返回格式无效", False) from exc
        raise last_error or ProviderError("provider_unknown", "AI provider 调用失败", False)


class FakeProvider:
    def __init__(self, mode: str = "valid"):
        self.mode = mode
        self.calls = 0

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        if self.mode == "timeout":
            raise ProviderError("provider_timeout", "fake timeout", True)
        if self.mode == "rate_limit":
            raise ProviderError("provider_unavailable", "fake rate limit", True)
        if self.mode == "invalid_json":
            return ProviderResponse(output={"not": "valid"})

        facts = request.input.facts
        if not facts:
            raise ProviderError("no_interpretable_facts", "报告没有可解释事实", False)
        primary = next((f for f in facts if f.kind in ("finding", "metric")), facts[0])
        module_facts: dict[str, str] = {}
        for fact in facts:
            if fact.module_key in ("body_posture_head_trunk", "upper_limb", "lower_limb"):
                module_facts.setdefault(fact.module_key, fact.fact_id)
        knowledge = request.input.knowledge
        suggestion = []
        if knowledge:
            suggestion = [{
                "title": knowledge[0].title,
                "text": f"可尝试在教练观察下进行{knowledge[0].title}相关练习，并结合原视频确认变化。",
                "fact_refs": [primary.fact_id],
                "knowledge_refs": [knowledge[0].knowledge_id],
                "applicability": "仅在当前数据质量允许并经教练确认后采用。",
                "cautions": knowledge[0].contraindications[:2],
            }]
        output = {
            "schema_version": "swim-report-interpretation.v1",
            "plain_language_summary": {
                "text": f"本次报告的重点是“{primary.label}”，需要结合原视频和教练观察复核。",
                "fact_refs": [primary.fact_id],
                "knowledge_refs": [],
            },
            "module_explanations": [
                {
                    "module_key": module,
                    "text": "该模块存在可供复核的客观测量，建议关注变化趋势而非单次定性。",
                    "fact_refs": [fact_id],
                    "knowledge_refs": [],
                }
                for module, fact_id in sorted(module_facts.items())
            ],
            "priority_focus": [{
                "text": f"优先复核{primary.label}及其对应视频证据。",
                "fact_refs": [primary.fact_id],
                "knowledge_refs": [],
            }],
            "training_suggestions": suggestion,
            "retest_targets": [],
            "limitations": ["AI 解读不替代教练判断。"],
        }
        if self.mode == "extra_field":
            output["overall_score"] = 92
        if self.mode == "assertive":
            output["plain_language_summary"]["text"] = "这证明运动员核心能力不足。"
        return ProviderResponse(output=output, usage={"input_tokens": 1, "output_tokens": 1})


def build_provider(settings: Settings) -> InterpretationProvider:
    if settings.ai_interpretation_provider == "fake":
        return FakeProvider()
    if settings.ai_interpretation_provider in ("deepseek", "qwen", "openai_compatible"):
        return OpenAICompatibleProvider(settings)
    raise ProviderError("unsupported_provider", "不支持的 AI provider", False)

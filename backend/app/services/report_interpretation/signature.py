import hashlib

from app.core.config import Settings
from app.schemas.report_interpretation import (
    INTERPRETATION_OUTPUT_SCHEMA,
    PROMPT_POLICY_VERSION,
    InterpretationInput,
)
from .projector import input_hash, stable_json


def generation_signature(
    interpretation_input: InterpretationInput,
    settings: Settings,
    knowledge_base_version: str,
) -> tuple[str, str]:
    current_input_hash = input_hash(interpretation_input)
    payload = {
        "base_report_generation_signature": interpretation_input.base_report_generation_signature,
        "input_hash": current_input_hash,
        "provider": settings.ai_interpretation_provider,
        "model": settings.ai_interpretation_model,
        "parameters": {
            "temperature": settings.ai_interpretation_temperature,
            "max_output_tokens": settings.ai_interpretation_max_output_tokens,
            "thinking_enabled": settings.ai_interpretation_thinking_enabled,
            "visual_enabled": settings.ai_interpretation_visual_enabled,
            "model_supports_vision": settings.ai_interpretation_model_supports_vision,
            "model_supports_structured_output": settings.ai_interpretation_model_supports_structured_output,
            "max_evidence_images": settings.ai_interpretation_max_evidence_images,
            "max_curve_points": settings.ai_interpretation_max_curve_points,
        },
        "prompt_version": PROMPT_POLICY_VERSION,
        "output_schema_version": INTERPRETATION_OUTPUT_SCHEMA,
        "knowledge_base_version": knowledge_base_version,
        "knowledge_ids": [f"{item.knowledge_id}@{item.version}" for item in interpretation_input.knowledge],
    }
    digest = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
    return digest, current_input_hash

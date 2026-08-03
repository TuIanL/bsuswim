"""一次性的真实 qwen 解读冒烟测试（不写入 DB，不调度后台任务）。

用法：从 backend/ 目录运行，加载 backend/.env 的真实 provider 配置。
仅覆盖 ai_interpretation_max_input_chars（backend/.env 仍是旧的 24000，
而真实报告投影后 30810 字符会超出）。其余配置全部来自 .env。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models import ReportMetadata
from app.schemas.report_interpretation import InterpretationOutput, ProviderRequest
from app.services.report_interpretation.evidence import build_evidence_bundle
from app.services.report_interpretation.knowledge import KnowledgeRegistry
from app.services.report_interpretation.prompt import SYSTEM_POLICY
from app.services.report_interpretation.projector import project_report
from app.services.report_interpretation.provider import build_provider
from app.services.report_interpretation.service import _fit_evidence_to_input_budget, _serialized_input
from app.services.report_interpretation.validator import complete_numeric_fact_refs, parse_output, validate_output


def main() -> None:
    settings = Settings(
        _env_file=".env",
        ai_interpretation_max_input_chars=40000,
    )
    report_id = int(os.environ.get("REPORT_ID", "276"))
    db = SessionLocal()
    try:
        report = db.get(ReportMetadata, report_id)
        if report is None:
            print(f"报告 {report_id} 不存在")
            return
        report_data = report.report_data
    finally:
        db.close()

    registry = KnowledgeRegistry()
    projected = project_report(report_data)
    projected.knowledge = registry.retrieve(
        projected, limit=settings.ai_interpretation_max_knowledge_items
    )
    bundle = build_evidence_bundle(report_data, projected, settings)
    projected.evidence = bundle.items
    projected.evidence_exclusions = bundle.exclusions
    _fit_evidence_to_input_budget(projected, settings.ai_interpretation_max_input_chars)
    serialized = _serialized_input(projected)
    print(f"[报告 {report_id}] facts={len(projected.facts)} knowledge={len(projected.knowledge)} "
          f"chars={len(serialized)} exclusions={len(projected.evidence_exclusions)}")
    print(f"[px 归一化] norm facts: "
          f"{[f.source_key for f in projected.facts if f.derived_from]}")
    print(f"[知识检索] top: {[k.knowledge_id for k in projected.knowledge]}")
    visual_mode = bool(
        settings.ai_interpretation_visual_configured and bundle.image_data_urls
    )
    print(f"[模式] {'visual' if visual_mode else 'text'} "
          f"(视觉图片 {len(bundle.image_data_urls)} 张, provider={settings.ai_interpretation_provider}, "
          f"model={settings.ai_interpretation_model})")

    provider = build_provider(settings)
    request = ProviderRequest(
        policy=SYSTEM_POLICY,
        input=projected,
        output_schema=InterpretationOutput.model_json_schema(),
        evidence_images=bundle.image_data_urls if visual_mode else {},
        visual_mode=visual_mode,
    )
    print("[调用 provider] ...")
    response = provider.generate(request)
    print(f"[provider 返回] finish ok, usage={response.usage}")

    output = parse_output(response.output)
    # 与真实 execute_interpretation 一致：先保守补全引用，再校验。
    completed = complete_numeric_fact_refs(output, projected)
    try:
        result = validate_output(output, projected)
        print(f"[校验] valid={result['valid']} 补全引用={completed} structure_signals={result['structure_signals']}")
    except Exception as exc:
        print(f"[校验] 失败: {exc}")
        print("[校验] 已完成引用补全:", completed)
    print(f"[输出 schema] {output.schema_version}")
    print()
    print("=" * 70)
    print("总体总结：", output.plain_language_summary.text)
    print("=" * 70)
    for item in output.module_explanations:
        print(f"\n【模块 {item.module_key}】")
        print(item.text)
        print(f"  fact_refs={item.fact_refs} knowledge_refs={item.knowledge_refs}")
    print("\n【优先关注】")
    for item in output.priority_focus:
        print(" -", item.text)
    print("\n【训练建议】")
    for item in output.training_suggestions:
        print(f" - {item.title}")
        print(f"   {item.text}")
        print(f"   [适用条件] {item.applicability}")
        if item.cautions:
            print(f"   [注意] {item.cautions}")
    print("\n【复测目标】", [r.metric_key for r in output.retest_targets])
    print("【限制】", output.limitations)
    print("\n[参考知识卡]", [(k.knowledge_id, k.title) for k in projected.knowledge])
    print("[trace] knowledge_ids =", [f"{k.knowledge_id}@{k.version}" for k in projected.knowledge])


if __name__ == "__main__":
    main()

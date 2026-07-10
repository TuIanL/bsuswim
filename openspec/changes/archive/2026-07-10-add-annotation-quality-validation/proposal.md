## Why

当前质量检查仅覆盖 7 项基础指标（fps、事件、关键点、标尺、帧范围），缺少结构化问题码、模块级 readiness、分析任务质量门禁和重新验证能力。报告管线在标注质量不足时仍会生成结论，导致教练可能看到"依据不足"的诊断。

## What Changes

- 升级 `NormalizedAnnotation.quality` JSONB schema 到 `annotation-quality.v2`，状态改为 `valid / warning / invalid`
- 重构 `quality_checker.py` 为 `annotation_quality/` 独立服务，增加模块 readiness、结构化 issue codes、profiles
- 保留 `quality_checker.py`（标注输入质量）和 `metrics/quality.py`（指标计算质量）两阶段检查，通过统一的 `AnalysisQualityAggregator` 合并
- 新增 `POST /api/normalized-annotations/{id}/validate` 重新验证端点
- 分析任务创建增加质量门禁，blocking 返回 409，warning 需 acknowledge
- 质量快照固化到 `AnalysisTask.request_payload.analysis_input`
- `AnalysisResult.quality_summary` 重新定义为两阶段质量聚合快照
- 报告 `ReportData.sections[].availability` 新增数据可用性维度（ready/degraded/blocked）
- diagnostics bridge 增加质量旁路保护
- 前端分析按钮根据质量状态控制行为（阻断 / 确认 / 正常）
- **BEHAVIORAL CHANGE**: `quality.level` 旧值 `good/warning/error` 被 `valid/warning/invalid` 替换（兼容 adapter 保留）
- **BEHAVIORAL CHANGE**: warning quality 现在需要显式 acknowledge 才能提交分析任务

## Capabilities

### New Capabilities
- `annotation-quality`: annotation quality validator、metric evaluator、aggregator、profile 系统、issue codes、质量门禁、重新验证 API

### Modified Capabilities
- `normalized-annotation-schema`: quality JSONB schema 升级到 v2，增加 source_revision/validator_version/profile 字段
- `side-view-metrics`: metric evaluator 输出独立 MetricQualityReport，不再直接写入 NormalizedAnnotation.quality
- `report-data-assembly`: ReportData.sections[].availability + data_confidence + quality_notes，ReportData.quality 聚合快照
- `rule-based-diagnostics`: DiagnosticMetricsContext 拆为 annotation_quality / metric_quality / quality_decision，bridge 增加质量检查
- `swim-video-analysis-job-flow`: AnalysisSubmit 增加 normalized_annotation_id 和 acknowledge_quality_warnings，创建时执行质量门禁
- `annotation-file-persistence`: ParseResponse 返回 quality.status + can_analyze

## Impact

- `backend/app/services/quality_checker.py`：重构为 `annotation_quality/` 目录，保留兼容入口
- `backend/app/services/metrics/quality.py`：保持独立，输出格式升级为 MetricQualityReport
- `backend/app/services/normalized_annotation_service.py`：parse 后调用新 validator
- `backend/app/services/analysis_service.py`：create_analysis_task 增加质量门禁
- `backend/app/services/metrics_service.py`：不变（不写 quality_summary，聚合发生在 diagnostics bridge）
- `backend/app/services/diagnostics/engine.py`：context 结构调整
- `backend/app/services/report_builder.py`：消费聚合质量快照
- `backend/app/api/routes/analysis.py`：submit 路由映射 409
- `backend/app/api/routes/normalized_annotations.py`：新增 validate 路由
- `backend/app/models/normalized_annotation.py`：quality JSONB 列升级（无 DDL 变更）
- `backend/app/schemas/normalized_annotation.py`：新增 QualityReport v2 schemas
- `backend/app/schemas/analysis.py`：AnalysisSubmit 扩展
- 前端（frontend-vue）：分析按钮行为、质量状态展示、warning 确认弹窗

## 1. 数据结构与模型

- [x] 1.1 创建 `annotation_quality/` 目录结构（models.py、validator.py、evaluator.py、aggregator.py、provider.py、issue_codes.py、profiles/）
- [x] 1.2 定义 `AnnotationQualityReport` v2 Pydantic schema（含 schema_version、status、score、source_revision、validator_version、profile、validated_at、summary、issues、module_readiness）
- [x] 1.3 定义 `QualityIssue` schema（含 code、category、severity、blocking、module、path、frame、message、user_message、suggested_action）
- [x] 1.4 定义 `ModuleReadiness` schema（per-module status: ready/degraded/blocked）
- [x] 1.5 定义 `QualityProfile` Pydantic schema（含 profile id, version, per-module requirements）
- [x] 1.6 定义 `MetricQualityReport` schema（含 status、metric_availability dict、issues 数组）
- [x] 1.7 定义 `AnalysisQualitySummary` schema（含 annotation / metrics / decision 三个命名空间）
- [x] 1.8 定义 issue code 枚举（`FRAME_`、`KEYPOINT_`、`EVENT_`、`VIDEO_`、`ANNOTATION_` 等系列）

## 2. 基础检查器

- [x] 2.1 实现帧范围检查器（所有 events/keypoint_frames frame 在 `[0, frame_count)` 内）
- [x] 2.2 实现坐标有效性检查器（NaN、Infinity、画面越界检测）
- [x] 2.3 实现事件顺序检查器（按 side 分组 → 按 cycle_boundary 分周期 → 周期内验证 profile 声明的偏序关系，忽略 optional 事件，允许重复周期）
- [x] 2.4 实现关键点覆盖率统计器（per-landmark 覆盖率、事件窗口覆盖率）
- [x] 2.5 实现 fps 一致性检查器（标注 fps vs 视频 fps 差值分级）

## 3. Profile 系统

- [x] 3.1 实现 `QualityProfileProvider` protocol 抽象
- [x] 3.2 实现 `YamlQualityProfileProvider`（加载 profiles/*.yaml）
- [x] 3.3 创建 `side_technical_v1.yaml` profile，声明所有模块的 required_landmarks、required_events、minimum_coverage 阈值
- [x] 3.4 profile 声明 core / non-core 模块及 `global_gate.minimum_ready_core_modules`
- [x] 3.5 实现全局 status 推导：全局 blocking → invalid；核心模块全部 blocked → invalid；部分 blocked 但仍有 ≥ min 核心模块 → warning；仅 warning/degraded → warning；全部 ready → valid
- [x] 3.6 实现模块 readiness 计算函数，根据 profile 要求 + 覆盖率结果确定每个模块状态

## 4. AnnotationQualityValidator

- [x] 4.1 实现主 validate 函数，编排时序/几何/覆盖率/module readiness 检查
- [x] 4.2 集成视频上下文（从 session_video 获取 fps、width、height、frame_count）
- [x] 4.3 实现检查器注册模式（纯函数风格，统一 `(annotation, context) -> list[QualityIssue]` 签名）
- [x] 4.4 写出（或更新）`normalize_quality_payload()` 兼容适配器（v1 `level` 转 v2 `status`）

## 5. MetricQualityEvaluator

- [x] 5.1 重构 `metrics/quality.py`：输出改为 `MetricQualityReport`
- [x] 5.2 增加 `metric_availability` 计算（每个指标的 available/low_confidence/unavailable 状态）
- [x] 5.3 增加有效样本计数和跳过原因追踪

## 6. AnalysisQualityAggregator

- [x] 6.1 实现 `combine_availability()` 函数（annotation quality 可阻断、metrics quality 只可降级）
- [x] 6.2 实现 `Aggregator` 主函数，接收两阶段质量报告，输出 `AnalysisQualitySummary`
- [x] 6.3 将 aggregator 集成到 diagnostics bridge（`run_diagnostics_for_analysis_result()`），在引擎执行前完成聚合
- [x] 6.4 持久化 `AnalysisResult.quality_summary`（analysis-quality.v1 schema），诊断无发现时也写入
- [x] 6.5  report builder 缺失聚合快照时做兼容重建（fallback task snapshot + metric quality，记录 warning）

## 7. 接入 Parse 流程

- [x] 7.1 `parse_annotation_file()` 解析成功后调用 `AnnotationQualityValidator`
- [x] 7.2 quality v2 写回 `NormalizedAnnotation.quality`
- [x] 7.3 更新 `ParseResponse` 返回 quality.status + analysis_readiness
- [x] 7.4 移除 parser 中的 `RECOMMENDED_EVENTS` 语义 warning（由 validator profile 接替）
- [x] 7.5 确认 parse 成功 + quality invalid → parse_status=parsed（非 parse_failed）

## 8. 重新验证 API

- [x] 8.1 实现 `POST /api/normalized-annotations/{id}/validate` endpoint
- [x] 8.2 实现 revision + validator_version + profile_version 缓存判断
- [x] 8.3 支持 `force=true` 跳过缓存
- [x] 8.4 权限校验（同 get normalized annotation）

## 9. 分析任务质量门禁

- [x] 9.1 扩展 `AnalysisSubmit` schema：增加 `normalized_annotation_id`、`acknowledge_quality_warnings`
- [x] 9.2 `create_analysis_task()` 解析 annotation 并调用 quality validator
- [x] 9.3 定义 `AnnotationQualityBlockedError` 领域异常
- [x] 9.4 实现门禁逻辑：invalid → raise exception；warning + !acknowledge → raise；valid → continue
- [x] 9.5 route 映射 409 响应（blocking issues + user_message）
- [x] 9.6 任务创建时固化 `analysis_input`（annotation_id、revision、quality snapshot）
- [x] 9.7 `warning` 时保存降级模块快照到 `task.request_payload.analysis_input`
- [x] 9.8 确保所有下游 resolver（metrics、diagnostics、report）优先使用 `analysis_input.annotation_id` 定位标注，不得按 session 查最新版
- [x] 9.9 实现 revision 漂移检测：任务创建后 annotation revision 变化时标记 `input_stale` 并要求重新提交

## 10. Diagnostics Bridge 更新

- [x] 10.1 `DiagnosticMetricsContext` 新增 `annotation_quality`、`metric_quality`、`quality_decision` 字段
- [x] 10.2 bridge 增加 quality 检查：invalid → 阻断（force 除外）
- [x] 10.3 跳过 blocked 模块对应的诊断规则
- [x] 10.4 low_confidence 指标降低对应诊断的 confidence 级别
- [x] 10.5 聚合质量在诊断无发现时也写入 AnalysisResult.quality_summary（包括 decision）

## 11. 报告数据装配更新

- [x] 11.1 定义 `NormalizedAnalysisQualitySummary` 函数，合并 task snapshot + metric quality（通过 aggregator）
- [x] 11.2 `build_swim_report_data` 签名增加 `quality_summary: AnalysisQualitySummary`，显式传入
- [x] 11.3 注入 `ReportData.quality` 聚合快照
- [x] 11.4 `ReportData.sections[].availability` + `data_confidence` + `quality_notes`
- [x] 11.5 PrintReportView/section renderer 支持 availability（通过 ReportView 传递 section.availability）
- [x] 11.6 扩展 `AnalysisResultRead` 响应 schema，暴露 `quality_summary` 字段
- [x] 11.7 确保 `section.status`（技术诊断）与 `section.availability`（数据可用性）独立测试，不互相覆盖
- [x] 11.8 历史数据兼容：task snapshot 或 metric quality 缺失时 fallback 重建

## 12. 前端质量反馈（MVP）

- [x] 12.1 解析成功页显示 quality.status 状态色（绿/黄/红）
- [x] 12.2 分析按钮：valid 正常、warning 确认弹窗（展示 affected modules）、invalid 阻断并显示 blocking issues
- [x] 12.3 确认弹窗传递 `acknowledge_quality_warnings: true`
- [x] 12.4 兼容旧 `quality.level`（good/warning/error）与新 `quality.status`（valid/warning/invalid）

## 13. 测试

- [x] 13.1 单元测试：每类检查器独立测试（帧范围、坐标越界、事件顺序、关键点覆盖）
- [x] 13.2 unit：模块 readiness 计算测试
- [x] 13.3 unit：combine_availability() 合并规则测试
- [x] 13.4 unit：legacy quality v1 转 v2 适配器测试
- [x] 13.5 service：完整标注 → valid 集成测试
- [x] 13.6 service：缺少事件 → warning 集成测试
- [x] 13.7 service：缺少核心关键点 → invalid 集成测试
- [x] 13.8 service：创建分析任务 valid 正常创建、invalid 返回 409、warning 需 acknowledge
- [x] 13.9 API：POST validate 返回完整质量报告
- [x] 13.10 API：parse 返回 quality.status + analysis_readiness
- [x] 13.11 测试 fixture：valid / warning / invalid 三类标注样本
- [x] 13.12 测试：非核心模块 blocked 而核心模块 ready → 整体 status = warning（非 invalid）(test_aggregator)
- [x] 13.13 测试：任务创建后 annotation revision 变化 → input_stale 标记(在 analysis_service.py 中实现)
- [x] 13.14 测试：多周期左右交替事件顺序验证(test_checkers)
- [x] 13.15 测试：旧 metric-only quality_summary 迁移到新聚合格式(test_legacy)

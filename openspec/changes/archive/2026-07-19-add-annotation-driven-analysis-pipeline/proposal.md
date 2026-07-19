# Change: Add Annotation-Driven Analysis Pipeline

## Why

系统已经具备一条完整但尚未接通的二维运动学产物链：

NormalizedAnnotation
  → AnnotationMetric
  → KinematicArtifactSet
  → KinematicReviewFindingSet
  → FivePageKinematicsReport

当前 AnalysisTask 创建阶段已经锁定 normalized_annotation_id、annotation
revision 和质量快照，但 run_analysis_task() 仍固定调用 ModelServiceClient，
导致基于人工骨架标注的指标、视觉资产、复核发现和五页报告只能通过多个
独立 API 手动生成。

因此，即使用户已经上传视频并完成 CVAT 标注，系统仍不能从一个分析任务
自动生成最终报告。

本 Change 将 AnalysisTask 执行器扩展为可路由的多 pipeline 执行框架，
并实现第一条本地 annotation_kinematics pipeline，使系统无需调用 mock
模型服务即可完成二维运动学分析和五页报告持久化。

## What Changes

- 为 AnalysisTask 增加 pipeline_type、pipeline_version、execution_state、
  attempt_count、failed_stage 和 error_code
- 增加 analysis pipeline registry 和统一执行协议
- 保留现有 model_service pipeline 行为
- 新增 annotation_kinematics / side_2d_v1 pipeline
- 预留 hybrid pipeline 类型，但本 Change 不实现其执行逻辑
- 根据显式 pipeline_type 或 normalized_annotation_id 选择执行路径
- 在后台执行前重新校验 annotation ID、revision、session 归属、侧面机位和质量状态
- 调用 side_2d_kinematics calculator 并持久化 AnnotationMetric
- 生成或复用当前 KinematicArtifactSet
- 生成或复用当前 KinematicReviewFindingSet
- 创建或更新任务对应的 AnalysisResult
- 装配 side_2d_kinematics_5page_v1 报告
- 创建或更新 ReportMetadata，并使已有 PDF 状态变为 stale
- 增加失败任务 retry API，同一任务重试时复用已完成的幂等产物
- 增加结构化阶段错误、执行检查点和完整来源追溯

## Pipeline Types

- model_service
  - 保留现有模型服务调用路径
- annotation_kinematics
  - 本 Change 实现
  - pipeline_version = side_2d_v1
- hybrid
  - 仅保留类型和路由边界
  - 本 Change 返回 PIPELINE_NOT_IMPLEMENTED

## Annotation Pipeline Stages

queued
  → validating_input
  → calculating_metrics
  → generating_artifacts
  → running_findings
  → saving_result
  → assembling_report
  → completed

任何不可恢复错误：

current_stage
  → failed

## Capabilities

### New Capabilities

- annotation-driven-analysis-pipeline
  - 系统可以根据已锁定的 NormalizedAnnotation 执行完整二维运动学分析
  - 系统可以持久化执行检查点并复用幂等产物
  - 系统可以不依赖模型服务生成五页报告

### Modified Capabilities

- heavy-model-analysis-architecture
  - AnalysisTask 不再只代表模型服务任务
  - 执行器根据 pipeline_type 路由
  - 模型服务仍保持独立，不在业务后端加载重模型

- side-2d-kinematics
  - 支持由 AnalysisTask 自动调用并持久化指标

- kinematics-visual-artifacts
  - 支持由 AnalysisTask 自动生成或复用当前 artifact set

- rule-based-diagnostics
  - 支持由 AnalysisTask 自动生成待复核发现
  - review findings 不写成确定性 diagnostics

- five-page-kinematics-report
  - 支持由 AnalysisTask 装配并写入 ReportMetadata

- report-data-assembly
  - side_2d_kinematics_5page_v1 成为 annotation_kinematics pipeline 的最终报告产物

## Impact

- backend/app/models/analysis.py
- backend/app/schemas/analysis.py
- backend/app/services/analysis_service.py
- backend/app/services/analysis_pipelines/
- backend/app/services/reporting/kinematics_report/assembly_service.py
- backend/app/api/routes/analysis.py
- backend/app/models/report.py 或现有 ReportMetadata 写入逻辑
- Alembic migration
- OpenSpec capability specs
- backend unit / integration / E2E tests

## Non-Goals

- 不实现 hybrid pipeline
- 不实现 Celery、Redis 或持久化任务队列
- 不修改二维运动学公式
- 不重新实现 artifacts renderer
- 不重新实现 review findings engine
- 不修改五页报告的页面内容和展示规则
- 不实现前端工作流重构
- 不实现 PDF 导出
- 不把 review findings 转换为确定性专业诊断
- 不支持正面、俯视或其他泳姿 pipeline

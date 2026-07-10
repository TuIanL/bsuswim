## Context

当前质量系统有两个独立检查器：

```
quality_checker.py           metrics/quality.py
─────────────────            ─────────────────
7 项结构化检查               9 项指标计算后验证
输出 AnnotationQuality       输出 metrics quality dict
在 parse 时内联执行           在 metrics engine 内执行
写入 NormalizedAnnotation.quality  写入 AnnotationMetric.quality
```

缺少统一的 issue code 体系、模块级 readiness、分析任务门禁、重新验证能力和报告质量说明。分析提交不考虑质量状态，报告在数据不足时仍能生成。

## Goals / Non-Goals

**Goals:**

- 升级 quality JSONB 到 `annotation-quality.v2`，状态使用 `valid / warning / invalid`
- 重构 quality_checker.py 为 annotation_quality/ 服务，支持结构化 issue codes 和模块 readiness
- 保留两阶段检查（annotation + metrics），通过 AnalysisQualityAggregator 合并
- 新增 `POST .../validate` 重新验证端点，使用 `(revision + validator_version + profile_version)` 做轻量缓存
- 分析任务创建增加质量门禁，blocking → 409，warning → acknowledge
- 质量快照固化到 `AnalysisTask.request_payload.analysis_input`
- AnalysisResult.quality_summary 定义为两阶段质量聚合快照
- 报告 sections 增加 availability（ready/degraded/blocked）维度
- diagnostics bridge 增加质量旁路保护
- 前端分析按钮根据状态控制行为

**Non-Goals:**

- SHA256 validation fingerprint（使用 revision 缓存键代替）
- 数据库 profile 和教练自定义 profile
- 完整覆盖率仪表盘和轨迹异常高级检测
- 单独的质量问题数据库表
- 批量重新验证
- 帧跳转前端功能

## 数据时序

质量数据在不同阶段产生，写入不同位置，最终在 diagnostics bridge 聚合。

```
T1  parse
   NormalizedAnnotation.quality = annotation-quality.v2
   (包含 annotation quality status、issues、module_readiness)

T2  submit
   task.request_payload.analysis_input =
     annotation_id + revision + annotation quality snapshot
   ↓
   门禁：invalid → 409，warning → require acknowledge
   门禁后整个链路的输入被锁定到此 annotation_id + revision

T3  calculate metrics
   AnnotationMetric.quality = metric-quality.v1
   (包含 metric_availability、有效样本数、issues)

T4  diagnostics bridge ← 聚合在此发生
   load task snapshot（T2 的 annotation quality snapshot）
   load AnnotationMetric.quality（T3 的 metric quality）
   → AnalysisQualityAggregator.aggregate()
   → 写入 AnalysisResult.quality_summary（analysis-quality.v1）
   → 再执行 diagnostics engine

T5  report
   consume persisted AnalysisResult.quality_summary
   → ReportData.quality
   → section.availability + data_confidence + quality_notes
   → 不重新查询最新标注
```

### 关键约束

```
T2→T4→T5 全链路使用同一 annotation_id + revision
T4 是 AnalysisResult.quality_summary 的唯一写入点
    metrics engine 不写 quality_summary
    report builder 不写 quality_summary
    诊断无发现时也写入（decision：full/degraded/blocked）
T5 不存在 quality_summary 时做兼容重建（fallback，记录 warning）
```

## Decisions

### 1. 复用现有 quality JSONB，不新增 quality_report 列

| 方案 | 结论 |
|------|------|
| 新增 quality_report 列 + 保留现有 quality 列 | 两列数据同步问题，排除 |
| 升级现有 quality 列 schema v2 | 采用 |

历史格式通过兼容适配器读取：

```python
def normalize_quality_payload(raw: dict | None) -> AnnotationQualityReport:
    if raw and raw.get("schema_version") == "annotation-quality.v2":
        return AnnotationQualityReport.model_validate(raw)
    return migrate_legacy_quality_payload(raw or {})
```

不新增 `quality_status` / `quality_score` 等冗余标量列。

### 2. 保留两阶段检查器，通过聚合层合并

```
AnnotationQualityValidator    MetricQualityEvaluator
(标注输入质量)                 (指标计算质量)
       │                              │
       └──────────┬───────────────────┘
                  ▼
     AnalysisQualityAggregator
                  ▼
     AnalysisResult.quality_summary
```

不选择（a）统一取代两者，因为两阶段回答不同问题且发生在不同时间点。

### 3. Profile provider 接口现在做

```python
class QualityProfileProvider(Protocol):
    def get(self, profile_id: str) -> QualityProfile: ...
```

第一版使用 YAML 实现，目录与 diagnostics 保持一致：

```
backend/app/services/annotation_quality/profiles/side_technical_v1.yaml
```

数据库实现推迟。

### 4. 质量门禁以 service 层为权威位置

```
route: 解析 HTTP → 映射异常
service: 质量检查 + 抛出 AnnotationQualityBlockedError
```

```python
class AnnotationQualityBlockedError(Exception):
    def __init__(self, quality: AnnotationQualityReport):
        self.quality = quality
```

warning 需调用方显式传递 `acknowledge_quality_warnings: true`，避免仅靠前端弹窗决定。

### 5. 质量快照固化到 task.request_payload

```json
{
  "analysis_input": {
    "type": "normalized_annotation",
    "annotation_id": 401,
    "annotation_revision": 4,
    "annotation_quality_snapshot": {...}
  }
}
```

所有后续下游（metrics resolver、diagnostics bridge、report builder）SHALL 优先使用 `analysis_input.annotation_id` 定位标注，不得按 session 查最新版。任务创建后若 annotation revision 变化，系统 SHALL 标记 `input_stale` 并要求重新提交。

### 6. Aggregator 在 diagnostics bridge 内运行

Aggregator 的位置不是 metrics service（`metrics_service.py: 不变`），也不是 report builder。

```text
run_diagnostics_for_analysis_result()
  │
  ├─ load task.request_payload.analysis_input
  ├─ get AnnotationMetric.quality (latest by calculator_version)
  ├─ AnalysisQualityAggregator.aggregate()
  ├─ persist → AnalysisResult.quality_summary
  └─ RuleBasedDiagnosticsEngine.run()  ← 聚合完成后才执行
```

Report builder 只消费、不生产 quality_summary。缺失时通过兼容路径重建并记录 warning。

### 7. AnalysisTask 仍为 model-task 记录，annotation_id 是输入引用

本 Change 不重构 task executor。`analysis_input.type = normalized_annotation` 对 ModelServiceClient 暂无执行分支影响；其约束在 T4（diagnostics bridge）和 T5（report）体现。后续可单独做 task executor 类型的拆分。

### 8. AnalysisResult.quality_summary 定义为聚合快照

```json
{
  "schema_version": "analysis-quality.v1",
  "annotation": { "...annotation quality..." },
  "metrics": { "...metric quality..." },
  "decision": { "analysis_allowed": true, "module_availability": {...} }
}
```

### 9. 整体 invalid 与单模块 blocked 的推导规则

profile 声明哪些是 core modules：

```yaml
profile:
  id: side_technical_v1
  global_gate:
    minimum_ready_core_modules: 2
  modules:
    body_position:  { core: true }
    arm_entry:      { core: true }
    catch_pull:     { core: true }
    leg_kick:       { core: false }
    efficiency:     { core: false }
```

annotation status 推导规则：

```
存在全局 blocking issue（如视频上下文不存在）→ status = invalid
核心模块全部 blocked → status = invalid
部分模块 blocked，仍有 ≥ minimum_ready_core_modules 可运行 → status = warning
只有 degraded / warning issue → status = warning
全部 ready 且无 warning → status = valid
```

`blocking` 字段在 issue 级别表示"此问题阻断其所在模块"；模块 availability 为 `blocked` 不代表整体 `invalid`。前端根据整体 status 控制分析按钮。

### 10. 报告 section 增加 availability 维度

```json
{
  "key": "catch_pull",
  "status": "has_issues",
  "availability": "degraded",
  "data_confidence": "low",
  "quality_notes": ["缺少 catch_start，阶段时长未生成"]
}
```

`status` 表示技术诊断严重程度（由 diagnostics 决定）；`availability` 表示数据可用性（由质量决定）。PDF 省略根据 availability 判断。

### 11. 不新增 DB migration

quality JSONB v1 → v2 通过兼容 adapter 处理。现有数据无需迁移。

### 12. diagnostics bridge 增加质量保护

直接调用 diagnostics run API 时也检查 quality：

```python
if quality.status == "invalid" and not force:
    raise AnnotationQualityBlockedError(...)
```

### 13. 事件顺序验证按周期分组

事件顺序检查 SHALL 先按 `side` 分组，再以连续 `hand_entry` 作为周期边界。在单个周期内验证 profile 声明的偏序关系，而非整段视频一条硬链。

```yaml
event_sequences:
  freestyle_arm_cycle:
    partition_by: side
    cycle_boundary: hand_entry
    order:
      - hand_entry
      - catch_start
      - pull_end
      - hand_exit
    optional:
      - recovery_peak
```

MVP 只比较同侧相邻事件，忽略不存在的 optional event，允许重复周期。

### 14. build_swim_report_data 显式接收质量参数

```python
def build_swim_report_data(
    result: AnalysisResult,
    annotation_metric: AnnotationMetric,
    diagnostics: list[dict],
    quality_summary: AnalysisQualitySummary,
) -> dict: ...
```

不要从数据库中猜测。调用方（diagnostics bridge 或 report endpoint）负责传入。

### 15. 前端分层策略

- 必须做：分析按钮行为（阻断/确认/正常）、基础质量状态显示、warning 确认弹窗传递 acknowledge 参数
- 推迟：详细 AnnotationQualityPanel、帧跳转、覆盖率仪表盘

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 旧前端可能把 quality=invalid 误当 parse_failed | API response 同时返回 parse_status + quality.status，前端 explicit 判断 |
| revision 缓存键在 video metadata 变化时失效 | MVP 接受；变化时由调用方 force revalidate |
| AnalysisSubmit 新增 normalized_annotation_id 破坏现有调用方 | 设为 optional，缺失时从 session 推导 |
| diagnostics 与 quality 职责边界模糊 | 文档固定：quality 决定"能不能跑"，diagnostics 决定"有没有技术问题" |

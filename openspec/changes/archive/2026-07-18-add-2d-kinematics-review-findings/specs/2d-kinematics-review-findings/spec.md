## ADDED Requirements

### Requirement: 生成待复核二维运动学发现
系统 SHALL 从 `swim-side-kinematics.v1` 的 `AnnotationMetric` 生成有限、可解释的待复核发现集合，每条发现包含标题、结构化指标证据、证据帧、置信度、数据与方法限制以及教练复核问题。所有发现 `status` SHALL 恒为 `review_required`，不得输出确定性技术诊断。

#### Scenario: 成功生成八类发现中的命中项
- **WHEN** 对合法的 `side_2d_kinematics` AnnotationMetric 调用生成接口且若干规则条件成立
- **THEN** 返回 `status=ready` 的 finding set，其中每条 finding 含 `title`、`evidence_metrics`、`evidence_frames`、`confidence`、`limitations`、`review_question`，且 `status=review_required`

#### Scenario: 无规则命中仍成功
- **WHEN** 指标合法但所有规则条件均不成立
- **THEN** 返回 `status=ready`、`findings=[]`、`finding_count=0`，不属于错误

### Requirement: 证据与置信度不越权推断
系统 SHALL 仅基于二维运动学事实测量表达"疑似"技术模式，不得输出力量不足、推进力不足、能力或效率不足等确定性结论。每条 finding 的 `title` SHALL 以"疑似"或"可能"开头，且 limitations 中 SHALL 至少包含侧面二维投影或未结合动作阶段等限制说明。

#### Scenario: 禁用确定性断言短语
- **WHEN** 任意 review finding 的 `title`、`review_question` 或 `limitations` 文本包含 `力量不足`、`推进力不足`、`核心能力不足` 等断言短语
- **THEN** 内容校验 SHALL 失败（硬校验）

#### Scenario: 低置信指标保留但降级
- **WHEN** 某 required 指标 `availability=low_confidence` 且条件成立
- **THEN** finding 仍生成、`status` 仍为 `review_required`、置信度乘 0.65、并追加"部分证据指标可信度较低"限制

### Requirement: 证据帧定位不重算触发值
`EvidenceResolver` SHALL 优先使用 `AnnotationMetric.metrics.time_series` 定位证据帧；当所需位置序列未持久化时 MAY 从 `NormalizedAnnotation` 重建该序列，但 MUST NOT 重新计算或覆盖用于触发规则的指标值。

#### Scenario: 持久化序列直接定位
- **WHEN** KRF001 需要身体轴角偏离最大的帧
- **THEN** resolver 直接从 `time_series.body_axis_angle_deg` 定位，不回读标注

#### Scenario: 标注回读仅用于找帧
- **WHEN** KRF002 需要髋中点最高/最低帧且髋 y 未持久化
- **THEN** resolver 从 `NormalizedAnnotation` 重建髋中点 y 仅用于选帧，触发值仍来自 metric

### Requirement: 缺失与不可用指标显式跳过
系统 SHALL 将"逻辑键不存在"标记为 `missing_metric:<key>`、"envelope 为 unavailable"标记为 `unavailable_metric:<key>`，二者均进入 `skipped_rules`。`low_confidence` 指标 SHALL 继续评估并降低置信度；`available` 但条件不成立 SHALL 视为正常未命中，不进入 `skipped_rules`。

#### Scenario: 全部规则因数据不足被跳过
- **WHEN** 所有 required 指标均 unavailable
- **THEN** 返回 `status=ready`、`findings=[]`、`skipped_rules` 含 `unavailable_metric:<key>`、`warnings` 含 `no_evaluable_review_rules`

### Requirement: 幂等生成与版本追溯
系统 SHALL 基于 `annotation_metric_id`、`source_annotation_revision`、`source_metric_hash`、`rule_set`、`rule_file_hash`、`engine_version`、`threshold_basis` 计算 `generation_signature`。相同 signature + `force=false` 返回已有记录；相同 signature + `force=true` 原地覆盖；不同 signature 创建新记录供追溯。

#### Scenario: 相同输入幂等返回
- **WHEN** 对相同 metric 与规则以 `force=false` 重复生成
- **THEN** 返回已有 finding set，不新建行

#### Scenario: force 原地覆盖
- **WHEN** 以 `force=true` 对相同 signature 重新生成
- **THEN** 将已有记录重置为 generating 并原地覆盖 findings，不 INSERT 新行

### Requirement: 读取接口按期望签名解析
GET 接口 SHALL 依据当前 metric、当前规则文件、当前 engine version 计算 `expected_generation_signature`，返回与其完全匹配的 finding set；不存在时返回 `404 review_findings_not_generated`。SHALL NOT 盲目返回 `created_at` 最新行。

#### Scenario: 返回当前版本而非历史
- **WHEN** 规则升级后存在旧 signature 的历史记录与当前 signature 的新记录
- **THEN** GET 返回与 expected signature 匹配的新记录，而非旧版本

### Requirement: 独立持久化与 API 边界
系统 SHALL 在 `kinematic_review_finding_sets` 表持久化 finding set，不写入 `annotation_metrics.metrics` 或 `analysis_results.diagnostics`。提供 `POST /annotation-metrics/{id}/review-findings/generate` 与 `GET /annotation-metrics/{id}/review-findings`，并校验 calculator/schema 匹配、ownership 与 source revision 未 stale。

#### Scenario: 拒绝旧 schema 输入
- **WHEN** 对 `swim-side-metrics.v1` 的 AnnotationMetric 调用生成接口
- **THEN** 返回 `422 unsupported_metric_schema`

#### Scenario: 拒绝 stale revision
- **WHEN** metric 的 `source_revision` 与 `NormalizedAnnotation.revision` 不一致
- **THEN** 返回 `409 metric_revision_stale`

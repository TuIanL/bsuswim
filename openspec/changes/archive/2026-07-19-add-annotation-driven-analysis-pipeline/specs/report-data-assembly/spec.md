# Capability: report-data-assembly

## MODIFIED Requirements

### Requirement: side_2d_kinematics_5page_v1 is the annotation pipeline final report

report-data-assembly SHALL 将 side_2d_kinematics_5page_v1 作为
annotation_kinematics pipeline 的最终报告产物。

#### Scenario: Report produced by annotation pipeline

- **WHEN** annotation_kinematics pipeline 完成
- **THEN** 装配产物 SHALL 为五页 swim-report.v1
- **AND** 该产物 SHALL 被写入 ReportMetadata（persistence 由 pipeline 负责）
- **AND** assembly service 本身 SHALL NOT 持久化 ReportMetadata

### Requirement: Review findings resolution is explicit

report-data-assembly SHALL 明确区分“findings 尚未生成”与“findings 规则错误”。

#### Scenario: Findings generated

- **WHEN** 当前 KinematicReviewFindingSet 已存在
- **THEN** 系统 SHALL 解析并以 review_required 形式展示 findings

#### Scenario: Findings not generated

- **WHEN** review findings 尚未生成
- **THEN** 系统 SHALL 允许 partial report（仅跳过 findings 页内容）

#### Scenario: Rule or schema error

- **WHEN** 规则集缺失、版本不匹配或 metric revision 不一致
- **THEN** 系统 SHALL 向上抛出结构化异常
- **AND** MUST NOT 静默降级为无 findings

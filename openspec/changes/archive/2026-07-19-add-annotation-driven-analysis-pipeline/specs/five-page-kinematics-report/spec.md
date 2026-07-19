# Capability: five-page-kinematics-report

## MODIFIED Requirements

### Requirement: Report is assembled and persisted by the analysis pipeline

五页报告 SHALL 可由 annotation_kinematics pipeline 装配并写入 ReportMetadata。

#### Scenario: Annotation pipeline assembles report

- **WHEN** annotation_kinematics task 到达 assembling_report 阶段
- **THEN** 系统 SHALL 调用 assemble_five_page_kinematics_report
- **AND** SHALL 将结果写入当前 session 的 ReportMetadata
- **AND** SHALL 在报告中附加 pipeline_trace

#### Scenario: Current session report follows last-successful-write

- **WHEN** annotation pipeline 成功持久化报告
- **AND** session 已有更早的 ReportMetadata（可能来自其他 pipeline）
- **THEN** 系统 SHALL 整体替换 report_data
- **AND** source SHALL 为 annotation_kinematics
- **AND** 已导出的 PDF SHALL 标记为 stale
- **AND** 失败发生在报告持久化之前时，既有报告 SHALL 保持不变
- **AND** 报告持久化 SHALL 在 session 行锁保护下进行（见 annotation-driven-analysis-pipeline）

#### Scenario: Report content excludes volatile execution trace

- **WHEN** annotation pipeline 写入 report_data
- **THEN** 稳定的来源信息 SHALL 写入 `source_trace`
- **AND** task_id / analysis_result_id / attempt SHALL NOT 出现在 report_data 中
- **AND** 相同 generation_signature 重试 SHALL 产生相同 report_data

### Requirement: Report assembly errors are not swallowed

assembly service SHALL NOT 将规则配置或 staleness 异常静默降级为“无 findings”。

#### Scenario: Non-generatable findings

- **WHEN** review findings 尚未生成（review_findings_not_generated）
- **THEN** 系统 SHALL 允许 partial report

#### Scenario: Structural errors are raised

- **WHEN** 出现 metric_revision_stale / invalid_rule_set / rule_output_kind_mismatch
       或其他系统异常
- **THEN** 系统 SHALL 正常向上抛出
- **AND** MUST NOT 静默降级为无 findings

## ADDED Requirements

### Requirement: Guided workflow provides report entry after completion
引导工作流 SHALL 在 annotation_kinematics 任务完成后提供 HTML 报告与 PDF 操作入口。

#### Scenario: Completed annotation pipeline task
- **WHEN** 最新 annotation_kinematics 任务状态为 completed
- **THEN** 引导工作流 MUST 提供"查看 HTML 报告"入口（复用 `/reports/:sessionId`）
- **AND** MUST 提供导出/下载 PDF 入口（复用现有 PDF API）
- **AND** MUST NOT 在工作流页内复制报告 section renderer 或五页报告结构

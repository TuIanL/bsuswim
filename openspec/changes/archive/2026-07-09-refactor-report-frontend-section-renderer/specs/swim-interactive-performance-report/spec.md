## ADDED Requirements

### Requirement: Frontend renders swim-report.v1 sections

前端报告页 SHALL 支持渲染后端 swim-report.v1 产出的 `sections` 数组，并在缺少 `section.type` 字段时通过 section key 映射进行渲染。

#### Scenario: Sections array is rendered in order
- **WHEN** `report_data.sections` 包含多个 section 对象
- **THEN** 前端 MUST 按数组顺序渲染每个 section，每个 section 使用其对应的 renderer 组件

#### Scenario: Unknown section key does not break page
- **WHEN** section 包含不在渲染映射表中的 key
- **THEN** 前端 MUST 使用 GenericSection 渲染，不引发页面崩溃或白屏

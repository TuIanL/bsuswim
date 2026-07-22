## MODIFIED Requirements

### Requirement: The system assembles a fixed five-page kinematics report

The system SHALL assemble a `swim-report.v1` document using report profile
`side_2d_kinematics_5page_v1`.

The document SHALL contain exactly five sections with `page_number` values
`[1, 2, 3, 4, 5]`.

#### Scenario: Complete current inputs are available

- **GIVEN** a current `AnnotationMetric` with schema `swim-side-kinematics.v1`
- **AND** its current artifact set is available
- **AND** its current review finding set is available
- **WHEN** the report is assembled
- **THEN** the report SHALL contain exactly five sections
- **AND** their `page_number` values SHALL be `[1, 2, 3, 4, 5]`
- **AND** the report `assembly_status` SHALL be `ready`

#### Scenario: Frontend renders five-page report

- **WHEN** 用户访问报告页面
- **AND** 报告数据包含 `page_number`, `page_type`, `module_key` 字段
- **THEN** 前端 SHALL 按 `page_number` 顺序渲染5个页面
- **AND** 每个页面 SHALL 显示对应的 `page_type` 标题
- **AND** 每个页面 SHALL 渲染 `metrics`, `findings`, `assets` 内容
- **AND** 每个页面 SHALL 显示 `quality_notes`（如果有）

## ADDED Requirements

### Requirement: 前端 SHALL 支持5页报告的完整渲染

系统 SHALL 在前端完整渲染5页运动学报告的所有内容，包括指标、发现、可视化资产。

#### Scenario: 报告页面结构渲染

- **WHEN** 报告数据加载完成
- **THEN** 前端 SHALL 渲染5个独立的页面区域
- **AND** 每个页面 SHALL 有明确的分页样式（page-break-after）
- **AND** 每个页面 SHALL 显示页码和页面类型标记

#### Scenario: 报告指标渲染

- **WHEN** 报告章节包含 `metrics` 数据
- **THEN** 前端 SHALL 以表格或卡片形式展示每个指标
- **AND** 每个指标 SHALL 显示名称、数值、单位、状态
- **AND** 不可用的指标 SHALL 显示为"不可用"状态

#### Scenario: 报告发现渲染

- **WHEN** 报告章节包含 `findings` 数据
- **THEN** 前端 SHALL 以列表形式展示每个发现
- **AND** 每个发现 SHALL 显示标题、描述、严重程度
- **AND** 发现 SHALL 按严重程度排序

#### Scenario: 报告资产渲染

- **WHEN** 报告章节包含 `assets` 数据
- **THEN** 前端 SHALL 渲染可视化资产
- **AND** 图片资产 SHALL 以适当尺寸展示
- **AND** 图表资产 SHALL 使用图表库渲染

#### Scenario: 报告打印优化

- **WHEN** 用户触发打印或PDF导出
- **THEN** 前端 SHALL 应用打印样式
- **AND** 每个页面 SHALL 在打印时独立成页
- **AND** 页面内容 SHALL 不溢出打印区域

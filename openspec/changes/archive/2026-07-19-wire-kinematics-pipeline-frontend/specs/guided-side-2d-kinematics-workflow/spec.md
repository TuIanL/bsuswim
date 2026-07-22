## MODIFIED Requirements

### Requirement: Six-step guided side-view 2D kinematics workflow

系统 SHALL 在 `/sessions/:sessionId/upload` 提供可恢复的六步侧面二维运动学 Web 工作流：上传并绑定侧面视频、上传 CVAT Skeleton XML、自动解析并展示标注质量、确认四类运动学模块可用状态、提交并跟踪 annotation_kinematics 分析任务、查看 HTML 报告或导出/下载 PDF。

#### Scenario: User enters an upload page with no assets

- **WHEN** 用户进入一次训练记录的上传页且不存在任何侧面视频与标注
- **THEN** 系统 MUST 将当前工作流阶段推导为 `video_required`
- **AND** 仅展示侧面视频输入，不展示后续步骤的可操作内容

#### Scenario: Full guided loop completes

- **WHEN** 用户上传侧面视频、上传 CVAT XML、确认模块可用性并提交分析
- **THEN** 系统 MUST 在页面内持续展示真实流水线进度直至报告生成
- **AND** 报告完成后提供 HTML 报告入口与 PDF 导出/下载入口

#### Scenario: Analysis completed shows kinematics results

- **WHEN** 分析任务状态变为 `completed`
- **THEN** 系统 SHALL 自动获取并展示运动学指标数据
- **AND** 系统 SHALL 自动获取并展示可视化 artifacts
- **AND** 系统 SHALL 自动获取并展示诊断发现
- **AND** 用户 SHALL 可以在工作流页面查看完整的运动学分析结果

## ADDED Requirements

### Requirement: 工作流页面 SHALL 集成运动学结果展示

系统 SHALL 在现有工作流页面中集成运动学结果展示，无需跳转到其他页面。

#### Scenario: 运动学指标展示区域

- **WHEN** 分析完成且指标数据可用
- **THEN** 工作流页面 SHALL 在分析进度面板下方显示"运动学指标"区域
- **AND** 该区域 SHALL 展示身体姿态、上肢、下肢等维度的指标
- **AND** 每个指标 SHALL 显示名称、数值、单位

#### Scenario: 可视化 artifacts 展示区域

- **WHEN** 分析完成且 artifacts 数据可用
- **THEN** 工作流页面 SHALL 在指标区域下方显示"可视化分析"区域
- **AND** 该区域 SHALL 展示关键帧图片和图表
- **AND** 用户 SHALL 可以点击查看大图

#### Scenario: 诊断发现展示区域

- **WHEN** 分析完成且诊断发现数据可用
- **THEN** 工作流页面 SHALL 在可视化区域下方显示"诊断建议"区域
- **AND** 该区域 SHALL 按严重程度展示发现和建议
- **AND** 每个发现 SHALL 显示标题、描述、改进建议

#### Scenario: 结果区域折叠/展开

- **WHEN** 运动学结果数据加载完成
- **THEN** 工作流页面 SHALL 默认展开结果区域
- **AND** 用户 SHALL 可以折叠/展开各个结果区域
- **AND** 折叠状态 SHALL 在页面刷新后保持

### Requirement: 工作流页面 SHALL 支持运动学结果的手动刷新

系统 SHALL 支持用户手动刷新运动学结果数据，以获取最新的计算结果。

#### Scenario: 用户触发结果刷新

- **WHEN** 用户在工作流页面点击"刷新结果"按钮
- **THEN** 系统 SHALL 重新调用所有运动学相关 API
- **AND** SHALL 更新所有结果展示区域
- **AND** SHALL 显示刷新进度和结果

#### Scenario: 结果刷新失败

- **WHEN** 结果刷新 API 调用失败
- **THEN** 系统 SHALL 保持现有数据不变
- **AND** SHALL 显示刷新失败提示
- **AND** SHALL 提供重试按钮

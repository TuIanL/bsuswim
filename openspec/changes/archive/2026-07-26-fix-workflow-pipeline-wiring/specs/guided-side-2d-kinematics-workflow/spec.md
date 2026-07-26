## MODIFIED Requirements

### Requirement: Six-step guided side-view 2D kinematics workflow

系统 SHALL 在 `/sessions/:sessionId/upload` 提供可恢复的六步侧面二维运动学 Web 工作流：上传并绑定侧面视频、上传 CVAT Skeleton XML、自动解析并展示标注质量、确认四类运动学模块可用状态、提交并跟踪 annotation_kinematics 分析任务、查看 HTML 报告或导出/下载 PDF。

分析完成后，系统 SHALL 展示三个运动学结果面板（指标、可视化分析、诊断建议），其数据 SHALL 从分析任务的真实 `annotation_metric_id` 加载。

#### Scenario: User enters an upload page with no assets

- **WHEN** 用户进入一次训练记录的上传页且不存在任何侧面视频与标注
- **THEN** 系统 SHALL 将当前工作流阶段推导为 `video_required`
- **AND** 仅展示侧面视频输入，不展示后续步骤的可操作内容

#### Scenario: Full guided loop completes

- **WHEN** 用户上传侧面视频、上传 CVAT XML、确认模块可用性并提交分析
- **THEN** 系统 SHALL 在页面内持续展示真实流水线进度直至报告生成
- **AND** 报告完成后提供 HTML 报告入口与 PDF 导出/下载入口
- **AND** 运动学结果面板 SHALL 使用分析任务产出的真实 `annotation_metric_id` 加载数据

#### Scenario: Annotation metric ID is resolved from pipeline result

- **WHEN** annotation_kinematics 分析任务完成
- **THEN** 前端 SHALL 从 `AnalysisResult.raw_result.products.annotation_metric_id` 获取真实 metric ID
- **AND** `KinematicsArtifactsPanel` SHALL 使用该 ID 加载可视化数据
- **AND** `KinematicsReviewPanel` SHALL 使用该 ID 加载诊断数据
- **AND** MUST NOT 使用硬编码或默认值

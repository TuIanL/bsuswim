## Context

当前侧面二维运动学流程已经能在 CVAT/其他标注文件解析后生成 `NormalizedAnnotation` 和 `AnnotationQualityReport`。质量检查会识别 `scale`、`reference_lines.waterline`、`swim_direction`、`events.hand_entry` 和 `frame_mapping.verified` 的缺失，但 `KinematicsWorkflowPage` 目前只能展示问题，不能修改标准化标注。

现有数据模型已经具备本 Change 所需的主要字段：`scale`、`reference_lines`、`events`、`swim_direction` 存在于 `NormalizedAnnotation`，帧映射保存在 `annotation_metadata.frame_mapping`。CVAT 解析流程已有 `FrameMappingOverride`，但没有针对其余质量字段的补充接口。质量报告还定义了 `suggested_action`，但当前检查器没有系统性填充，前端也没有操作行为。

约束是：修复操作必须保留原始文件、遵循 revision 链路、复用现有质量 validator；前端需要以绑定的侧面视频为背景，不能把本功能扩展成完整 CVAT 骨架编辑器。

## Goals / Non-Goals

**Goals:**

- 在质量问题旁边提供可执行的修复入口。
- 支持在视频帧上补充标尺和水面线，并在时间轴上补充事件。
- 支持设置游泳方向和确认 annotation/source video frame mapping。
- 保存后递增 normalized annotation revision，重新验证质量并返回最新 readiness。
- 让修复后的数据参与后续 analysis submit，并保持 quality snapshot 的 revision 一致性。
- 提供足够的后端和前端测试覆盖换算、坐标、事件、映射确认和问题去重。

**Non-Goals:**

- 不编辑 CVAT 原始 XML，不覆盖原始上传文件。
- 不实现逐帧骨架点拖拽、轨迹插值或完整 CVAT 替代能力。
- 不自动推断用户未确认的物理标尺、水面线或游泳方向。
- 不改变既有质量规则的阈值和运动学计算公式。

## Decisions

### 1. 修复写入新的 normalized annotation revision

采用 `POST /api/normalized-annotations/{id}/quality-repair` 保存修复。服务读取当前 annotation，在事务中合并允许修改的字段、递增 `revision`、更新 `annotation_metadata` 并重新运行 validator。原始 AnnotationFile 和旧 revision 保留。

不选择直接修改原始文件：原始文件可能来自外部工具，修改会破坏可追溯性；也不新增独立质量问题表，因为质量问题是由当前 annotation revision 派生的快照。

### 2. 使用 typed repair payload，并限制可修改字段

请求体使用 Pydantic schema，允许以下操作：

- `scale`: 两个参考点、真实长度和可选方法/说明；服务计算并校验 `pixels_per_meter`。
- `waterline`: 两个点和可选 confidence，转换为 `reference_lines.waterline`。
- `swim_direction`: `left_to_right` 或 `right_to_left`。
- `events`: 新增或替换指定事件，事件必须包含名称、帧号、时间和来源。
- `frame_mapping`: affine/identity 参数和显式 `confirmed`。

服务拒绝任意 JSONB merge，避免客户端修改关键点、质量快照或不属于本工作台的数据。

### 3. 前端采用统一工作台而不是多个弹窗

质量面板通过 `suggested_action.type` 打开同一个 `AnnotationQualityRepairWorkbench`，工作台按步骤显示：几何参考、方向、事件、帧映射、复核保存。视频使用已绑定的 side video；通过 HTMLVideoElement 的 `currentTime` 定位帧，画布叠加层保存相对于原始视频分辨率的坐标，而不是保存 CSS 缩放后的坐标。

采用单工作台可以共享视频加载、帧步进、撤销当前草稿和重新验证状态。简单 `el-dialog + 表单` 不足以支持画布坐标和时间轴操作。

### 4. 标尺和水面线使用原始像素坐标

前端根据视频 intrinsic width/height 将画布坐标映射回原始像素坐标。水面线保存两个点，指标层继续使用现有 `waterline_y_at_x` 插值；标尺保存两个点和真实长度，服务计算线段像素长度与 `pixels_per_meter`。

不保存归一化坐标作为 canonical 数据，因为现有 metrics 和测试均使用像素坐标，且同一视频的分辨率是稳定上下文。

### 5. 事件以追加/替换语义保存并去重

同一事件名称、同一帧号和同一侧视为重复；服务在保存时去重并按 frame 排序。工作台默认新增 `hand_entry`，同时允许补充 profile 声明的其他必需事件。不会自动生成周期事件或插值事件。

### 6. 帧映射确认复用现有 FrameMappingOverride

工作台提交 `mode`、`source_frame_offset`、`source_frame_stride` 和 `confirmed=true`，服务将其转换为现有 `FrameMapping`，并设置 `verification_reason=user_confirmed`。映射确认只在用户明确点击确认后生效；前端展示 annotation frame 与 source video frame 的样例预览，防止仅凭默认值误确认。

### 7. 质量问题按 code 合并但不改变底层 issue 数量

前端展示层按 `issue.code` 合并重复提示，保留最严重 severity、blocking 状态、模块集合和所有修复入口。后端仍保留 validator 的原始 issue 列表，确保审计和 metrics 聚合不丢失信息。重复的 `SCALE_INVALID`/`SCALE_MISSING` 类用户文案由 suggested action 统一引导到“补充标尺”。

### 8. 保存后重新验证，提交分析使用最新 revision

修复 API 返回 normalized annotation、quality、analysis readiness 和 revision。前端刷新当前选择；`useKinematicsWorkflow.canSubmit` 只基于最新 revision。分析提交时沿用已有 `annotation_id + annotation_revision + annotation_quality_snapshot`，避免任务继续使用旧质量快照。

## Risks / Trade-offs

- [视频帧与标注帧未必一一对应] → 工作台明确显示两种帧号；未经 `confirmed=true` 的映射不能解除时间指标阻断。
- [用户在缩放画布上误标坐标] → 使用 intrinsic video 尺寸转换，显示端点和数值预览，保存前执行范围与正长度校验。
- [一个修复影响多个模块] → 保存后统一运行完整 validator，前端展示最新 module readiness，不在客户端猜测指标可用性。
- [并发修改造成 revision 覆盖] → 请求携带 `expected_revision`；不匹配时返回冲突，要求刷新后重新编辑。
- [浏览器视频无法加载或跨域] → 工作台复用现有 media URL 解析和视频错误状态；无法加载时允许设置方向/手工帧映射，但禁用依赖画布和时间轴的操作。
- [不同来源字段语义不同] → 第一版仅对 side view 和可写入现有 normalized schema 的来源开放；其他来源返回不可修复提示。

## Migration Plan

1. 先部署后端 schema、修复 service/API 和兼容响应字段；不需要数据库 migration。
2. 部署前端工作台，旧质量响应没有 `suggested_action` 时使用 issue code 的兼容映射。
3. 对已有 annotation，首次修复时从当前 revision 开始递增；不批量改写历史数据。
4. 回滚时停止前端入口即可；后端修复记录仍是合法 normalized annotation revision，不影响原有分析读取。

## Open Questions

- 标尺默认真实长度是否优先使用泳池长度、泳道标记长度，还是每次都要求用户填写？设计按每次填写处理，避免把泳池长度误当作画面内参考长度。
- 是否需要在第一版支持 `catch_start` 和 `pull_end` 的批量标记？设计允许事件类型扩展，但 UI 第一版默认聚焦 `hand_entry`。
- 视频帧数或 FPS 不可信时，时间轴应显示“按帧定位”并要求用户确认，还是完全禁止事件补标？当前设计允许按帧定位，但保存时仍保留低置信度警告。

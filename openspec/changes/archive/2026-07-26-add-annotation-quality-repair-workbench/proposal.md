## Why

上传 CVAT 标注后，系统已经能够识别缺少标尺、水面线、游泳方向、入水事件和帧映射确认等问题，但用户只能看到警告，无法在当前分析流程中直接修复。用户需要离开系统、修改原始标注文件或重新导入，导致质量门禁无法形成可操作的闭环，也容易造成重复警告和无效重试。

现在新增一个面向侧面视频的标注质量修复工作台：用户可以在视频帧上补充几何参考信息、在时间轴上补充事件、确认帧映射，保存后自动重新验证并更新模块可用性。

## What Changes

- 在标注质量面板中为可修复问题提供操作入口，并按稳定 issue code 合并重复问题。
- 新增质量修复工作台，支持视频帧预览、帧定位、画布交互标线和表单输入。
- 支持补充标尺：在帧上选择两个参考点并填写真实长度，生成 `scale.pixels_per_meter`。
- 支持补充水面线：在帧上选择两个点，保存为 `reference_lines.waterline`。
- 支持设置游泳方向：选择左到右或右到左。
- 支持在视频时间轴上标记 `hand_entry` 等必需事件，并保存帧号和时间。
- 支持确认或修正 annotation frame 到 source video frame 的 affine/identity 映射，并写入 `verified=true` 和确认原因。
- 新增保存质量修复和重新验证的 API；保存后递增 annotation revision，重新计算质量报告和分析 readiness。
- 质量报告返回可执行的 `suggested_action`，前端据此打开对应修复步骤。
- 修复后刷新质量面板和运动学模块可用性；仍未满足条件的问题继续阻断或降级相应模块。
- 保留原始上传文件和历史 revision，修复数据作为标准化标注的后续版本保存。
- 不新增完整逐帧骨架编辑能力，不替代 CVAT。

## Capabilities

### New Capabilities

- `annotation-quality-repair-workbench`: 在视频帧和时间轴上补充质量检查所需的几何参考、方向、事件和帧映射确认，并保存修复结果。

### Modified Capabilities

- `annotation-quality`: 质量问题需要提供稳定的可执行操作信息；质量报告支持按 issue code 去重，并在修复后重新验证。
- `automatic-annotation-ingestion-workflow`: 标准化标注支持在导入后提交质量修复、递增 revision 和重新生成 readiness。

## Impact

- 前端：`KinematicsWorkflowPage`、`AnnotationQualityPanel`、CVAT 标注步骤，以及新增的视频帧修复工作台和画布交互组件。
- Backend：normalized annotation service、annotation quality validator、质量修复 API、revision 和质量快照处理。
- API：新增质量修复读取/保存/重新验证接口，扩展质量问题的 `suggested_action` 契约。
- 数据：继续使用现有 `scale`、`reference_lines`、`events`、`swim_direction` 和 `annotation_metadata.frame_mapping` JSONB 字段；不新增独立质量问题表。
- 测试：增加几何标线换算、事件保存、帧映射确认、revision、质量去重和前端交互测试。

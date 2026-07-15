## Why

当前系统仅支持 Kinovea 导出的 JSON/CSV 标注格式作为数据输入，但标注工具已切换到 CVAT。CVAT 使用 COCO 17 点骨架格式，导出 XML（Task 格式）和 COCO JSON 两种形式，数据结构与 Kinovea 有本质区别——CVAT 只有骨架关键点，不含划水事件、轨迹和人工标签。需要新增 CVAT XML 解析能力，同时借此次重构把时间轴、标注覆盖和可见性语义在 NormalizedAnnotation 层真正定稳。

## What Changes

- 新增 `source=cvat` 标注来源，扩展 `AnnotationSource` 枚举
- 实现 CVAT XML 解析器（`cvat_xml.py`），提取 COCO 17 点骨架关键点
- 实现 `AnnotationDerivedDataBuilder`，从 keypoint_frames 推导轨迹和身体中心
- 扩展 `normalized-annotation-schema`：
  - `KeypointPoint.x/y` 改为 `float | null`
  - `visibility` 增加 `"missing"` 选项
  - `KeypointFrame` 增加 `annotation_frame`、`source_video_frame`、`timestamp_sec`、`image_name`
  - 顶层增加 `frame_mapping`、`video`、`annotation_sequence`、`analysis_ranges`、`annotation_coverage` 结构
- 质量检测器适配 `source=cvat` 下 events 和 scale 缺失场景，按模块分级可用性（角度/轨迹可用，时间/距离不可用）
- add-cvat-skeleton-import 作为新能力，保持 Kinovea parser 继续可用

## Capabilities

### New Capabilities
- `cvat-xml-parse`: 解析 CVAT Task XML 格式的骨架标注，提取 COCO 17 点关键点，处理 outside/occluded 可见性语义，按 frame 聚合多 track 骨架
- `annotation-time-mapping`: 定义 frame → timestamp 的四模式映射（explicit/affine/identity/unknown），保存时间轴 meta 到 NormalizedAnnotation，metrics 层以 `timestamp_sec` 为权威时间源
- `annotation-derivation`: 独立的数据派生层，从标准化 keypoint_frames 推导轨迹、身体中心线、可见性摘要，按 parse service 同步调用但不污染 parser

### Modified Capabilities
- `normalized-annotation-schema`: schema_version 升级到 `swim-annotation.v2`，KeypointPoint 支持 nullable x/y 和 `missing` visibility，KeypointFrame 增加帧级时间映射字段，新增顶层 video/annotation_sequence/analysis_ranges 结构
- `annotation-quality`: quality 规则适配 `source=cvat` 下的 events/scale 缺失，按指标类型分模块可用性（角度/轨迹可算，速度/划频/距离不可算）

## Impact

- `backend/app/models/annotation.py` — 扩展 `AnnotationSource` 枚举
- `backend/app/models/normalized_annotation.py` — 模型字段变更（可空 x/y、新字段）
- `backend/app/schemas/normalized_annotation.py` — Pydantic schema v2 升级
- `backend/app/services/parsers/cvat_xml.py` — **新增** CVAT XML 解析器
- `backend/app/services/parsers/__init__.py` — 导出新 parser
- `backend/app/services/annotation_derivation/trajectory_builder.py` — **新增** 轨迹推导服务
- `backend/app/services/annotation_derivation/body_center_builder.py` — **新增** 身体中心推导
- `backend/app/services/normalized_annotation_service.py` — parse 链路接入派生层
- `backend/app/services/annotation_file_service.py` — 允许 `xml` 作为 CVAT 来源的文件类型
- `backend/app/services/annotation_quality/` — quality profile 新增 cvat 规则
- `backend/app/services/metrics/` — metrics 层适配 `timestamp_sec` 权威时间源
- `backend/tests/` — 新增 CVAT parser 测试、派生层测试
- `backend/alembic/` — schema v2 迁移

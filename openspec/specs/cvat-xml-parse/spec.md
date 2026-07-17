# cvat-xml-parse Specification

## Purpose
解析 CVAT Task XML 格式的骨架标注文件，提取 COCO 17 点骨架关键点，处理 outside/occluded 可见性语义，按 frame 分组多 track 骨架，输出原始 keypoint_frames（无时间戳、无轨迹、无派生数据）。

## Requirements

### Requirement: Parse CVAT Task XML skeleton annotations
系统 SHALL 支持解析符合 CVAT 1.1 Task XML 规范的标注文件，从 `<track>` 元素中提取 `<skeleton>` 和 `<points>` 子结构。

#### Scenario: Parse valid CVAT XML with skeleton tracks
- **WHEN** 输入为有效的 CVAT Task XML，包含 `<track>` 元素，每个 track 包含 `<skeleton>` 子元素，skeleton 内含 `<points>` 关键点
- **THEN** 系统 MUST 提取所有 track 中 `outside="0"` 的 skeleton，按 frame 编号分组，输出 `RawCvatKeypointFrame[]`

#### Scenario: Parse XML with multiple single-frame tracks
- **WHEN** XML 包含多个 `<track>` 元素，每个 track 只有一帧 `outside="0"` 的 skeleton
- **THEN** 系统 MUST 将每个 `outside="0"` 的 skeleton 按 frame 编号分组，同一 frame 只有一个 skeleton 时正常输出

### Requirement: Parser outputs raw keypoint frames without timestamps
Parser SHALL 输出 `raw_keypoint_frames`，不含 `source_video_frame`、`timestamp_sec`、`image_name`。时间映射由 `CvatAnnotationNormalizer` 独立完成。

#### Scenario: Raw frame has annotation_frame and points only
- **WHEN** parser 完成 XML 提取
- **THEN** 每个 `RawCvatKeypointFrame` MUST 包含 `annotation_frame`、`points`、`source_track_ids`，MUST NOT 包含 `source_video_frame` 或 `timestamp_sec`

### Requirement: Multiple active skeletons in same frame are rejected
同一 frame 编号出现两个以上 `outside="0"` 的 skeleton 时，系统 SHALL 视为多人标注，阻止 parse。

#### Scenario: Two skeletons same frame blocks parse
- **WHEN** 某 frame 有两个不同 track 的 skeleton 且均为 `outside="0"`
- **THEN** 系统 MUST 产生 `MULTIPLE_ACTIVE_SKELETONS` error，阻止 parse，`annotation_file.status` 设为 `parse_failed`

#### Scenario: Single skeleton per frame succeeds
- **WHEN** 所有 frame 最多只有一个 `outside="0"` 的 skeleton
- **THEN** 系统 MUST 正常解析，不产生多骨架错误

### Requirement: source_track_id recorded for provenance
每个 `RawCvatKeypointFrame` SHALL 记录来源的 CVAT track ID，仅作为追溯和调试用途。

#### Scenario: Track provenance recorded
- **WHEN** parser 提取 skeleton
- **THEN** `RawCvatKeypointFrame` MUST 包含 `source_track_ids: list[str]`，列出该 frame 所有有效 skeleton 的 track ID

### Requirement: Parse <meta> for frame range and labels
系统 SHALL 从 `<meta>` 元素中读取任务元数据，包括帧范围、标签定义和图片尺寸。

#### Scenario: Extract meta information
- **WHEN** XML 包含 `<meta><job>` 子结构
- **THEN** 系统 MUST 提取 `start_frame`、`stop_frame`、`size`（帧总数），以及标签定义中的关键点名称和骨架连接关系

### Requirement: COCO 17 point skeleton name mapping
系统 SHALL 将 CVAT XML 中的 COCO 17 点名称（kebab-case）映射为内部 snake_case 关键点名。

#### Scenario: Map hyphenated COCO names to snake_case
- **WHEN** points label 为 `left-shoulder`、`right-elbow`、`left-wrist` 等
- **THEN** 系统 MUST 替换连字符为下划线，生成 `left_shoulder`、`right_elbow`、`left_wrist`

#### Scenario: Five face keypoints are preserved
- **WHEN** points label 为 `nose`、`left-eye`、`right-eye`、`left-ear`、`right-ear`
- **THEN** 系统 MUST 仍保留这些关键点，不做丢弃或过滤

### Requirement: outside flag determines skeleton visibility

系统 SHALL 根据 `<points>` 的 `outside` 属性决定关键点的可见性状态。

#### Scenario: Everything outside=1 skips skeleton
- **WHEN** skeleton 内所有 points 均为 `outside="1"`
- **THEN** 系统 MUST 跳过整副 skeleton，不生成原始帧记录

#### Scenario: Partial outside=1 marks individual points missing
- **WHEN** skeleton 内部分 points 为 `outside="1"`，其余为 `outside="0"`
- **THEN** 系统 MUST 保留该 skeleton，`outside="1"` 的 points 标记为 `visibility="missing"`，坐标设为 None

#### Scenario: outside=1 residual coordinates are discarded
- **WHEN** `outside="1"` 的 point 携带坐标值
- **THEN** 系统 MUST 丢弃这些坐标，不在 RawCvatPoint 中使用

### Requirement: occluded flag maps to visibility
系统 SHALL 将 `<points>` 的 `occluded` 属性映射为 KeypointPoint 的可见性。

#### Scenario: occluded=0 maps to visible
- **WHEN** points 为 `outside="0"` 且 `occluded="0"`
- **THEN** 该点的 visibility MUST 为 `"visible"`，保留坐标

#### Scenario: occluded=1 maps to occluded
- **WHEN** points 为 `outside="0"` 且 `occluded="1"`
- **THEN** 该点的 visibility MUST 为 `"occluded"`，保留坐标，confidence 为 null

### Requirement: CVAT XML parser returns pure data without database access
系统 SHALL 确保 CVAT XML parser 不直接访问数据库，返回纯数据对象。

#### Scenario: Parser testable without database
- **WHEN** 调用 CVAT XML parser
- **THEN** parser MUST 返回纯数据对象，不依赖 Session、ORM 或数据库连接

### Requirement: XML security hardening
Parser SHALL 按不可信输入处理用户上传的 XML 文件。

#### Scenario: XML with DTD rejected
- **WHEN** 上传的 XML 包含 DTD 或实体声明
- **THEN** 系统 MUST 拒绝解析并返回明确的错误信息

#### Scenario: NaN or Infinity coordinates rejected
- **WHEN** points 坐标包含 NaN、Infinity 或负数
- **THEN** 系统 MUST 拒绝并报错

## ADDED Requirements

### Requirement: Parser uses single-pass streaming

系统 SHALL 使用 `ET.iterparse()` 单次流式遍历 XML 文件，同时读取 `<meta>` 元素和 `<track>` 元素，不得使用 `ET.parse()` 完整加载 DOM。

#### Scenario: Single-pass iterparse without DOM
- **WHEN** 调用 `parse_cvat_xml(file_path)`
- **THEN** 系统 MUST 仅调用 `ET.iterparse()`，不得调用 `ET.parse()`
- **AND** 系统 MUST 在完成每个 track 后调用 `elem.clear()`

### Requirement: RawCvatPoint uses nullable coordinates

`RawCvatPoint.x` 和 `RawCvatPoint.y` SHALL 允许为 null。`outside="1"` 的关键点使用 `x=None, y=None, visibility="missing"`，不得使用 `(0.0, 0.0)` 作为哨兵值。

#### Scenario: outside=1 produces null coordinates
- **WHEN** CVAT XML 中某关键点 `outside="1"`
- **THEN** `RawCvatPoint.x` MUST 为 None，`RawCvatPoint.y` MUST 为 None，`visibility` MUST 为 `"missing"`

#### Scenario: outside=0 preserves coordinates
- **WHEN** CVAT XML 中某关键点 `outside="0"` 且存在坐标
- **THEN** `RawCvatPoint.x` MUST 为 float，`RawCvatPoint.y` MUST 为 float

### Requirement: RawCvatPoint visibility-coordinate consistency

`RawCvatPoint` SHALL 通过 Pydantic model_validator 确保坐标与可见性状态一致。

#### Scenario: missing with coordinates rejected
- **WHEN** `visibility = "missing"` 且 `x` 或 `y` 不为 None
- **THEN** 验证 MUST 失败，抛出 ValueError

#### Scenario: visible with None coordinates rejected
- **WHEN** `visibility = "visible"` 且 `x` 为 None 或 `y` 为 None
- **THEN** 验证 MUST 失败，抛出 ValueError

### Requirement: Parser returns structured errors

Parser error SHALL 包含结构化字段 `code`、`frame`（可选）和 `track_ids`（可选），而非纯文本字符串。

#### Scenario: Multiple active skeletons returns structured error
- **WHEN** 同一 frame 有两个以上 active skeleton
- **THEN** `CvatParseError.code` MUST 为 `"MULTIPLE_ACTIVE_SKELETONS"`
- **AND** `CvatParseError.frame` MUST 包含触发帧号
- **AND** `CvatParseError.track_ids` MUST 包含冲突的 track ID 列表

### Requirement: Parser uses file-size and record-count capacity limits

Parser SHALL 基于文件大小（100MB）、骨架记录数（50000）和有效帧数（20000）设置安全限制，不得使用 `MAX_TRACK_COUNT` 静默截断。

#### Scenario: File exceeds size limit
- **WHEN** XML 文件大于 100MB
- **THEN** parser MUST 以 `parse_failed` 拒绝

#### Scenario: Skeleton records exceed limit
- **WHEN** XML 中 skeleton 记录超过 50000 条
- **THEN** parser MUST 以 `parse_failed` 拒绝

#### Scenario: Over 200 one-frame tracks pass through
- **WHEN** XML 包含超过 200 个 track，每个 track 仅一帧 skeleton，且文件在安全限制内
- **THEN** 所有 active frame MUST 被解析，不得静默丢弃

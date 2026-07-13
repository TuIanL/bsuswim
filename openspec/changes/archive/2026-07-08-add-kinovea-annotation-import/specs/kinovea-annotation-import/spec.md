# kinovea-annotation-import Specification

## Purpose
将 Kinovea 导出的原始标注文件（JSON 和固定列名 CSV 两种格式）解析为 `swim-annotation.v1` 兼容的标准化标注数据，打通"上传 → parse → NormalizedAnnotation → quality validation"的完整导入链路。

## ADDED Requirements

### Requirement: Kinovea JSON annotation parse
系统 SHALL 支持解析符合 Kinovea-assisted JSON 规范的标注文件，提取 events、keypoint_frames、trajectories、manual_tags、scale 等字段。

#### Scenario: Parse valid Kinovea JSON
- **WHEN** `annotation_file.file_type = "json"` 且 `annotation_file.source = "kinovea"`，调用 `POST /api/v1/annotations/{annotation_file_id}/parse`
- **THEN** 系统 MUST 从文件读取 JSON，规范化事件（`labeled_by = "kinovea"`）、关键帧、轨迹和人工标签，生成 normalized annotation 记录

#### Scenario: Missing scale in JSON is allowed
- **WHEN** Kinovea JSON 缺少 `scale` 或 `scale.pixels_per_meter`
- **THEN** 系统 MUST 仍然创建 normalized annotation，quality.level 为 `warning`，`disabled_modules` 包含 `speed_distance`

### Requirement: Kinovea CSV annotation parse
系统 SHALL 支持解析固定列名的 Kinovea CSV 标注文件，按 `type` 列将行分派为 event、keypoint、trajectory 或 tag。

#### Scenario: Parse CSV with event and keypoint rows
- **WHEN** CSV 包含 `type, name, label, frame, time_sec, side, point, x, y, tag, severity, comment` 列且内容有效
- **THEN** 系统 MUST 将 `type=event` 行转为 events，`type=keypoint` 行按 frame 聚合为 keypoint_frames，`type=tag` 行转为 manual_tags

#### Scenario: CSV keypoint rows aggregated by frame
- **WHEN** CSV 多个 keypoint 行具有相同 `frame`
- **THEN** 系统 MUST 将所有该 frame 的关键点聚合到同一个 keypoint_frame 的 `points` 字典中

#### Scenario: CSV missing required columns
- **WHEN** CSV 缺少 `type`、`frame`、`x`、`y` 中的任一列
- **THEN** 系统 MUST 抛出 `KinoveaParseError`，返回 400，并将 `annotation_files.status` 更新为 `parse_failed`

### Requirement: Trust annotation_file.file_type for format selection
系统 SHALL 根据 `annotation_file.file_type` 选择 parser 实现，MVP 不做内容格式嗅探。

#### Scenario: file_type is csv but content is JSON
- **WHEN** `annotation_file.file_type = "csv"` 但实际文件为 JSON
- **THEN** 系统 MUST 尝试按 CSV 解析，失败后返回明确的错误信息，提示用户检查 file_type

### Requirement: time_sec inference from frame and fps
当 CSV 行缺少 `time_sec` 时，parser SHALL 通过 `frame / fps` 自动推导。

#### Scenario: time_sec inferred successfully
- **WHEN** CSV 行有 `frame` 和 `fps` 但无 `time_sec`
- **THEN** parser MUST 计算 `time_sec = frame / fps`，精确到毫秒

#### Scenario: time_sec and fps both missing
- **WHEN** CSV 行既无 `time_sec` 也无 `fps`
- **THEN** 系统 MUST 抛出 `KinoveaParseError`，要求至少提供其一

### Requirement: Keypoint name alias mapping
Parser SHALL 内置关键点别名映射，将中英文通用名称转换为标准关键点名。

#### Scenario: Chinese point name mapped to standard
- **WHEN** CSV keypoint 行的 `point` 值为 "肩" 或 "shoulder"
- **THEN** parser MUST 将其映射为 `right_shoulder`

#### Scenario: Unknown point name passed through
- **WHEN** CSV keypoint 行的 `point` 值不在 alias 映射表中
- **THEN** parser MUST 保留原始名称并在 warnings 中提示

### Requirement: Parser returns pure data without database access
Kinovea parser SHALL 返回纯数据对象 `ParsedKinoveaAnnotation`，不直接访问数据库。

#### Scenario: Parser testable without database
- **WHEN** 调用 `parse_kinovea_annotation(file_path, file_type="csv", ...)`
- **THEN** parser MUST 返回 `ParsedKinoveaAnnotation` 对象，不依赖 `Session` 或 ORM

### Requirement: Semantic warnings for missing recommended events
Parser SHALL 检查推荐事件（hand_entry、catch_start、pull_end、cycle_start、cycle_end）是否存在，缺失时生成 warnings 但不阻止 parse 成功。

#### Scenario: Missing hand_entry generates warning
- **WHEN** 解析后的 events 不包含 `hand_entry`
- **THEN** parser MUST 在 `warnings` 中添加提示，但 parse 仍然成功

#### Scenario: All recommended events present
- **WHEN** events 包含所有推荐事件
- **THEN** parser MUST 不生成语义 warnings

### Requirement: Event name normalization
Parser SHALL 将事件名统一为英文 code，中文展示名仅作为 label。

#### Scenario: Event name is English code
- **WHEN** CSV 行 `name = "hand_entry"`
- **THEN** parser MUST 保留 `name = "hand_entry"`，`label` 使用 CSV 提供的 label 或默认中文映射

#### Scenario: Event name is Chinese
- **WHEN** CSV 行 `name = "入水"`
- **THEN** parser MUST 通过映射将 `name` 转为 `hand_entry`，`label` 保留为 "入水"

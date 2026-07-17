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

## MODIFIED Requirements

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

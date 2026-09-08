## ADDED Requirements

### Requirement: source_of_truth 由 AnalysisTask 显式引用驱动

系统 SHALL 使用 `source_of_truth` 枚举（`manual_segments` / `imported_events`）裁决人工区间与 imported events 谁是权威输入，不使用布尔标记。裁决 MUST 完全由 `AnalysisTask.reference_annotation_revision_id` 驱动，系统 MUST NOT 通过"发现数据库存在已发布人工 revision"自动切换。`source_of_truth` 是解析结果，MUST NOT 作为 set 或 revision 的存储字段。系统 MUST 始终维持「一个权威输入 → 派生表示」，而不是两套数据相互同步。

#### Scenario: 任务显式指定 revision 时人工为权威

- **WHEN** `AnalysisTask.reference_annotation_revision_id` 非空且 resolver 返回 `ready`
- **THEN** `source_of_truth` MUST 解析为 `manual_segments`，且 MUST 严格消费该 revision

#### Scenario: 任务未指定时回退 legacy 行为

- **WHEN** `AnalysisTask.reference_annotation_revision_id` 为 NULL
- **THEN** `source_of_truth` MUST 解析为 `imported_events`

#### Scenario: 多个已发布 revision 时不自动挑选

- **WHEN** 同一 session video 存在多个 `reviewed` / `frozen` revision 且任务未显式引用
- **THEN** 系统 MUST NOT 自行选择其中一个，MUST 解析为 `imported_events` 并在 warning 中提示需显式指定

#### Scenario: draft revision 不可被任务引用

- **WHEN** 调用方尝试创建引用 `draft` revision 的分析任务
- **THEN** 系统 MUST 拒绝，MUST NOT 让运行期间可变的 draft 标注成为分析输入

#### Scenario: 布尔标记未被使用

- **WHEN** 检查权威裁决的数据模型
- **THEN** 系统 MUST NOT 使用 `is_authoritative` 之类的布尔字段表达权威来源

#### Scenario: source_of_truth 不作为存储字段

- **WHEN** 检查 set 与 revision 的表结构
- **THEN** 两者 MUST NOT 包含 `source_of_truth` 列；该值只作为解析结果记录在分析产物上

### Requirement: 显式引用不可用时阻断而非回退

系统 SHALL 在 `AnalysisTask` 显式指定了 reference revision 但该 revision 不可用时返回 `reference_input_invalid` 并阻断相关分析，MUST NOT 回退到 imported events 或其他 revision。

#### Scenario: revision 被删除时阻断

- **WHEN** 任务引用了不存在的 revision
- **THEN** 系统 MUST 返回 `reference_input_invalid`，MUST NOT 改用 imported events 继续分析

#### Scenario: checksum 不匹配时阻断

- **WHEN** 任务引用的 revision 与当前视频 checksum 不一致
- **THEN** 系统 MUST 返回 `reference_input_invalid`，MUST NOT 改用 imported events

#### Scenario: profile 不匹配时阻断

- **WHEN** 任务快照的 `phase_profile_hash` 与 revision 记录的不一致
- **THEN** 系统 MUST 返回 `reference_input_invalid`，MUST NOT 改用其他 revision

#### Scenario: 未指定时的回退仍允许但必须记录

- **WHEN** 任务未指定 reference revision
- **THEN** 系统 MUST 允许回退到 imported events，并 MUST 在 quality 或 warning 中显式记录该回退

### Requirement: 人工区间派生边界事件供现有 metrics 使用

当人工标注完整时，adapter SHALL 从 phase 区间稳定派生 `hand_entry` / `catch_start` / `pull_end` / `hand_exit` 边界事件，供既有 `rhythm_metrics` 与 metrics 引擎消费。

#### Scenario: 完整人工区间派生四边界

- **WHEN** 某 cycle 的 `entry` / `catch` / `push` / `recovery` 四段齐全
- **THEN** adapter MUST 派生出 `hand_entry` = `entry.start_time_sec`、`catch_start` = `catch.start_time_sec`、`pull_end` = `push.start_time_sec`、`hand_exit` = `push.end_time_sec`

#### Scenario: 派生事件标记来源为人工

- **WHEN** adapter 从人工区间派生边界事件
- **THEN** 派生事件的 `labeled_by` MUST 为 `manual`，且 MUST 携带源 `revision_id`

#### Scenario: 派生事件按 side 分组

- **WHEN** 左右臂区间分别标注
- **THEN** 派生事件 MUST 保留各自 `side`，MUST NOT 混并为 unknown

### Requirement: imported events 派生区间仅在四边界齐全时完整生成

adapter SHALL 在从 imported events 派生区间时，仅当四个边界齐全才生成完整四阶段；边界缺失时 MUST 返回 partial derivation，MUST NOT 猜测。

#### Scenario: 缺 hand_exit 时返回 partial derivation

- **WHEN** 同源事件缺少 `hand_exit`
- **THEN** adapter MUST 只生成 `entry` 与 `catch`，并对 `push` / `recovery` 标记 `recovery_unavailable` 与 `missing_hand_exit`

#### Scenario: 四边界齐全时生成完整区间

- **WHEN** 同源事件包含 `hand_entry` / `catch_start` / `pull_end` / `hand_exit`
- **THEN** adapter MUST 生成完整四阶段，并标记 `derivation = "event_derived"`

#### Scenario: 派生区间降级标注置信度

- **WHEN** 区间由 events 派生而来
- **THEN** 该区间的 `derivation` MUST 为 `event_derived`，`confidence` MUST 低于人工标注，MUST NOT 与 `manual` 混淆

### Requirement: 派生结果一律不回写任一侧

adapter SHALL 保证派生结果只作为下游输入，永不写回人工 segment 或 imported events。

#### Scenario: segments 派生事件不写回 events

- **WHEN** adapter 从人工区间派生出边界事件供 metrics 使用
- **THEN** 系统 MUST NOT 将这些事件写入 `normalized_annotations.events`

#### Scenario: events 派生区间不写回 segments

- **WHEN** adapter 从 imported events 派生出区间
- **THEN** 系统 MUST NOT 在 `manual_phase_segments` 中创建对应记录

#### Scenario: 派生结果需要缓存时独立存储

- **WHEN** 系统需要缓存派生结果
- **THEN** 派生数据 MUST 存入独立的 derived 存储并携带 `source_signature`，MUST NOT 出现在 `manual_phase_segments` 中

### Requirement: 冲突只告警不自动修复

系统 SHALL 在人工区间与 imported events 语义冲突时生成 conflict / warning，MUST NOT 自动双向同步或静默覆盖。

#### Scenario: 边界时间偏差产生 conflict

- **WHEN** 人工 `entry.start_time_sec` 与同源 `hand_entry` 事件时间偏差超过阈值
- **THEN** 系统 MUST 生成 conflict 记录并保留两侧原始值，MUST NOT 自动调整任一侧

#### Scenario: 阶段缺失产生 warning

- **WHEN** 人工 revision 中某 cycle 缺少 `recovery` 而同源事件存在 `hand_exit`
- **THEN** 系统 MUST 生成 warning，MUST NOT 自动补齐缺失阶段

### Requirement: compatibility adapter 提供秒到帧的转换

为兼容既有以 `(frame, fps)` 为时间源的 metrics 实现，adapter SHALL 提供 `秒 → 帧` 转换。该转换属于 compatibility 层，MUST NOT 反向定义数据模型。

#### Scenario: 转换使用 frame_basis 中的 fps

- **WHEN** adapter 将 `start_time_sec = 1.234` 转为帧号且 `frame_basis.fps = 30`
- **THEN** 转换结果 MUST 为 `round(1.234 * 30)`，且 MUST 记录所用 fps 与 `fps_source`

#### Scenario: frame_basis 缺失时不转换

- **WHEN** `frame_basis` 缺失或 `fps` 为空
- **THEN** adapter MUST 返回空 frame 值，MUST NOT 使用默认 fps 猜测

#### Scenario: 转换误差记入 warning

- **WHEN** `frame_basis.fps` 因 `Numeric(6, 2)` 精度限制无法精确表示实际帧率
- **THEN** 系统 MUST 记入 warning，MUST NOT 让转换误差影响 canonical 的秒值

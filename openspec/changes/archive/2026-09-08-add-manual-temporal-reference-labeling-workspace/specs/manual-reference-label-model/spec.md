## ADDED Requirements

### Requirement: 三层数据模型与 revision 引用完整性

系统 SHALL 提供 `manual_annotation_sets` / `manual_annotation_revisions` / `manual_phase_segments` 三张表。set 表示一条视频上的一套逻辑标注谱系，revision 表示某个时间点的不可变内容版本，segment 表示一条时间区间。segment MUST 通过 `revision_id` 外键引用 revision，`revision_no` 仅作展示与冗余，不承担引用完整性。

#### Scenario: segment 引用 revision 主键

- **WHEN** 系统创建一条 phase segment
- **THEN** segment 的 `revision_id` MUST 外键指向 `manual_annotation_revisions.id` 且 NOT NULL

#### Scenario: revision_no 被篡改不影响引用

- **WHEN** 某个 revision 的 `revision_no` 被修改（展示层调整）
- **THEN** 该 revision 下的所有 segment MUST 仍然通过 `revision_id` 正确归属，不受 `revision_no` 变化影响

#### Scenario: 一次查询取到完整冻结切片

- **WHEN** 调用方按 `revision_id` 查询 segments
- **THEN** 系统 MUST 返回该 revision 下全部 segment，且 MUST NOT 依赖 `set_id` + `revision_no` 组合推断

### Requirement: 标注归属固定为 session_video_id

系统 SHALL 以 `session_video_id` 作为 annotation set 的唯一归属引用。分析任务只消费某一 revision，不拥有标注。

#### Scenario: 创建 set 绑定 session video

- **WHEN** 用户为某条视频创建人工标注 set
- **THEN** 系统 MUST 将 `session_video_id` 外键指向 `session_videos.id` 且 NOT NULL

#### Scenario: set 不承载 analysis_task 外键

- **WHEN** 检查 `manual_annotation_sets` 表结构
- **THEN** 该表 MUST NOT 包含 `analysis_task_id` 字段

### Requirement: 时间 canonical 为 start_time_sec / end_time_sec

系统 SHALL 以 `start_time_sec` 与 `end_time_sec` 作为区间时间的唯一权威来源。`start_frame` / `end_frame` 为派生快照，MUST 同时记录 `frame_basis`。

#### Scenario: 创建区间以秒为权威

- **WHEN** 用户创建一条 `[1.234s, 2.567s]` 的区间
- **THEN** `start_time_sec` MUST 为 `1.234`，`end_time_sec` MUST 为 `2.567`

#### Scenario: frame 快照无 frame_basis 时为 NULL

- **WHEN** 创建区间时未提供 `frame_basis`
- **THEN** `start_frame` 与 `end_frame` MUST 为 NULL，系统 MUST NOT 用默认 fps 反推帧号

#### Scenario: frame_basis 记录 fps 来源

- **WHEN** 系统为区间生成 frame 快照
- **THEN** `frame_basis` MUST 包含 `fps`、`fps_source`、`mapping_mode`、`mapping_verified`

#### Scenario: 人工标注时间精度不依赖 SessionVideo.fps

- **WHEN** `SessionVideo.fps`（`Numeric(6, 2)`）因精度限制无法精确表示 29.97 或 59.94
- **THEN** 系统 MUST 仍以 `start_time_sec` / `end_time_sec` 为准，MUST NOT 让人工标注的时间精度受该字段影响

### Requirement: cycle_id 稳定且 side 显式

系统 SHALL 为每条 segment 记录稳定的 `cycle_id` 与显式 `side`。`cycle_index` 仅作排序与展示，允许为空。

#### Scenario: 创建 segment 带 cycle_id 与 side

- **WHEN** 用户为右臂第 2 个周期标注抱水区间
- **THEN** 该 segment MUST 记录稳定的 `cycle_id` 与 `side = "right"`

#### Scenario: 删除中间周期不导致后续漂移

- **WHEN** 用户删除同侧第 2 个周期的全部 segment，随后新增一个新周期
- **THEN** 新周期 MUST 获得新的 `cycle_id`，MUST NOT 复用被删除周期的 `cycle_id`，已有周期的 `cycle_id` MUST 保持不变

#### Scenario: cycle_index 允许乱序标注

- **WHEN** 用户先标注第 3 个周期再回头标注第 1 个周期
- **THEN** 系统 MUST 允许保存，`cycle_index` 可由系统在展示时按时间重排，MUST NOT 阻塞保存

#### Scenario: fork 时 cycle_id 被继承

- **WHEN** 系统从源 revision fork 出新 revision
- **THEN** 相同周期的 segment MUST 沿用源 revision 的 `cycle_id`，MUST NOT 重新生成

#### Scenario: 新增周期生成新 cycle_id

- **WHEN** 用户在 fork 出的 revision 中新增一个周期
- **THEN** 新周期 MUST 获得新的 `cycle_id`，MUST NOT 复用任何已有周期（含被删除周期）的 `cycle_id`

#### Scenario: cycle_id 不是全局唯一数据库键

- **WHEN** 检查 `manual_phase_segments` 的约束定义
- **THEN** 系统 MUST NOT 对 `cycle_id` 建立全局唯一约束；可选的完整性约束为 `UNIQUE(revision_id, cycle_id, side, phase_code)`

#### Scenario: 跨 revision 追溯同一周期

- **WHEN** 查询某 `cycle_id` 在 revision 2 与 revision 5 中的 segment
- **THEN** 系统 MUST 能按同一 `cycle_id` 定位到两版中的对应周期，以支持 revision diff 与一致性分析

### Requirement: side 在正式数据中收敛为 left 或 right

系统 SHALL 允许 `draft` revision 使用 `side = both` 或 `unknown`，但 MUST NOT 让这两个取值进入 `reviewed` / `frozen` 数据。

#### Scenario: draft 允许未判明左右臂

- **WHEN** 用户在 draft revision 中标注一条 `side = unknown` 的区间
- **THEN** 系统 MUST 允许保存

#### Scenario: 提交复核时拦截 both 与 unknown

- **WHEN** revision 中存在 `side` 为 `both` 或 `unknown` 的 segment 且用户提交复核
- **THEN** 系统 MUST 阻止进入 `reviewed`，并提示需收敛为 `left` 或 `right`

#### Scenario: 冻结数据只含 left 与 right

- **WHEN** 检查 `frozen` revision 的全部未删除 segment
- **THEN** 每条 segment 的 `side` MUST 为 `left` 或 `right`

### Requirement: segment 与 revision 保留完整 provenance

系统 SHALL 按以下归属保留 provenance 字段：

| 实体 | 字段 |
|---|---|
| `ManualAnnotationSet` | `created_by`、`created_at`、`updated_at`、`deleted_at` |
| `ManualAnnotationRevision` | `created_by`、`updated_by`、`reviewed_by`、`review_status`、`reviewed_at`、`created_at`、`updated_at`、`deleted_at`、`schema_version` |
| `ManualPhaseSegment` | `created_by`、`updated_by`、`reviewed_by`、`review_status`、`confidence`、`note`、`created_at`、`updated_at`、`deleted_at`、`schema_version` |

#### Scenario: 创建 segment 记录创建者

- **WHEN** 用户创建一条 segment
- **THEN** 系统 MUST 写入 `created_by`、`created_at`、`schema_version`

#### Scenario: 复核写入复核者与状态

- **WHEN** 专家将某 revision 复核通过
- **THEN** 系统 MUST 在 revision 与其 segment 上写入 `reviewed_by`、`review_status`、`reviewed_at`

### Requirement: confidence 为人工判据置信度且允许为空

系统 SHALL 将 `confidence` 定义为"边界本身是否清晰"的人工评估，MUST NOT 由 `review_status` 自动推导。`confidence` 允许为 NULL。

#### Scenario: 边界不清晰时人工填低置信度

- **WHEN** 标注员因水花遮挡难以判断入水瞬间，填写 `confidence = 0.4`
- **THEN** 系统 MUST 保存该值，MUST NOT 覆盖为其他值

#### Scenario: 复核通过不自动改为满置信度

- **WHEN** 某 segment 的 `confidence = 0.4` 且所属 revision 被复核通过
- **THEN** `confidence` MUST 保持 `0.4`，系统 MUST NOT 因 `review_status` 变为 reviewed 而自动置为 `1.0`

#### Scenario: 未评估时允许为空

- **WHEN** 标注员未填写置信度
- **THEN** `confidence` MUST 为 NULL，系统 MUST NOT 填入默认值

### Requirement: draft revision 具备乐观锁

系统 SHALL 为 draft revision 提供 `edit_version` 乐观锁，防止并发编辑静默覆盖。

#### Scenario: 版本号随编辑递增

- **WHEN** draft revision 的 segment 发生增删改
- **THEN** `edit_version` MUST 递增

#### Scenario: 版本不匹配时拒绝写入

- **WHEN** 客户端携带的 `edit_version` 小于 revision 当前值
- **THEN** 系统 MUST 返回 409，MUST NOT 静默覆盖后保存方之前的修改

#### Scenario: 前端收到 409 时提示刷新

- **WHEN** 前端写请求收到 409
- **THEN** 前端 MUST 提示用户刷新后重试，MUST NOT 自动重试提交

### Requirement: 删除为 soft delete

系统 SHALL 对 segment 的删除执行 soft delete，写入 `deleted_at`，保留审计记录。

#### Scenario: 用户在 UI 删除区间

- **WHEN** 用户在标注工作台删除一条区间
- **THEN** 系统 MUST 将该 segment 的 `deleted_at` 置为当前时间，且该 segment MUST NOT 出现在默认查询结果中

#### Scenario: 软删除数据仍可审计

- **WHEN** 审计方查询某 revision 的历史变更
- **THEN** 系统 MUST 能返回已 soft delete 的 segment 及其 `deleted_at`

### Requirement: 区间 CRUD API

系统 SHALL 提供人工标注的创建、读取、更新、删除 API，归属路径为 session video → annotation set → revision → segments。

#### Scenario: 为 session video 创建 annotation set

- **WHEN** 调用 `POST /api/session-videos/{session_video_id}/manual-annotation-sets` 并提供 `phase_profile_id`
- **THEN** 系统 MUST 创建 set 并同时创建首个 `draft` revision，返回 set 与 revision

#### Scenario: 列出某 session video 的 set

- **WHEN** 调用 `GET /api/session-videos/{session_video_id}/manual-annotation-sets`
- **THEN** 系统 MUST 返回该视频下所有 set 的摘要（id、`phase_profile_id`、当前 head revision、状态、`segment_count`）

#### Scenario: 读取某 revision 的 segments

- **WHEN** 调用 `GET /api/manual-annotation-revisions/{revision_id}/segments`
- **THEN** 系统 MUST 返回该 revision 下全部未删除 segment，按 `side`、`start_time_sec` 排序

#### Scenario: 创建区间

- **WHEN** 调用 `POST /api/manual-annotation-revisions/{revision_id}/segments` 并含 `cycle_id`、`side`、`phase_code`、起止秒
- **THEN** 系统 MUST 校验通过 L1 结构校验后创建 segment

#### Scenario: 编辑 draft revision 的区间

- **WHEN** 调用 `PATCH /api/manual-phase-segments/{segment_id}` 且所属 revision 为 `draft`
- **THEN** 系统 MUST 更新 segment 并重算 revision 的 `content_hash`

#### Scenario: 编辑非 draft revision 的区间被拒绝

- **WHEN** 调用 `PATCH /api/manual-phase-segments/{segment_id}` 且所属 revision 状态为 `reviewed` 或 `frozen`
- **THEN** 系统 MUST 返回 409 并提示该 revision 不可修改

### Requirement: 保留 ML 导出所需字段与未来 export contract

系统 SHALL 在 set / revision / segment 上保留 ML 数据集导出所需字段，并定义未来 export contract 的数据要求。本能力不实现导出服务。

#### Scenario: 导出所需字段齐备

- **WHEN** 检查 set / revision / segment 的字段集合
- **THEN** MUST 至少包含 `video_checksum_sha256`、`annotation_set_id`、`revision_id`、`revision_no`、`content_hash`、`phase_profile_id`、`phase_profile_version`、`phase_profile_hash`、`cycle_id`、`side`、`phase_code`、`start_time_sec`、`end_time_sec`、frame 快照与 `frame_basis`、标注者与复核者 provenance、`review_status`、`confidence`

#### Scenario: 环节定义与内容均可哈希校验

- **WHEN** 创建或发布 revision
- **THEN** 系统 MUST 计算并存储 `phase_profile_hash`（环节定义哈希）与 `content_hash`（区间内容哈希）

#### Scenario: 未来数据集拆分的单元与防泄漏组被区分记录

- **WHEN** 定义未来 export contract
- **THEN** contract MUST 区分两个层级：`sample unit = cycle_id`（样本构造单元，同一 cycle 的多个 phase 不得拆散）与 `split leakage group = video_checksum_sha256`（同一 source video 的所有 cycles 必须落在同一 train / val / test split）

#### Scenario: 同一视频的周期不跨 split

- **WHEN** 未来执行数据集拆分
- **THEN** 同一 `video_checksum_sha256` 下的全部 cycle MUST 被分配到同一 split，MUST NOT 出现相邻周期分别落入训练集与测试集

#### Scenario: 未实现的导出能力有明确边界

- **WHEN** 调用方请求 dataset export 服务
- **THEN** 本能力 MUST NOT 提供该服务；`dataset_snapshot`、split、inter-rater agreement、adjudication workflow 仅作为未来接口记录，不在本能力实现

### Requirement: 可复现快照落在 revision 而非 set

系统 SHALL 将视频与时间基准的可复现快照存放在 revision 上，set 只保留谱系与归属信息。

#### Scenario: revision 创建时快照视频与时间基准

- **WHEN** 系统创建 revision
- **THEN** revision MUST 记录 `video_checksum_sha256`、`video_fps_snapshot`、`video_duration_snapshot`、`frame_basis`

#### Scenario: revision 创建时快照 profile 版本

- **WHEN** 系统创建 revision
- **THEN** revision MUST 记录 `phase_profile_id`、`phase_profile_version`、`phase_profile_hash`

#### Scenario: 后续 profile 升级不改写历史 revision

- **WHEN** profile 版本从 1.0.0 升级到 1.1.0，且 set 的默认 profile 随之更新
- **THEN** 已有 revision 记录的 `phase_profile_version` 与 `phase_profile_hash` MUST 保持创建时的值

#### Scenario: set 不承载快照字段

- **WHEN** 检查 `manual_annotation_sets` 表结构
- **THEN** 该表 MUST NOT 包含 `video_checksum_sha256`、`frame_basis`、`phase_profile_hash` 等快照字段

### Requirement: content_hash 不作唯一约束

系统 SHALL 将 `content_hash` 用于证明内容身份、检测变化与保证可复现，MUST NOT 对其建立唯一约束。

#### Scenario: fork 出的 revision 与源内容相同时可保存

- **WHEN** 用户从 revision 3 fork 出 revision 4 且未做任何修改
- **THEN** 系统 MUST 成功保存 revision 4，MUST NOT 因 `content_hash` 与 revision 3 相同而拒绝

#### Scenario: 无 set 级 content_hash 唯一约束

- **WHEN** 检查 `manual_annotation_revisions` 的约束定义
- **THEN** MUST 存在 `UNIQUE(set_id, revision_no)`，且 MUST NOT 存在 `UNIQUE(set_id, content_hash)`

#### Scenario: hash 在离开 draft 后固定

- **WHEN** revision 从 `draft` 进入 `in_review` 或更高状态
- **THEN** `content_hash` MUST 固定，后续任何写操作 MUST 被拒绝而非重算 hash

#### Scenario: draft 阶段 hash 随编辑变化

- **WHEN** draft revision 的 segment 发生增删改
- **THEN** `content_hash` MUST 重算

#### Scenario: 相同内容得到相同 hash

- **WHEN** 对同一组 segment 语义内容两次计算 `content_hash`
- **THEN** 两次结果 MUST 完全相同；系统 MUST 按固定规则序列化：字段按 key 字典序排序、排除 `id` / `created_at` / `updated_at` / `deleted_at` / `revision_id` / `cycle_index` 等非语义字段、浮点时间按固定小数位、已 soft delete 的 segment 不参与

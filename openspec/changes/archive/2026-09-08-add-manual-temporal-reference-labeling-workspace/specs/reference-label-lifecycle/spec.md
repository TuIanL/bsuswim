## ADDED Requirements

### Requirement: revision 生命周期状态机

系统 SHALL 为 annotation revision 提供 `draft` → `in_review` → `reviewed` → `frozen` 的状态流转，并允许 `rejected` 回退。set 表示逻辑标注谱系，revision 表示不可变内容版本。

#### Scenario: 新建 revision 为 draft

- **WHEN** 系统创建 annotation set
- **THEN** 系统 MUST 同时创建首个 revision，状态为 `draft`

#### Scenario: draft 提交复核

- **WHEN** 用户将 `draft` revision 提交复核
- **THEN** 系统 MUST 将状态置为 `in_review`，并 MUST 先通过 L1 与 L2 校验

#### Scenario: 复核通过

- **WHEN** 复核者通过 `in_review` revision
- **THEN** 系统 MUST 将状态置为 `reviewed`，并写入 `reviewed_by` 与复核时间

#### Scenario: 复核打回

- **WHEN** 复核者打回 `in_review` revision
- **THEN** 系统 MUST 将状态置为 `rejected`，且 MUST NOT 直接把内容改回 `draft`；继续修改 MUST 通过 fork 完成

#### Scenario: reviewed 冻结为 frozen

- **WHEN** 用户将 `reviewed` revision 冻结
- **THEN** 系统 MUST 将状态置为 `frozen`，并 MUST 通过 L3 校验

### Requirement: 已发布 revision 不可修改，修改通过 fork 完成

系统 SHALL 保证 revision 一旦离开 `draft` 状态即内容不可修改（A revision becomes immutable once it leaves the draft state）。`in_review` 即锁内容，而不是等到 `reviewed`。后续修改 MUST 通过从该 revision fork 出新的 `draft` revision 完成，且新 revision 仍属同一 annotation set。

#### Scenario: fork 生成新 draft revision

- **WHEN** 用户对一个 `frozen` revision 发起继续编辑
- **THEN** 系统 MUST 在同一 set 下创建新的 `draft` revision，复制源 revision 的全部未删除 segment，并记录 `forked_from_revision_id`

#### Scenario: fork 重置复核状态

- **WHEN** 系统执行 fork
- **THEN** 新 revision MUST 重置 `review_status` 与 `reviewed_by`，MUST 保留 `note` 内容

#### Scenario: fork 保留 cycle_id

- **WHEN** 系统执行 fork
- **THEN** 相同周期的 segment MUST 沿用源 revision 的 `cycle_id`，以支持跨 revision 的周期级 diff

#### Scenario: 小修改不新建 set

- **WHEN** 用户对已发布 revision 做增量修改
- **THEN** 系统 MUST 保持同一 `annotation_set_id`，MUST NOT 创建新的 annotation set

#### Scenario: 不同标注者建立独立 set

- **WHEN** 第二位标注者对同一视频进行独立标注
- **THEN** 系统 MUST 创建新的 annotation set，MUST NOT 复用他人 set 的 revision

#### Scenario: 修改已发布 revision 被拒绝

- **WHEN** 调用方尝试修改 `reviewed` 或 `frozen` revision 下的 segment
- **THEN** 系统 MUST 返回 409，且 MUST NOT 修改任何数据

#### Scenario: in_review 阶段即锁定内容

- **WHEN** revision 处于 `in_review` 且调用方尝试修改其 segment
- **THEN** 系统 MUST 返回 409，MUST NOT 允许提交复核后再修改

#### Scenario: draft 仍可编辑

- **WHEN** revision 处于 `draft`
- **THEN** 系统 MUST 允许 segment 的增删改，并 MUST 重算 `content_hash` 与递增 `edit_version`

#### Scenario: 被打回后通过 fork 继续修改

- **WHEN** revision 状态为 `rejected`
- **THEN** 系统 MUST 拒绝直接修改，继续修改 MUST 通过 fork 出新 draft revision 完成

### Requirement: L1 结构校验在任何状态下执行

系统 SHALL 对任何状态下的 segment 执行 L1 结构校验：区间边界有效、落在视频时长内、`side` 取值合法、`phase_code` 属于当前 profile、`cycle_id` 非空。

#### Scenario: 起止时间非法被拒绝

- **WHEN** 创建 `start_time_sec >= end_time_sec` 的区间
- **THEN** 系统 MUST 拒绝创建并返回结构化错误

#### Scenario: 区间超出视频时长被拒绝

- **WHEN** 创建 `end_time_sec` 大于视频 `duration_sec` 的区间
- **THEN** 系统 MUST 拒绝创建

#### Scenario: phase_code 不属于 profile 被拒绝

- **WHEN** 创建 `phase_code = "kick"` 而当前 profile 为 `freestyle_arm_phase_v1`
- **THEN** 系统 MUST 拒绝创建，MUST NOT 静默接受未知 code

#### Scenario: draft 允许结构合法的重叠与空隙

- **WHEN** draft revision 中存在同侧重叠区间或空隙
- **THEN** 系统 MUST 允许保存，MUST NOT 阻止

### Requirement: L2 周期完整性校验为 reviewed 准入条件

系统 SHALL 在 revision 进入 `reviewed` 前执行 L2 校验：同 `(side, cycle_id)` 内四阶段齐全、无重叠、相邻阶段空隙不超过阈值，且 `side` 已收敛为 `left` / `right`。

#### Scenario: 四阶段齐全且无缝通过 L2

- **WHEN** 右侧某 cycle 内 `entry` / `catch` / `push` / `recovery` 四段齐全、互不重叠、相邻空隙均 ≤ 50ms
- **THEN** L2 校验 MUST 通过

#### Scenario: 同侧同周期重叠阻止 reviewed

- **WHEN** 同一 `(side, cycle_id)` 内 `catch` 与 `push` 区间重叠
- **THEN** 系统 MUST 阻止进入 `reviewed` 并给出 conflict 详情

#### Scenario: 缺失阶段阻止 reviewed

- **WHEN** 某 cycle 内缺少 `recovery` 段
- **THEN** 系统 MUST 阻止进入 `reviewed` 并提示缺失阶段

#### Scenario: 左右臂区间重叠不被视为错误

- **WHEN** 左臂 `catch` 与右臂 `push` 在全局时间轴上重叠
- **THEN** 系统 MUST 视为正常，MUST NOT 产生任何校验错误

#### Scenario: 不同 cycle 之间的区间重叠不被视为错误

- **WHEN** 同侧第 1 周期的 `recovery` 与第 2 周期的 `entry` 在全局时间轴上重叠
- **THEN** 系统 MUST 视为正常，MUST NOT 产生任何校验错误

#### Scenario: side 未收敛阻止 reviewed

- **WHEN** revision 中存在 `side` 为 `both` 或 `unknown` 的 segment
- **THEN** 系统 MUST 阻止进入 `reviewed` 并提示收敛为 `left` 或 `right`

### Requirement: L3 profile 严格校验为 frozen 准入条件

系统 SHALL 在 revision 进入 `frozen` 前执行 L3 校验：完整 cycle 数量达标、cycle 边界落在 `hand_entry` 上、与同源点事件派生结果交叉一致。

#### Scenario: 完整 cycle 数不足阻止 frozen

- **WHEN** revision 中完整 cycle 数少于 profile 声明的 `minimum_complete_cycles`
- **THEN** 系统 MUST 阻止进入 `frozen`

#### Scenario: cycle 边界未落在 hand_entry 阻止 frozen

- **WHEN** 某 cycle 的 `entry` 起点与同源 `hand_entry` 事件时间偏差超过阈值
- **THEN** 系统 MUST 阻止进入 `frozen` 并给出偏差详情

#### Scenario: 无同源点事件时跳过交叉校验

- **WHEN** 该 session video 不存在任何 imported events
- **THEN** 系统 MUST 跳过交叉一致性校验，MUST NOT 因此阻止 frozen

### Requirement: 数据库层不强制无重叠约束

系统 SHALL 不在数据库层建立区间排他约束（如 PostgreSQL `EXCLUDE USING gist`），全部重叠校验在应用层按状态分级执行。

#### Scenario: 数据库无排他约束

- **WHEN** 检查 `manual_phase_segments` 表定义
- **THEN** 该表 MUST NOT 包含基于时间范围的排他约束

#### Scenario: draft 可保存重叠区间

- **WHEN** 用户在 draft revision 中保存两条同侧重叠区间
- **THEN** 写入 MUST 成功，不被数据库拒绝

# freestyle-arm-phase-profile Specification

## Purpose
自由泳单臂周期的四阶段环节定义 profile，声明 id、version、cycle_definition 与 phases。

## Requirements
### Requirement: freestyle_arm_phase_v1 profile 定义

系统 SHALL 提供 `freestyle_arm_phase_v1` 环节定义 profile，声明自由泳单臂周期的四个阶段。profile MUST 包含 `id`、`version`、`cycle_definition` 与 `phases` 四个部分。

#### Scenario: profile 声明四阶段

- **WHEN** 加载 `freestyle_arm_phase_v1`
- **THEN** `phases` MUST 按周期顺序包含 `entry`、`catch`、`push`、`recovery` 四个 code

#### Scenario: 中文名称仅作展示

- **WHEN** 检查 profile 的 phase 定义
- **THEN** 每个 phase MUST 含稳定 `code` 与展示用 `display`；`display` 分别为「入水」「抱水」「推水」「移臂」，API 与存储 MUST 一律使用 `code`

#### Scenario: profile 声明必选边界

- **WHEN** 加载 `freestyle_arm_phase_v1`
- **THEN** `required_boundaries` MUST 为 `hand_entry`、`catch_start`、`pull_end`、`hand_exit`

#### Scenario: profile 预留未来拆分边界

- **WHEN** 加载 `freestyle_arm_phase_v1`
- **THEN** `optional_boundaries` MUST 包含 `catch_end`，用于未来拆分 catch 与 pull

### Requirement: cycle 定义沿用既有契约

系统 SHALL 将自由泳单臂 cycle 定义为「同侧 `hand_entry` → 下一次同侧 `hand_entry`」，与既有 `side_technical_v1.yaml` 的 `partition_by: side` + `cycle_boundary: hand_entry` 保持一致，不另发明 cycle 定义。

#### Scenario: cycle 边界为同侧 hand_entry

- **WHEN** 系统为右臂划分 cycle
- **THEN** 每个 cycle MUST 以一次右侧 `hand_entry` 开始，以下一次右侧 `hand_entry` 结束

#### Scenario: 左右臂周期互不干扰

- **WHEN** 视频中左臂与右臂交替划水
- **THEN** 系统 MUST 按 side 分别划分 cycle，MUST NOT 把左臂 `hand_entry` 当作右臂 cycle 的边界

### Requirement: 四阶段与边界事件的映射

系统 SHALL 按以下映射在 phase 区间与边界事件之间转换：

| phase_code | 展示名 | 起始边界 | 结束边界 |
|---|---|---|---|
| `entry` | 入水 | `hand_entry` | `catch_start` |
| `catch` | 抱水 | `catch_start` | `pull_end` |
| `push` | 推水 | `pull_end` | `hand_exit` |
| `recovery` | 移臂 | `hand_exit` | 下一周期 `hand_entry` |

#### Scenario: 完整区间派生四个边界事件

- **WHEN** 某 cycle 四个 phase 区间完整
- **THEN** 系统 MUST 派生出 `hand_entry`、`catch_start`、`pull_end`、`hand_exit` 四个边界事件

#### Scenario: recovery 结束边界为下一周期 hand_entry

- **WHEN** 系统推导 `recovery` 区间的结束时间
- **THEN** MUST 使用同侧下一 cycle 的 `hand_entry` 时间

#### Scenario: 最后一个未闭合周期不派生完整边界

- **WHEN** 某 cycle 的 `recovery` 之后没有下一次同侧 `hand_entry`
- **THEN** 系统 MUST 将该 cycle 标记为 incomplete，MUST NOT 虚构 `hand_entry` 时间

### Requirement: 边界缺失时返回 partial derivation，不得猜测

系统 SHALL 在既有 imported events 缺少 `hand_exit` 时返回 partial derivation，并明确标记不可用阶段，MUST NOT 推断或插值。

#### Scenario: 只有三个边界时标记 recovery 不可用

- **WHEN** 同源事件只有 `hand_entry` / `catch_start` / `pull_end`，缺少 `hand_exit`
- **THEN** 系统 MUST 生成 `entry`、`catch` 两段，`push` 与 `recovery` MUST 标记为 unavailable，并给出 `missing_hand_exit` 提示

#### Scenario: 只有三个边界时不得切分 push 与 recovery

- **WHEN** 缺少 `hand_exit`
- **THEN** 系统 MUST NOT 把 `pull_end` 之后的整段归为 `push` 或 `recovery`，MUST NOT 用时长比例猜测分界点

#### Scenario: 四边界齐全时生成完整四阶段

- **WHEN** 同源事件包含 `hand_entry` / `catch_start` / `pull_end` / `hand_exit`
- **THEN** 系统 MUST 生成完整四阶段区间

### Requirement: 边界必须具备人工操作定义

系统 SHALL 在 profile 中为每个边界提供 `boundary_definitions`，至少含 `display`、`operational_definition`、`reference_joint`、`annotation_guidance`，使不同标注员依据同一判据标注。缺少人工操作定义时，结构化数据只会成为"结构化的不一致标签"。

#### Scenario: hand_entry 定义明确判定瞬间

- **WHEN** 标注员判断入水瞬间
- **THEN** profile MUST 明确取"指尖首次接触水面 / 手掌过水面 / 腕关节过水面"中的哪一个，并 MUST 给出 `reference_joint`

#### Scenario: catch_start 定义明确判定依据

- **WHEN** 标注员判断抱水开始
- **THEN** profile MUST 明确取"前臂开始改变方向 / 肘屈曲超过阈值 / 建立有效迎水面"中的哪一个；若采用阈值判据 MUST 给出具体数值

#### Scenario: pull_end 定义明确与推水的分界

- **WHEN** 标注员判断拉水结束与推水开始的分界
- **THEN** profile MUST 给出可执行的判据，MUST NOT 只写"拉水结束"

#### Scenario: hand_exit 定义明确离水瞬间

- **WHEN** 标注员判断出水瞬间
- **THEN** profile MUST 明确取"手掌离水 / 腕关节离水 / 指尖完全离水"中的哪一个

#### Scenario: 缺少操作定义的 profile 被拒绝加载

- **WHEN** 加载缺少 `boundary_definitions` 或某项缺 `operational_definition` 的 profile
- **THEN** 系统 MUST 拒绝加载，MUST NOT 静默使用空定义

#### Scenario: 前端可展示标注判据

- **WHEN** 标注员在工作台选择环节标签
- **THEN** 系统 MUST 能展示该环节边界的 `annotation_guidance`

### Requirement: profile 版本化与可校验

系统 SHALL 对 profile 做版本管理，并在创建与发布 revision 时记录 `phase_profile_id`、`phase_profile_version` 与 `phase_profile_hash`。

#### Scenario: 创建 set 记录 profile 版本

- **WHEN** 用户创建 annotation set 并指定 `freestyle_arm_phase_v1`
- **THEN** 系统 MUST 记录 `phase_profile_id`、`phase_profile_version`，并计算 `phase_profile_hash`

#### Scenario: profile 内容变更产生新 hash

- **WHEN** `freestyle_arm_phase_v1` 的 phase 定义发生变化且版本升级
- **THEN** `phase_profile_hash` MUST 变化，已有 revision 记录的旧 hash MUST 保持不变

#### Scenario: 未知 profile 被拒绝

- **WHEN** 创建 set 时提供未定义的 `phase_profile_id`
- **THEN** 系统 MUST 返回 422，MUST NOT 回退到默认 profile


## Context

### 现状

平台当前的动作阶段信息全部是**点事件**语义。`AnnotationEvent`（`backend/app/schemas/normalized_annotation.py:37`）只有 `name / label / frame / time_sec / side / confidence / labeled_by`，没有任何表示"持续"的字段。`ManualTag`（同文件 `:74`）虽然有 `frame_range`，但语义是 `severity` 问题标记，不是技术环节区间。

存在一个已经声明但未落地的周期契约。`backend/app/services/annotation_quality/profiles/side_technical_v1.yaml:62`：

```yaml
event_sequences:
  freestyle_arm_cycle:
    partition_by: side
    cycle_boundary: hand_entry
    order: [hand_entry, catch_start, pull_end, hand_exit]
    optional: [recovery_peak]
```

这 4 个边界点理论上切出 4 段：入水 / 抱水 / 推水 / 移臂。但 `hand_exit` 在全仓库只出现 3 处（profile yaml `:70`、`temporal_checks.py:91`、归档 `design.md:265`）——没有 parser 产出它，没有质量模块的 `required_events` 要求它，没有测试 fixture 用它。真实数据最多 3 个边界，只能切出 3 段。

时间源方面存在规范与实现的脱节。`openspec/specs/annotation-time-mapping/spec.md` 声明「metrics 层 SHALL 以 `KeypointFrame.timestamp_sec` 为唯一权威时间源」，但 `backend/app/services/metrics/` 全目录没有任何一处读取 `timestamp_sec`（只在 `parsers/cvat_normalizer.py:76` 写入，零消费方）。实际权威是 `(frame, fps) → time_sec`。

归属方面，`normalized-annotation-schema` 明确 `session_video_id` 是 canonical reference，而前端 `/workspace/:taskId` 绑定的是 analysis task，两者不一致。

### 约束

- 本次改动不得破坏既有 imported-event 流水线与已产出的 metrics
- 既有 metrics 层的时间系统不在本次改造范围内
- 人工标注不能与现有点事件形成两套可独立编辑的真值

### 可复用的既有 precedent

| precedent | 位置 | 本次如何复用 |
|---|---|---|
| revision 三态检测 | `metrics_service.py:157 compute_revision_status` | resolver 的 `current / stale / unknown` 语义 |
| signature 解析 | `kinematic_artifacts/resolver.py:60 resolve_current_artifact_set` | resolver 的函数形状与返回结构 |
| set + items 两层 + provenance | `models/kinematic_review_finding.py:24-64` | set / revision / segment 三层与 provenance 字段清单 |
| 视频版本锚点 | `models/video.py:27 VideoFile.checksum_sha256`（NOT NULL） | 直接复用，不新增字段 |
| 快照落点 | `models/analysis.py:29 AnalysisTask.request_payload` | provenance 镜像位置 |

## Goals / Non-Goals

**Goals:**

- 建立可长期积累的人工时序参考标注资产层，而不是一次性的工作台 CRUD
- 让标注拥有谱系（set）、不可变版本（revision）与可审计来源（provenance）
- 统一自由泳四阶段定义，使人工区间与既有边界事件共享同一套动作定义
- 让下游分析显式消费某个 revision，杜绝"按 session 猜最新"导致的分析结果静默漂移
- 为未来 ML 数据集导出预留完整的字段与契约

**Non-Goals:**

- 不训练任何机器学习模型
- 不实现完整 dataset export 服务，只定义字段与未来接口
- 不全面重构既有 metrics 的时间系统
- 不强制迁移所有历史 imported events
- 不修复既有 `hand_exit` / `recovery_peak` / `cycle completeness` 遗留问题
- 不做自动动作阶段识别
- 不实现多人 adjudication 工作流与 inter-rater agreement 计算

## Decisions

### D1：revision 是一等实体，segment 通过 `revision_id` FK 引用

```
manual_annotation_sets (1) ──< manual_annotation_revisions (1) ──< manual_phase_segments
        谱系                        版本（离开 draft 后不可变）          区间行
```

`manual_phase_segments.revision_id` → `manual_annotation_revisions.id`（FK，NOT NULL）。
`revision_no` 由 revision 表在 set 内维护，segment 可冗余存储用于展示，但**不承担引用完整性**。

**revision 可变性语义**（重要，避免与 CRUD 自相矛盾）：

> A revision becomes immutable once it leaves the draft state.

| 状态 | 内容可变 | `content_hash` |
|---|---|---|
| `draft` | 可变（CRUD 与 fork 均在此态进行） | 随编辑变化 |
| `in_review` | **不可变** | 固定 |
| `reviewed` | 不可变 | 固定 |
| `frozen` | 不可变 | 固定 |
| `rejected` | 不可变 | 固定（继续修改须 fork） |

`in_review` 即锁内容，而不是等到 `reviewed`——否则提交复核后标注者仍可悄悄修改，复核者看到的内容不再稳定。

- **备选 A**：segment 存 `(set_id, revision_no)` 组合键
- **备选 B（采纳）**：segment 存 `revision_id` FK
- **理由**：组合键无法阻止 `revision_no` 被误改导致整批 segment 指向错误版本；FK 让数据库直接保证引用完整性，且 `AnalysisTask → reference_annotation_revision_id → segments` 可一次 join 拿到完整冻结切片，无需时间旅行查询。

### D2：set 表示谱系，修改通过 fork 新 draft revision 完成，不因小改新建 set

- revision 一旦离开 `draft` 状态即不可修改（`in_review` / `reviewed` / `frozen` / `rejected` 均锁内容，`in_review` 即锁而非等到 `reviewed`）
- 需要继续修改 → 从该 revision fork 出新的 `draft` revision，仍属同一 set
- 只有以下情况才建立新 set：不同标注者的独立标注、不同 `phase_profile_id`、或真正独立的 reference set

- **备选 A**：frozen 后任何修改都新建 set
- **备选 B（采纳）**：frozen 后 fork 新 revision，保留同一 set
- **理由**：备选 A 会切断 lineage，无法回答"这份标注是从哪一版演化来的"，而这正是训练数据溯源的关键信息。

### D2b：`content_hash` 不作唯一约束，且必须定义稳定时机

**MUST NOT** 建立 `UNIQUE(set_id, content_hash)`。fork 出来的 revision 在刚创建时内容与源 revision 完全相同，`content_hash` 必然相同，会立刻违反唯一约束并让 fork 功能无法使用。

重复内容是合法状态，例如：

```
revision 3（reviewed） → fork → revision 4（draft）→ 标注员最终认为无需修改
→ revision 4 与 revision 3 内容相同
```

这不是数据错误。`content_hash` 的用途是**证明内容身份、检测变化、保证分析与 ML 导出可复现**，而不是强制"同一 set 不能出现两份相同内容"。改为普通 index。

**hash 稳定时机**：

| 状态 | `content_hash` |
|---|---|
| `draft` | 随每次 segment 增删改重算 |
| `in_review` / `reviewed` / `frozen` / `rejected` | 固定，不再变化 |

**canonical JSON 规则**（否则同样内容会得到不同 hash）：
- 字段按 key 字典序排序
- 排除 `id`、`created_at`、`updated_at`、`deleted_at`、`revision_id`、`cycle_index` 等非语义字段
- 参与哈希的语义字段：`cycle_id`、`side`、`phase_code`、`start_time_sec`、`end_time_sec`、`confidence`、`note`
- 浮点时间按固定小数位序列化，避免 `1.0` 与 `1.000` 产生不同 hash
- 已 soft delete 的 segment 不参与哈希

### D3：时间为 canonical 的是 `start_time_sec` / `end_time_sec`，frame 是派生快照

- canonical：`start_time_sec` / `end_time_sec`（`Numeric(12, 4)`）
- 派生：`start_frame` / `end_frame`，必须同时记录 `frame_basis = {fps, fps_source, mapping_mode, mapping_verified}`
- `frame_basis` 缺失时 frame 快照 MUST 为 NULL，不允许只存 frame 而无基准

- **备选 A**：跟随既有 metrics 实现，以 `(frame, fps)` 为 canonical
- **备选 B（采纳）**：以秒为 canonical，frame 降级为带基准的快照
- **理由**：既有 metrics 实现是历史包袱——规范本就声明应以时间为权威，只是从未落地。新体系若跟着倒退，未来迁移成本更高。第一版 adapter 临时执行 `time_sec → frame` 转换以兼容 `rhythm_metrics`，但这是 **compatibility adapter**，不反过来定义新数据模型。

### D3b：可复现快照下沉到 revision，set 只保留谱系信息

真正被分析任务引用、真正需要可复现的是 **revision**，不是 set。若把快照放在 set 上，一旦后续修复 fps / frame mapping / profile 版本，revision 1 当时实际使用的基准就永久丢失。

| 归属 | 字段 |
|---|---|
| `ManualAnnotationSet`（谱系与归属） | `session_video_id`、`phase_profile_id`（当前默认 profile，仅作新建 revision 时的默认值）、`head_revision_id`、`created_by`、`created_at`、`updated_at`、`deleted_at` |
| `ManualAnnotationRevision`（可复现快照） | `set_id`、`revision_no`、`forked_from_revision_id`、`video_checksum_sha256`、`video_fps_snapshot`、`video_duration_snapshot`、`frame_basis`、`phase_profile_id`、`phase_profile_version`、`phase_profile_hash`、`content_hash`、`status`、`edit_version`、provenance 字段 |

注意：`source_of_truth` **不是** set 或 revision 的存储字段。它是按 `AnalysisTask` 显式引用解析出来的**结果**（见 D6），记录在分析产物上，避免又出现一处可漂移的"当前权威"状态。

- **备选 A**：快照放 set，revision 只存内容
- **备选 B（采纳）**：快照放 revision
- **理由**：与「`AnalysisTask` 引用 revision」的哲学一致——revision 才表示"当时究竟基于哪条视频、哪个 profile、哪个时间映射形成的这份标注"。set 表示谱系，revision 表示事实。

### D3c：`side` 在正式数据中只允许 left / right

`both` / `unknown` 允许 `draft` 临时使用（标注员尚未判明左右臂时），但 **MUST NOT** 进入 `reviewed` / `frozen` 数据。否则 `partition_by: side` 的 cycle 定义会变得含糊，同侧周期边界无法确定。L2 校验 MUST 拦截。

### D4：cycle 定义沿用既有契约，`cycle_id` 稳定，`side` 显式

- cycle = 同侧 `hand_entry` → 下一次同侧 `hand_entry`（与 `side_technical_v1.yaml` 的 `partition_by: side` + `cycle_boundary: hand_entry` 完全一致，不另发明）
- `cycle_id`：UUID v4，作为**跨 revision 稳定的逻辑标识**（stable logical identifier across revisions）
- `cycle_index`：派生展示序号，可为空，允许乱序标注
- `side`：`left | right | both | unknown`，必须显式（正式数据收敛见 D3c）

**fork 时 `cycle_id` 必须继承，不是重新生成**：

| 操作 | `cycle_id` 行为 |
|---|---|
| fork 已有 cycle | **保留原 `cycle_id`** |
| 用户新增 cycle | 生成新的 UUID v4 |
| 用户删除 cycle | 后续 revision 中不存在，但历史 revision 保留 |

这样才能回答"revision 2 的 cycle X 与 revision 5 的 cycle X 之间发生了什么修改"，是 revision diff、标注一致性分析与 ML provenance 的基础。

`cycle_id` **MUST NOT** 作为全局唯一的数据库键。可选的完整性约束是 `UNIQUE(revision_id, cycle_id, side, phase_code)`（同一 revision 内同一侧的同一阶段不重复），而不是 `UNIQUE(cycle_id)`。

- **备选 A**：只存 `cycle_index`，下游按时间排序推导
- **备选 B（采纳）**：存稳定 `cycle_id`，`cycle_index` 仅作展示
- **理由**：备选 A 在人工删除或插入中间一段后，后续所有 cycle 的 index 会整体漂移，已快照的分析结果与标注无法对齐。
- **补充**：`cycle_id` 用 UUID v4 是合适的，但其目的是跨 revision 稳定，不是"避免 fork 碰撞"——fork 恰恰需要它保持不变。

### D5：不重构旧 event pipeline，采用兼容策略 + partial derivation

新 `freestyle_arm_phase_v1` 要求完整四阶段，本身即可派生 `hand_exit`。但对既有流水线：

- `segments → events`：人工标注完整时，adapter 可稳定派生 `hand_entry / catch_start / pull_end / hand_exit` 供 `rhythm_metrics` 使用
- `events → segments`：仅当四个边界齐全时才能生成完整四阶段；若只有 `hand_entry / catch_start / pull_end`，MUST 返回 partial derivation 并明确标记 `recovery_unavailable` / `missing_hand_exit`，**不得猜测**

- **备选 A**：本 Change 同步修复所有 parser 与 quality profile，把 `hand_exit` 提为必选
- **备选 B（采纳）**：新 profile 要求四阶段，旧体系问题记录为 follow-up
- **理由**：备选 A 会把"人工标注工作台"的范围膨胀成"全平台事件体系重构"，且需要回溯迁移历史 imported annotations，风险与工期都不可控。

已知遗留（记录在 proposal，另拆 follow-up Change）：
1. `hand_exit` 在旧 pipeline 无产出方
2. `temporal_checks.py:91` 用 `"recovery"`，profile `optional` 用 `recovery_peak`，命名不一致使 optional 失效
3. `coverage_checks.py:177 check_cycle_completeness` 未按 side 分区，双侧视频重复计数

### D6：`source_of_truth` 枚举裁决，单向派生，永不回写

```python
class SourceOfTruth(str, Enum):
    MANUAL_SEGMENTS = "manual_segments"
    IMPORTED_EVENTS = "imported_events"
```

**裁决规则完全由 `AnalysisTask` 的显式引用驱动，不做"发现数据库里存在人工标注就自动切换"的推断**：

```
AnalysisTask.reference_annotation_revision_id != NULL
  → source_of_truth = manual_segments
  → 严格消费该 revision 一个版本

AnalysisTask.reference_annotation_revision_id == NULL
  → source_of_truth = imported_events
  → 保持 legacy 行为
```

当同一 session video 存在多个 `reviewed` / `frozen` revision 时，系统 **MUST NOT** 自行挑选其中一个——没有显式引用就没有答案。

**显式指定但不可用时 MUST NOT 回退**：

| resolver 结果 | 行为 |
|---|---|
| `ready` | 正常消费 |
| `not_found` | 返回 `reference_input_invalid`，阻断相关分析 |
| `revision_mismatch` | 返回 `reference_input_invalid`，阻断 |
| `checksum_mismatch` | 返回 `reference_input_invalid`，阻断 |
| `profile_mismatch` | 返回 `reference_input_invalid`，阻断 |

若此时回退到 imported events，就退化成"本来指定人工 revision A，视频换了以后系统偷偷跑 imported events B"，恰恰是本 Change 要消除的**分析输入静默漂移**。

`draft` revision **MUST NOT** 被 `AnalysisTask` 引用（见 D6b）。两边冲突时生成 conflict / warning，**不得自动双向写回**。

始终维持 `one authoritative input → derived representation`，而不是两套数据相互同步。

### D6b：AnalysisTask 只能引用非 draft revision

分析任务引用的 revision 状态 MUST 属于 `in_review` / `reviewed` / `frozen`。引用 `draft` 会在任务运行期间被修改，破坏"输入不可变"的前提。

- **备选 A**：`is_authoritative: bool`
- **备选 B（采纳）**：`source_of_truth` 枚举 + 显式 revision 引用
- **理由**：bool 无法表达"人工 draft 存在但不应生效"这一第三态，也无法表达冲突时该听谁的。

### D7：重叠约束作用域为 `(side, cycle_id)`，DB 层不强制

- `draft` 状态：允许重叠与空隙
- `reviewed` 准入：同 `(side, cycle_id)` 内四阶段齐全、无重叠、相邻空隙 ≤ 阈值
- `frozen` 准入：完整 cycle 数达标、cycle 边界落在 `hand_entry` 上、与点事件派生结果交叉一致

左右臂在全局时间轴上重叠是自由泳的正常形态，**MUST NOT** 被当作错误。

- **备选 A**：PostgreSQL `EXCLUDE USING gist (side WITH =, tsrange(...) WITH &&)`
- **备选 B（采纳）**：DB 不建约束，应用层按状态分级校验
- **理由**：标注过程天然存在"先粗标后细化"的中间态，DB 硬约束会让 draft 无法保存；且跨 side 的重叠是合法的，约束表达式会非常复杂且难以演进。

### D8：`AnalysisTask` 用独立 FK，并在 `request_payload` 镜像

```python
# models/analysis.py
reference_annotation_revision_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("manual_annotation_revisions.id", ondelete="SET NULL"), nullable=True, index=True
)
```

同时镜像到 `request_payload.analysis_input`：

```json
{
  "reference_annotation_set_id": 123,
  "reference_annotation_revision_id": 456,
  "revision_no": 4,
  "content_hash": "sha256:...",
  "video_checksum_sha256": "...",
  "phase_profile_id": "freestyle_arm_phase_v1",
  "phase_profile_version": "1.0.0"
}
```

- **备选 A**：只加 `reference_annotation_set_id` + `reference_revision_no` 两个弱关联字段
- **备选 B（采纳）**：`reference_annotation_revision_id` 独立 FK + `request_payload` 镜像
- **理由**：revision 已是不可变实体，FK 直接提供引用完整性与可 join 性；组合字段无法阻止 `revision_no` 与 set 不一致。`request_payload` 保留一份用于 provenance、调试与未来兼容。

### D9：provenance 完整 + soft delete + draft 乐观锁

**provenance 字段归属**（与 D3b 的快照下沉一致，design 与 tasks 字段清单保持一致）：

| 实体 | provenance 字段 |
|---|---|
| `ManualAnnotationSet` | `created_by`、`created_at`、`updated_at`、`deleted_at` |
| `ManualAnnotationRevision` | `created_by`、`updated_by`、`reviewed_by`、`review_status`、`reviewed_at`、`created_at`、`updated_at`、`deleted_at`、`schema_version`、`phase_profile_id`、`phase_profile_version`、`phase_profile_hash`、`edit_version` |
| `ManualPhaseSegment` | `created_by`、`updated_by`、`reviewed_by`、`review_status`、`confidence`、`note`、`created_at`、`updated_at`、`deleted_at`、`schema_version` |

**soft delete**：UI 的"删除"表现为删除，数据层执行 soft delete（`deleted_at`），保留审计记录，避免训练数据不可追溯。

**draft 乐观锁**：`ManualAnnotationRevision.edit_version` 为整数，draft revision 每次内容变更递增。写请求 MUST 携带客户端读到的 `edit_version`，不匹配时返回 409。

- **备选 A**：硬删除 / 无并发保护
- **备选 B（采纳）**：soft delete + `edit_version` 乐观锁
- **理由**：标注是未来训练数据的来源，删除即丢失溯源证据。全库目前无 `deleted_at` 先例，本次建立该约定。乐观锁是因为工作台是 Web 应用，两个浏览器标签页同时编辑同一 draft revision 完全可能——无保护则后保存方静默覆盖前者。

### D9b：`confidence` 是人工判据置信度，不由 `review_status` 推导

`confidence` 表示"边界本身是否清晰"（如入水瞬间被水花遮挡 → 低置信），`review_status` 表示"是否经过专家复核"。这是两个正交维度。

- `reviewed` ≠ `confidence = 1.0`
- `confidence` 允许为 NULL（标注员未评估时不填）
- 系统 MUST NOT 根据 `review_status` 自动赋值 `confidence`
- 未来模型推荐标签引入 `model_confidence` 独立字段，不复用 `confidence`

### D10：ML export 只定义契约，不实现服务

本 Change 保留以下字段并定义未来 export contract 的接口形状：
`video_checksum_sha256 / annotation_set_id / revision_id / revision_no / content_hash / phase_profile_id / phase_profile_version / phase_profile_hash / cycle_id / side / phase_code / start_time_sec / end_time_sec / frame snapshot + frame_basis / annotator + reviewer provenance / review status / confidence`。

`dataset_snapshot`、`train/val/test` split、inter-rater agreement、adjudication workflow 本 Change **只定义接口与数据要求，不实现**。

其中三项现在不预留将来补不上的字段：
1. `phase_profile_hash` —— 否则无法证明两次导出用的是同一套环节定义
2. `content_hash` / `segments_hash` —— 否则无法证明两次导出是同一份数据
3. 数据集拆分的两个层级必须分开表述（不是两个并列的 split 维度）：

```
sample unit（样本构造单元）      = cycle_id
split leakage group（防泄漏组）  = video_checksum_sha256
```

含义：模型样本可以按 cycle 构造（一个 cycle 的四个 phase 作为一组，不拆散），但**同一个 source video 的所有 cycles 必须落在同一个 train / val / test split 中**。这样既不会把一个 cycle 的四阶段拆开，也不会把同一视频的相邻周期泄漏到训练集与测试集。

### D11：前端多轨 timeline，按 side 分轨

工作台按 `side` 分左右两轨，每轨按 `cycle_id` 分组渲染区间。提供帧步进、区间拖拽端点、数值输入框三种设定方式（同时满足粗标与精修）。

- **备选 A**：单轨混合渲染，用颜色区分 side
- **备选 B（采纳）**：左右分轨
- **理由**：自由泳左右臂区间在时间轴上大量重叠，单轨无法并列展示，且无法直观判断同侧周期是否齐全。

## Risks / Trade-offs

- **[Risk] 人工区间与 imported events 长期并存，可能出现语义漂移** → Mitigation：adapter 是唯一转换点，派生结果永不回写；`source_of_truth` 显式裁决；冲突只告警不自动修复
- **[Risk] `SessionVideo.fps` 为 `Numeric(6, 2)`，29.97 / 59.94 有精度损失** → Mitigation：`frame_basis` 记录 fps 来源，人工 label 的时间精度不依赖该字段；compatibility adapter 转帧时产生的误差记入 warning。该问题作为技术债记录
- **[Risk] compatibility adapter 的 `秒 → 帧` 转换引入与既有 metrics 不一致的取整行为** → Mitigation：统一采用 `round(t * fps)`，并在 revision 上记录 `frame_basis.fps_source`，使转换可复现
- **[Risk] 三张新表 + `cycle_id` 让查询变复杂** → Mitigation：`INDEX(revision_id)`、`(revision_id, side)`、`(revision_id, cycle_id)`、`(revision_id, side, cycle_id)`、`(set_id, revision_no)` 索引；resolver 只做单 revision 查询，不做跨版本聚合
- **[Risk] 前端多轨 timeline 交互成本被低估** → Mitigation：第一版只支持"数值输入 + 拖拽端点"，不做框选批量标注、不做键盘高效标注流
- **[Risk] soft delete 让所有查询都要带 `deleted_at IS NULL`** → Mitigation：在数据访问层统一封装，禁止业务代码直接写 SQL 过滤
- **[Trade-off] 不修旧 event pipeline 意味着旧数据仍只能三段** → 接受，已记录为 follow-up；新人工标注本身即可产出完整四阶段
- **[Trade-off] DB 层不强制无重叠，依赖应用层校验** → 接受，这是为了保住 draft 的可编辑性
- **[Risk] canonical JSON 规则不统一，导致相同内容算出不同 `content_hash`** → Mitigation：D2b 已明确字段排序、排除字段集与浮点序列化规则；实现时 MUST 用同一函数计算 draft 与发布时的 hash，并写"同内容两次计算必须相等"的测试
- **[Risk] fork 时 `cycle_id` 若被重新生成，跨 revision 的周期 diff 与 ML provenance 会失效** → Mitigation：D4 已规定 fork 继承 `cycle_id`；实现时 MUST 有测试断言 fork 前后同一周期的 `cycle_id` 相同
- **[Risk] draft 并发编辑导致后保存方静默覆盖** → Mitigation：D9 的 `edit_version` 乐观锁；不匹配返回 409，前端 MUST 提示刷新而非自动重试

## Migration Plan

1. 新增 alembic migration `20260907_0017_add_manual_reference_labels`
   - 建表 `manual_annotation_sets` / `manual_annotation_revisions` / `manual_phase_segments`
   - **循环 FK 处理**：`sets.head_revision_id → revisions.id` 与 `revisions.set_id → sets.id`
     互相引用。建表时 MUST 先建 `sets` 且**不带** `head_revision_id` FK，待 `revisions` 建完再用
     `op.create_foreign_key("fk_manual_annotation_sets_head_revision", ...)` 补上，否则 PostgreSQL
     报 `relation "manual_annotation_revisions" does not exist`
   - `analysis_tasks` 增加 `reference_annotation_revision_id` 可空 FK + 索引
   - downgrade **MUST 按以下顺序**（两处 FK 都要先解除，否则 PostgreSQL 拒绝删表）：
     1. drop `analysis_tasks.reference_annotation_revision_id` 的索引与 FK 约束，再 drop column
     2. drop `manual_annotation_sets.head_revision_id` 指向 revisions 的 FK 约束
        （不先解它，第 4 步删 revisions 会被 sets 的 FK 依赖挡住）
     3. drop table `manual_phase_segments`
     4. drop table `manual_annotation_revisions`
     5. drop table `manual_annotation_sets`
2. 新增 `freestyle_arm_phase_v1.yaml` profile，与既有 `side_technical_v1.yaml` 并存，不修改后者
3. 后端服务层与 API 先行，前端工作台后接
4. 下游 `metrics_service` / `diagnostics/bridge.py` 改为经 resolver 取 revision；`reference_annotation_revision_id` 为 NULL 时行为与改动前完全一致（fallback 到 imported events）
5. **回滚**：三张新表与 FK 列均为新增且可空，回滚只需 `alembic downgrade -1`；已有 analysis task 的 `reference_annotation_revision_id` 为 NULL，不受影响

## Open Questions

1. ~~`cycle_id` 用 UUID v4 还是 set 内单调整数？~~ **已定**：UUID v4，作为跨 revision 稳定的逻辑标识，fork 时继承（见 D4）
2. 第一版工作台是否需要"复制上一周期区间"这类提效操作？—— 待实现时按工作量决定
3. ~~`confidence` 由标注者手填还是按 review 状态自动赋值？~~ **已定**：标注者手填、可为 NULL，MUST NOT 由 `review_status` 推导（见 D9b）
4. ~~fork 时是否继承 `note`？~~ **已定**：继承 `note`，重置 `review_status` 与 `reviewed_by`，继承 `cycle_id`
5. 是否需要限制同一 `session_video_id` 下可存在的 set 数量？—— 倾向不限制，待实现时确认
6. `rejected` 状态是否允许直接重新打开为 `draft`？—— 当前设计限定必须 fork，待实现时确认是否放宽

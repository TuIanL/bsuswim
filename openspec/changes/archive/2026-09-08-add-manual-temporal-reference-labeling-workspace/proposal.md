## Why

当前平台的动作阶段信息只有两类来源：外部标注工具（Kinovea / CVAT）导入的**瞬时点事件**，以及模型服务输出的阶段提示。两者都是"点"语义，没有"某环节从 t1 持续到 t2"的显式区间表达，也没有让教练在平台内直接修正、复核、沉淀时序判断的入口。

更关键的是，现有点事件体系把 `hand_exit` 只写在契约里而没有任何产出方（全仓库仅 3 处出现，无 parser 产出、无质量门校验），导致自由泳四阶段（入水 / 抱水 / 推水 / 移臂）在真实数据中退化成三段，推水与移臂无法分离。

同时，未来动作周期识别与阶段分割模型需要可复现的训练 / 验证数据，而现在没有任何结构化载体能承载"谁在哪个版本的视频上、按哪套环节定义、标注了哪些区间、经过谁复核"。

因此需要一个**人工时序参考标注（reference label）资产层**：让教练在平台内直接标注区间，按 set / revision 谱系沉淀，可复核、可冻结、可被下游显式引用，并为未来数据集导出预留完整 provenance。

命名上，这些人工标注先称为 **reference labels**，不直接称为 ground truth。只有经专家复核（reviewed / adjudicated）的标注集，后续才允许进入 gold dataset 或正式模型评估集。

## What Changes

- 新增三层数据模型 `manual_annotation_sets` / `manual_annotation_revisions` / `manual_phase_segments`
  - set = 一条视频上的一套逻辑标注谱系；revision = 不可变内容版本；segment = 一条时间区间
  - segment 通过 `revision_id` FK 引用 revision；`revision_no` 仅作展示与冗余，**不承担引用完整性**
  - 归属固定 `session_video_id`，**不挂 `analysis_task`**：分析任务只消费某一 revision，不拥有标注
  - 时间 canonical 为 `start_time_sec` / `end_time_sec`；`start_frame` / `end_frame` 是带 `frame_basis` 的派生快照，不是第二套权威时间
- 新增 `freestyle_arm_phase_v1` 环节定义
  - 四阶段 `entry` / `catch` / `push` / `recovery`，中文"入水 / 抱水 / 推水 / 移臂"仅作展示名，存储与 API 一律用稳定 code
  - cycle 定义沿用既有契约（`side_technical_v1.yaml: partition_by: side, cycle_boundary: hand_entry`）：同侧 `hand_entry` → 下一次同侧 `hand_entry`
  - 显式 `side`（left / right）+ 稳定 `cycle_id`；`cycle_index` 仅作排序与展示，可为空且允许乱序标注
- 新增前端工作台：左右臂双轨 timeline，区间增删改，draft / reviewed / frozen 生命周期交互
- 新增 `label-event-adapter`：单一转换点，`source_of_truth ∈ {manual_segments, imported_events}` 裁决，支持双向派生但**派生结果一律不回写任一侧**
- 新增 `reference-revision-resolver`：显式按 `annotation_set_id` + `revision_id` 解析，禁止按 session 取 latest
- `analysis_tasks` 新增 `reference_annotation_revision_id` FK，并在 `request_payload.analysis_input` 镜像 provenance
- 预留 ML-ready provenance 字段与未来 dataset export contract（本 Change 只定义契约，不实现导出服务）

**BREAKING**：无。全部为新增表 / 字段 / 端点；`analysis_tasks.reference_annotation_revision_id` 可空，既有任务行为不变。

## Capabilities

### New Capabilities

- `manual-reference-label-model`：annotation set / 不可变 revision / phase segment 三层数据模型、CRUD API、provenance 与 soft delete、ML 导出所需字段与未来 export contract
- `reference-label-lifecycle`：draft → in_review → reviewed → frozen 状态机、fork 语义、分级校验规则、重叠约束作用域
- `freestyle-arm-phase-profile`：`freestyle_arm_phase_v1` 环节定义、与既有边界事件的映射、缺边界时的 partial derivation 规则
- `label-event-adapter`：`source_of_truth` 裁决、segments→events 与 events→segments 单向派生、冲突告警与禁止回写
- `reference-revision-resolution`：显式 resolver、analysis task revision 快照、禁止隐式 latest 回退
- `manual-labeling-workspace`：前端手工区间标注工作台（多轨 timeline、区间 CRUD、生命周期交互）

### Modified Capabilities

- `annotation-driven-analysis-pipeline`：分析流水线 MUST 消费显式 `reference_annotation_revision_id`，MUST NOT 按 session 查询 latest 标注；revision 缺失或 video checksum 不匹配时 MUST 生成 warning 而非静默回退

## Impact

- 后端新增
  - `backend/app/models/manual_reference_label.py`（3 张表）
  - `backend/app/schemas/manual_reference_label.py`
  - `backend/app/api/routes/manual_reference_labels.py`
  - `backend/app/services/reference_labels/`（adapter / resolver / validator / profile loader）
  - `backend/app/services/reference_labels/profiles/freestyle_arm_phase_v1.yaml`
- 数据库：新增 alembic migration `00xx_add_manual_reference_labels`；`analysis_tasks` 增加列 `reference_annotation_revision_id`（可空 FK）+ 索引
- 前端新增
  - `frontend-vue/src/views/ManualLabelingView.vue` 及 timeline 组件
  - `frontend-vue/src/router.ts` 新增路由
  - `frontend-vue/src/services/api.ts` 新增客户端方法
- 下游：`metrics_service` / `diagnostics/bridge.py` 的调用方改为经 resolver 取 reference revision
- 依赖：无新增外部依赖

### 已知遗留（本 Change 不修复，作为 follow-up 记录）

1. `hand_exit` 在既有 imported-event pipeline 中无产出方（全仓库仅 `side_technical_v1.yaml:70`、`temporal_checks.py:91`、归档 `design.md:265` 三处），导致旧数据最多三段，推水与移臂无法分离
2. `temporal_checks.py:91` 使用 `"recovery"`，而 profile yaml 的 `optional` 使用 `recovery_peak`，命名不一致使 optional 配置实际失效（被 `in event_order` 过滤）
3. `coverage_checks.py:177 check_cycle_completeness` 统计 hand_entry 未按 side 分区，双侧视频会重复计数
4. 既有 metrics 层实际以 `(frame, fps)` 为时间源，与 `annotation-time-mapping` 规范声明的 `timestamp_sec` 权威不一致；本 Change 通过 compatibility adapter 转换，不改造 metrics
5. `SessionVideo.fps` 为 `Numeric(6, 2)`，对 29.97 / 59.94 存在精度损失风险；人工 reference label 的时间精度 MUST NOT 依赖该字段

### 建议的 follow-up Change

- 统一修复既有 imported-event 体系：`hand_exit` 提为必选边界、`recovery` / `recovery_peak` 命名统一、`check_cycle_completeness` 按 side 分区
- 实现 dataset export 服务与 train / val / test split（样本构造单元 sample unit = `cycle_id`，防泄漏组 split leakage group = `video_checksum_sha256`，同一 source video 的全部 cycle 必须落在同一 split）
- 将 metrics 层时间源迁移到 `timestamp_sec`，消除规范与实现的脱节

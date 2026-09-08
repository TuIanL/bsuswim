> **实现 + 验证完成（2026-09-08）**。已在 Docker Postgres（`bsuswim-postgres`，`swim:swim@localhost:5432/swim_analysis`）
> 与项目 conda base 环境（`/Users/tuian/miniconda3/bin/python`）实跑通过：
> - `alembic upgrade head` / `downgrade -1` / 再 `upgrade head` **往返成功**（循环 FK 顺序正确）
> - 后端 `pytest tests -q` → **529 passed, 1 skipped, 0 failed**
> - 前端 `vue-tsc --noEmit` 类型检查通过、`vite build` 打包成功、`vitest` → **52 passed**
>
> 验证中发现并修复的 6 个真实缺陷（均为实现期 bug，非设计问题）：
> 1. `create_set` / `fork_revision` 在 `flush()` **之后**才赋 `content_hash`，而该列 NOT NULL → INSERT 直接失败；
>    改为 flush 前给初值（空集 hash / 继承源 hash），复制完 segment 后重算。
> 2. `hashing._fmt_value` 未识别 `Decimal`（Numeric 列读回类型）→ `json.dumps` 报
>    "Object of type Decimal is not JSON serializable"。
> 3. `adapter.events_to_segments` 把结尾孤立的 `hand_entry`（下一周期的终止边界）当作不完整周期，
>    导致 `complete` 永远为 False；改为仍参与提供 recovery 结束时间，但跳过完整性校验。
> 4. `service._make_segment` 的 `confidence` / `note` / `derivation` 缺默认值 → 调用方未传时 TypeError。
> 5. 测试从 `adapter` 导入 `STATUS_LEGACY`（实为 `resolver` 定义）。
> 6. 编辑 `analysis_service` 时误将 `AnalysisTaskAlreadyActiveError.__init__` 划入新增的
>    `ReferenceRevisionInvalidError`，导致 2 个既有测试失败；已归还。
>
> 注：跑 pytest 时若出现 `PermissionError: EEXIST ... pytest-of-unknown`，加 `--basetemp=/tmp/xxx` 即可（沙箱限制）。
> `vite build` 清空旧 `dist` 会触发批量删除保护，可改用 `--outDir /tmp/...` 验证打包。

## 1. 数据模型与数据库迁移

- [x] 1.1 新增 `backend/app/models/manual_reference_label.py`，定义 `ManualAnnotationSet`（只含谱系与归属：`session_video_id` FK、`phase_profile_id` 仅作新建 revision 时的默认 profile、`head_revision_id`、`created_by`、`created_at`、`updated_at`、`deleted_at`）
- [x] 1.2 定义 `ManualAnnotationRevision`，承载全部可复现快照：`set_id` FK、`revision_no`、`forked_from_revision_id`、`video_checksum_sha256`、`video_fps_snapshot`、`video_duration_snapshot`、`frame_basis`、`phase_profile_id`、`phase_profile_version`、`phase_profile_hash`、`content_hash`、`status`、`segment_count`、`cycle_count`、`edit_version`（乐观锁）、provenance 字段（`created_by` / `updated_by` / `reviewed_by` / `review_status` / `reviewed_at` / `created_at` / `updated_at` / `deleted_at` / `schema_version`）
- [x] 1.3 定义 `ManualPhaseSegment`（含 `revision_id` FK NOT NULL、`cycle_id` UUID、`cycle_index`、`side`、`phase_code`、`start_time_sec`、`end_time_sec`、`start_frame`、`end_frame`、`confidence`（nullable）、`note`、`derivation`、`created_by` / `updated_by` / `reviewed_by` / `review_status` / `created_at` / `updated_at` / `deleted_at` / `schema_version`）
- [x] 1.4 建表并建索引：`INDEX(revision_id)`、`INDEX(revision_id, side)`、`INDEX(revision_id, cycle_id)`、`INDEX(revision_id, side, cycle_id)`、`INDEX(set_id, revision_no)`、`INDEX(session_video_id)`；**注意 segment 表没有 `set_id` 列，不得建 `(set_id, revision_id)` 索引**
- [x] 1.5 建立约束：`UNIQUE(set_id, revision_no)`；`UNIQUE(revision_id, cycle_id, side, phase_code)`；**MUST NOT 建立 `UNIQUE(set_id, content_hash)`**（fork 出来的 revision 内容必然与源相同，会直接违反约束），改为普通 index
- [x] 1.6 同一 migration 为 `analysis_tasks` 增加可空列 `reference_annotation_revision_id`（FK → `manual_annotation_revisions.id`，ondelete SET NULL）及索引
- [x] 1.7 编写 migration downgrade，**顺序 MUST 为**：① drop `analysis_tasks.reference_annotation_revision_id` 的索引与 FK → ② drop `manual_annotation_sets.head_revision_id` 指向 revisions 的 FK（循环 FK，不先解则删 revisions 被挡）→ ③ drop `manual_phase_segments` → ④ drop `manual_annotation_revisions` → ⑤ drop `manual_annotation_sets`；并验证 `alembic upgrade` / `downgrade -1` 往返成功。建表时 `sets.head_revision_id` 的 FK MUST 在 revisions 建完后用 `op.create_foreign_key` 补（否则报 relation does not exist）

## 2. freestyle_arm_phase_v1 环节定义

- [x] 2.1 新增 `backend/app/services/reference_labels/profiles/freestyle_arm_phase_v1.yaml`，含 `id`、`version`、`cycle_definition`（`partition_by: side`、`boundary: hand_entry`）、`phases`（entry/catch/push/recovery，各带 `display`）、`required_boundaries`、`optional_boundaries`
- [x] 2.2 在 yaml 中补充 `boundary_definitions`，为每个边界写出**人工操作定义**（operational definition），至少含 `display`、`operational_definition`、`reference_joint`、`annotation_guidance`；必须回答：
  - `hand_entry`：指尖首次触水 / 手掌过水面 / 腕关节过水面 —— 取哪一个
  - `catch_start`：前臂开始改变方向 / 肘屈曲超过阈值 / 建立有效迎水面 —— 取哪一个
  - `pull_end`：拉水结束与推水开始的分界判据
  - `hand_exit`：手掌离水 / 腕关节离水 / 指尖完全离水 —— 取哪一个
- [x] 2.3 实现 profile loader，支持按 `phase_profile_id` 加载、校验结构完整性（含 `boundary_definitions` 必填）、计算 `phase_profile_hash`
- [x] 2.4 实现 phase code ↔ 中文展示名映射，供 API 与前端消费
- [x] 2.5 前端标注工作台 MUST 能按需展示每个边界的 `annotation_guidance`（悬停或帮助入口），使不同标注员依据同一判据标注
- [x] 2.6 校验 profile 与既有 `side_technical_v1.yaml` 的 cycle 定义一致（`partition_by: side` + `cycle_boundary: hand_entry`），并写一致性测试

## 3. 校验层

- [x] 3.1 实现 L1 结构校验：起止时间合法性、视频时长边界、`side` 枚举、`phase_code` 属于 profile、`cycle_id` 非空
- [x] 3.2 实现 L2 周期完整性校验：同 `(side, cycle_id)` 内四阶段齐全、无重叠、相邻空隙 ≤ 阈值；跨 side 与跨 cycle 的重叠 MUST NOT 报错
- [x] 3.3 L2 增加 `side` 收敛校验：`reviewed` / `frozen` 数据 MUST 只允许 `left` / `right`，含 `both` / `unknown` 时 MUST 阻止发布（`both` / `unknown` 仅允许 `draft`）
- [x] 3.4 实现 L3 profile 严格校验：完整 cycle 数 ≥ `minimum_complete_cycles`、cycle 边界落在 `hand_entry` 上、与同源点事件交叉一致（无同源事件时跳过）
- [x] 3.5 实现 `content_hash` 计算（canonical JSON → sha256），规则 MUST 为：字段按 key 字典序排序；排除 `id` / `created_at` / `updated_at` / `deleted_at` / `revision_id` / `cycle_index` 等非语义字段；参与哈希的语义字段为 `cycle_id` / `side` / `phase_code` / `start_time_sec` / `end_time_sec` / `confidence` / `note`；浮点时间按固定小数位序列化；已 soft delete 的 segment 不参与
- [x] 3.6 `content_hash` 按状态稳定：`draft` 随增删改重算；`in_review` / `reviewed` / `frozen` / `rejected` 固定不再变化
- [x] 3.7 实现内容不可变守卫：revision 一旦离开 `draft` 状态，任何 segment 写操作 MUST 被拒绝（409），`in_review` 即锁内容
- [x] 3.8 实现 draft 乐观锁：`edit_version` 随内容变更递增，写请求携带的 `edit_version` 不匹配时返回 409
- [x] 3.9 为三层校验、hash 规范化、不可变守卫、乐观锁各编写单元与集成测试；必须包含"相同内容两次计算 `content_hash` 必须相等"与"fork 前后同一 cycle 的 `cycle_id` 相同"两条断言

## 4. Adapter 与 Resolver

- [x] 4.1 实现 `source_of_truth` 解析，**完全由 `AnalysisTask` 的显式引用驱动**：`reference_annotation_revision_id != NULL` → `manual_segments`；`== NULL` → `imported_events`（legacy 行为）。MUST NOT 实现"发现数据库存在 reviewed/frozen revision 就自动切换"的推断逻辑——同一 session video 存在多个已发布 revision 时系统 MUST NOT 自行挑选
- [x] 4.2 `AnalysisTask` 引用 revision 时校验其状态：只允许 `in_review` / `reviewed` / `frozen`，引用 `draft` MUST 被拒绝
- [x] 4.3 实现 segments → events 派生，按 `freestyle_arm_phase_v1` 映射产出 `hand_entry` / `catch_start` / `pull_end` / `hand_exit`，`labeled_by = manual`，携带 `revision_id` 与 `side`
- [x] 4.4 实现 events → segments 派生，四边界齐全时生成完整四阶段并标记 `derivation = event_derived`；缺 `hand_exit` 时返回 partial derivation 并标记 `recovery_unavailable` / `missing_hand_exit`，禁止猜测
- [x] 4.5 实现 compatibility adapter 的 `秒 → 帧` 转换，统一 `round(t * fps)`，缺 `frame_basis` 时返回空值而非猜测
- [x] 4.6 实现冲突检测：边界时间偏差与阶段缺失生成 conflict / warning，不自动修复、不回写
- [x] 4.7 实现 `resolve_reference_labels(set_id, revision_id)`，返回 `ready` / `not_found` / `revision_mismatch` / `checksum_mismatch` / `profile_mismatch` / `checksum_unknown`；且不提供按 session 取 latest 的入口
- [x] 4.8 resolver 校验 revision 上记录的 `video_checksum_sha256` 与当前 `VideoFile.checksum_sha256`，并校验 `phase_profile_hash` 与任务快照一致
- [x] 4.9 实现"显式指定但不可用 MUST NOT 回退"：resolver 返回非 `ready` 时，调用方 MUST 返回 `reference_input_invalid` 并阻断相关分析，MUST NOT 回退到 imported events 或其他 revision
- [x] 4.10 编写 adapter 双向派生测试，重点覆盖"派生结果不回写"、partial derivation、以及"显式引用失效时不回退"

## 5. API 层

- [x] 5.1 新增 `backend/app/schemas/manual_reference_label.py`，含 set / revision / segment 的读写 schema；revision schema MUST 承载 `video_checksum_sha256` / `video_fps_snapshot` / `video_duration_snapshot` / `frame_basis` / `phase_profile_id` / `phase_profile_version` / `phase_profile_hash` / `content_hash` / `edit_version`
- [x] 5.2 新增 `POST /api/session-videos/{session_video_id}/manual-annotation-sets`，创建 set 并同时创建首个 draft revision；revision 创建时 MUST 快照当前视频的 checksum / fps / duration / frame_basis 与 profile 版本与 hash
- [x] 5.3 新增 `GET /api/session-videos/{session_video_id}/manual-annotation-sets`
- [x] 5.4 新增 `GET /api/manual-annotation-revisions/{revision_id}` 与 `.../segments`，响应 MUST 包含该 revision 的可复现快照字段
- [x] 5.5 新增 segment CRUD：`POST /api/manual-annotation-revisions/{revision_id}/segments`、`PATCH /api/manual-phase-segments/{segment_id}`、`DELETE /api/manual-phase-segments/{segment_id}`（soft delete）；写请求 MUST 携带 `edit_version`
- [x] 5.6 revision 离开 `draft` 后（含 `in_review`）的写操作返回 409，并写测试
- [x] 5.7 实现 fork 端点：从指定 revision 创建新 draft revision，**继承 `cycle_id`**（fork 出来的相同周期必须保持同一 `cycle_id`）、保留 `note`、重置 `review_status` 与 `reviewed_by`、记录 `forked_from_revision_id`、重新快照当前视频与 profile 信息
- [x] 5.8 实现生命周期端点：提交复核（先跑 L1+L2，含 `side` 收敛校验）、复核通过、打回、冻结（先跑 L3）
- [x] 5.9 所有查询默认过滤 `deleted_at IS NULL`，并在数据访问层统一封装
- [x] 5.10 新增 `GET /api/phase-profiles/{phase_profile_id}`，返回 phases 与 `boundary_definitions`，供前端展示人工标注判据

## 6. 分析任务快照与下游接线

- [x] 6.1 `AnalysisTask` 模型增加 `reference_annotation_revision_id` 字段与 relationship
- [x] 6.2 任务创建时写入 FK，并在 `request_payload.analysis_input` 镜像 `reference_annotation_set_id`、`reference_annotation_revision_id`、`revision_no`、`content_hash`、`video_checksum_sha256`、`phase_profile_id`、`phase_profile_version`、`phase_profile_hash`
- [x] 6.3 改造 `metrics_service` 与 `diagnostics/bridge.py` 的调用方，改为经 resolver 取 reference revision
- [x] 6.4 **仅当未指定** reference revision 时才回退 imported events，并在 quality / warning 中显式记录该回退
- [x] 6.5 已指定 reference revision 但 resolver 返回非 `ready` 时，MUST 记录 `reference_input_invalid` 并阻断相关分析，MUST NOT 回退到 imported events
- [x] 6.6 产物记录 `source_of_truth`、对应 revision 标识、`phase_profile_version` 与 `phase_profile_hash`
- [x] 6.7 验证历史任务（`reference_annotation_revision_id` 为 NULL）行为与改动前完全一致

## 7. 前端工作台

- [x] 7.1 新增 `frontend-vue/src/views/ManualLabelingView.vue` 与路由 `/sessions/:sessionId/videos/:sessionVideoId/labels`
- [x] 7.2 `services/api.ts` 新增 set / revision / segment 的客户端方法
- [x] 7.3 实现视频播放区与播放位置同步，含视频不可加载时的稳定错误态
- [x] 7.4 实现左右臂分轨 timeline 组件，按 `cycle_id` 分组，支持区间拖拽端点
- [x] 7.5 实现区间创建表单：数值输入起止秒 + 环节下拉（中文展示名 / code 提交）+ 使用当前播放位置
- [x] 7.6 实现区间编辑与删除；revision 离开 `draft` 后（含 `in_review`）禁用编辑并展示 fork 入口
- [x] 7.7 实现生命周期操作 UI：提交复核、复核通过、打回、冻结、fork，并展示 lineage
- [x] 7.8 展示 L2 校验冲突详情（冲突区间与阶段），并标记派生区间与不可用阶段
- [x] 7.9 确认界面不出现数据集导出、自动阶段识别、adjudication 等未实现入口
- [x] 7.10 在环节选择处提供 `boundary_definitions.annotation_guidance` 的查看入口（悬停或帮助），使不同标注员依据同一判据标注
- [x] 7.11 处理乐观锁冲突：写请求收到 409（`edit_version` 不匹配）时 MUST 提示用户刷新，MUST NOT 自动重试覆盖
- [x] 7.12 `side` 选择：`draft` 允许 `both` / `unknown`，提交复核前 MUST 提示收敛为 `left` / `right`

## 8. 测试与文档

- [x] 8.1 后端模型测试：三层引用完整性、soft delete、provenance 字段写入
- [x] 8.2 后端生命周期测试：状态机流转、**离开 draft（含 `in_review`）后内容不可改**、fork 行为
- [x] 8.3 后端 profile 测试：四阶段映射、partial derivation、未知 profile 拒绝、`boundary_definitions` 必填校验
- [x] 8.4 后端 resolver 测试：`revision_mismatch`、`checksum_mismatch`、`profile_mismatch`、**无 latest 回退入口**、**显式引用失效时不回退到 imported events**
- [x] 8.5 后端 API 集成测试：CRUD、409 拒绝、`request_payload` 镜像一致性
- [x] 8.6 前端组件测试：timeline 渲染、区间创建校验、非 draft 禁用态
- [x] 8.7 后端 `content_hash` 测试：**fork 出来的 revision 与源 revision 内容相同时必须都能保存**（验证无 `UNIQUE(set_id, content_hash)`）、相同内容两次计算结果相等、发布后 hash 固定
- [x] 8.8 后端并发测试：draft `edit_version` 不匹配时返回 409，不静默覆盖
- [x] 8.9 后端 `side` 收敛测试：`both` / `unknown` 可存 draft，但 MUST 被 L2 拦截无法进入 reviewed
- [x] 8.10 migration 往返测试：`alembic upgrade` 后 `downgrade -1` 必须成功（验证 FK 先于删表解除）
- [x] 8.11 在 proposal 与 design 中已记录的 5 项已知遗留，确认已写入 follow-up 清单
- [x] 8.12 更新 `docs/database-design.md`，补充三张新表与 `analysis_tasks` 新列

## 9. Follow-up 记录（本 Change 不实现）

- [x] 9.1 记录 follow-up：`hand_exit` 在旧 imported-event pipeline 提为必选边界
- [x] 9.2 记录 follow-up：`temporal_checks.py` 的 `recovery` 与 profile `recovery_peak` 命名统一
- [x] 9.3 记录 follow-up：`check_cycle_completeness` 按 side 分区统计
- [x] 9.4 记录 follow-up：metrics 层时间源迁移到 `timestamp_sec`
- [x] 9.5 记录 follow-up：`SessionVideo.fps` 精度升级（`Numeric(6, 2)` → 更高精度）
- [x] 9.6 记录 follow-up：dataset export 服务与 train/val/test split（sample unit = `cycle_id`，split leakage group = `video_checksum_sha256`，同一 source video 的全部 cycle 必须落在同一 split）

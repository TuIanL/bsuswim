# 侧面视角技术指标定义（side-view metrics）

> 配套实现：Change #4 `add-side-view-technical-metrics-calculation`
> 输出 schema：`swim-side-metrics.v1`
> 本文件只描述**事实测量值**，不描述诊断结论（诊断交给 Change #5，报告装配交给 Change #6）。

本文件逐一定义引擎产出的每个指标，供教练、前端（Change #6 report builder）与诊断模块（Change #5）对齐口径。每个指标包含：名称 / 中文名 / 公式 / 所需关键点 / 所需事件 / 单位 / 缺失处理 / 是否进 MVP 报告。

---

## 0. 全局约定

- **坐标系**：图像坐标，y 轴向下。`angle_to_horizontal` 取绝对值，因此身体/前臂与水平夹角结果恒为 0–90°，不随游进左右方向翻转。
- **三点角 `angle_between_points(a,b,c)`**：返回 ∠ABC（顶点 b），范围 0–180°。
- **依赖 `ppm`**：`pixels_per_meter`，取自 `annotation.scale.pixels_per_meter`。所有距离/速度类指标缺 ppm 时降级为 null。
- **`view_type`**：引擎入口参数，来自 `session_videos.view_type`。仅 `side` 支持；非 side 由端点返回 422（见下「非 side 处理」）。
- **核心关键点（CORE_KEYPOINTS）**：`shoulder / elbow / wrist / hip / knee / ankle`。也接受 `left_`/`right_` 前缀变体。缺核心点 → quality `error`。
- **最低可计算前提**：`fps` 有效 + `scale.pixels_per_meter` 存在 + ≥3 帧关键点（六点齐全，任一前缀）+ ≥1 个 `hand_entry` 或起止事件。

---

## A. 身体位置与流线型

### A.1 `body_angle_deg`
- **中文名**：身体倾角
- **公式**：`angle_to_horizontal(shoulder, ankle)`（取 abs，逐帧），再汇总 `avg / min / max`
- **所需关键点**：`shoulder`, `ankle`（任意一帧两者都可用即计入）
- **所需事件**：无
- **单位**：度（°）
- **输出 key**：`body_angle_deg_avg`、`body_angle_deg_min`、`body_angle_deg_max`
- **缺失处理**：某帧缺 shoulder 或 ankle → 该帧跳过；所有帧都缺 → 三个值均不产出（计入 `skipped_metrics`）
- **MVP 报告**：✅ 进报告

### A.2 `hip_depth_cm`
- **中文名**：髋部深度（相对水面）
- **公式**：`(hip.y − waterline_y@hip.x) / ppm × 100`，其中 `waterline_y@hip.x` 由 `reference_lines.waterline` 的两点线性插值得到
- **所需关键点**：`hip`
- **所需事件**：无
- **所需参考**：`reference_lines.waterline`（含 `points: [[x1,y1],[x2,y2]]`）
- **单位**：厘米（cm）
- **输出 key**：`hip_depth_cm_avg`
- **缺失处理**：缺 `waterline` 或 `ppm` → 该指标为 null，记 `missing_waterline` warning；不阻塞其余指标
- **MVP 报告**：✅ 进报告（仅在 waterline 存在时有值）

### A.3 `streamline_index`
- **中文名**：流线型指数（内部复合子分）
- **公式**：`clamp(100 − body_penalty − hip_penalty − line_dev_penalty, 0, 100)`
  - `body_penalty = min(body_angle_deg_avg × 2.5, 40)`
  - `hip_penalty = min(max(hip_depth_cm_avg, 0) × 1.5, 30)`
  - `line_dev_penalty = 0`（v2 待引入身体线偏差）
- **所需关键点**：同 A.1 / A.2
- **单位**：无量纲（0–100）
- **输出 key**：`streamline_index`
- **缺失处理**：始终可计算（即使 hip_depth 缺失，penalty 取 0）。这是**数值子分**，不是诊断结论
- **MVP 报告**：⚠️ 作为内部数值展示，不与 `technical_stability_score` 混淆

---

## B. 上肢技术

### B.1 `entry_angle_deg`
- **中文名**：入水角
- **公式**：`angle_to_horizontal(shoulder, wrist)`（取 abs，逐帧），再取 `avg`
- **目标帧**：优先 `hand_entry` 事件所在帧；无 `hand_entry` 事件时回退到全部关键点帧，并置 `entry_estimated=true`
- **所需关键点**：`shoulder`, `wrist`
- **所需事件**：`hand_entry`（可选，用于精确取帧）
- **单位**：度（°）
- **输出 key**：`entry_angle_deg_avg`、`entry_estimated`
- **缺失处理**：缺 shoulder/wrist 帧 → 跳过；无 `hand_entry` 且全部帧都缺点 → 不产出（辅助指标，不阻塞）
- **MVP 报告**：⚠️ 辅助指标，MVP 报告可选展示

### B.2 `front_reach_distance_cm`
- **中文名**：前伸距离
- **公式**：`abs(wrist.x − shoulder.x) / ppm × 100`；符号由 `swim_direction` 消歧：
  - `left_to_right` → 取 `wrist.x − shoulder.x`
  - `right_to_left` → 取 `shoulder.x − wrist.x`
  - 未设置 → 取绝对值（记 `swim_direction_unset` warning）
- **所需关键点**：`shoulder`, `wrist`
- **所需字段**：`swim_direction`（用于符号）
- **单位**：厘米（cm）
- **输出 key**：`front_reach_distance_cm_avg`
- **缺失处理**：缺 `ppm` → 不产出；缺 `swim_direction` 仅影响符号判定（仍按绝对值计算）
- **MVP 报告**：✅ 进报告

> **`swim_direction` 用途说明**：仅用于消除前伸距离的方向正负歧义（游进方向不同，前伸的 x 增量方向相反）。不影响角度类指标。未设置时按绝对值计算，不阻塞。

### B.3 `elbow_angle_deg`
- **中文名**：肘角（抓水/划水关键指标）
- **公式**：`angle_between_points(shoulder, elbow, wrist)`（逐帧取 avg）
- **所需关键点**：`shoulder`, `elbow`, `wrist`
- **单位**：度（°）
- **输出 key**：`elbow_angle_deg_avg`
- **缺失处理**：某帧三点不全 → 该帧跳过；所有帧都缺 → 不产出
- **MVP 报告**：✅ 进报告（关键）

### B.4 `forearm_drop_angle_deg`
- **中文名**：前臂下压角
- **公式**：`angle_to_horizontal(elbow, wrist)`（取 abs，逐帧取 avg）
- **所需关键点**：`elbow`, `wrist`
- **单位**：度（°）
- **输出 key**：`forearm_drop_angle_deg_avg`
- **缺失处理**：某帧缺 elbow/wrist → 跳过
- **MVP 报告**：⚠️ 辅助指标，MVP 报告可选展示

### B.5 `catch_duration_sec` / `pull_duration_sec`
- **中文名**：抱水时长 / 推水时长
- **公式**：`mean(pull_end.time_sec − catch_start.time_sec)`（同名事件多次出现时取两两组合均值）
- **所需事件**：`catch_start`, `pull_end`
- **单位**：秒（s）
- **输出 key**：`catch_duration_sec`、`pull_duration_sec`（MVP 简化：两者取同一差值）
- **缺失处理**：缺任一事件 → 不产出（低成本指标，有事件才计算）
- **MVP 报告**：✅ 进报告（若事件齐全）

---

## C. 腿部技术

### C.1 `knee_angle_deg`
- **中文名**：膝角（打腿关键指标）
- **公式**：`angle_between_points(hip, knee, ankle)`（逐帧，输出 `avg / min / max`）
- **所需关键点**：`hip`, `knee`, `ankle`
- **单位**：度（°）
- **输出 key**：`knee_angle_deg_avg`、`knee_angle_deg_min`、`knee_angle_deg_max`
- **缺失处理**：某帧三点不全 → 跳过
- **MVP 报告**：✅ 进报告（关键）

### C.2 `hip_angle_deg`
- **中文名**：髋角
- **公式**：`angle_between_points(shoulder, hip, knee)`（逐帧取 avg）
- **所需关键点**：`shoulder`, `hip`, `knee`
- **单位**：度（°）
- **输出 key**：`hip_angle_deg_avg`
- **缺失处理**：某帧点不全 → 跳过
- **MVP 报告**：⚠️ 辅助指标，MVP 报告可选展示

### C.3 `ankle_extension_angle_deg`
- **中文名**：踝伸展角（近似）
- **公式**：小腿向量 `(knee→ankle)` 与「竖直向下」参考线的夹角（cos 反余弦）。**当前为近似**：待 `foot/toe` 关键点补充后，替换为膝-踝-趾三点角
- **所需关键点**：`knee`, `ankle`
- **单位**：度（°）
- **输出 key**：`ankle_extension_angle_deg_avg`
- **缺失处理**：缺 knee/ankle → 跳过
- **MVP 报告**：⚠️ 近似指标，MVP 报告标注「近似」

### C.4 `kick_frequency_hz`
- **中文名**：打腿频率
- **公式**：`count(kick_downbeat) / duration_sec`，其中 `duration_sec = (last_frame − first_frame) / fps`
- **所需事件**：`kick_downbeat`（≥2 个）
- **单位**：赫兹（Hz，次/秒）
- **输出 key**：`kick_frequency_hz`
- **缺失处理**：`kick_downbeat` < 2 个或缺 `fps` → 不产出（null），不阻塞其余指标
- **MVP 报告**：✅ 进报告（若事件齐全）

> **v2 延期**：`kick_amplitude_cm`（打腿幅度）需要踝部轨迹密度，标注稀疏时不准，不在 MVP 实现。

---

## D. 节奏与效率

> **`event.side` 用法说明**：`hand_entry` 事件带 `side` 字段（`left` / `right` / `both` / `unknown`）。引擎按 `side` 把事件分组，仅用**单侧**事件计算划水周期：
> - 若既有 `left` 又有 `right`，优先取**非 unknown** 的一侧作为划频基准（避免左右交替被误算成双倍频率）。
> - 若全部 `side=unknown`，则把 unknown 整体当作单侧处理。
> - 每个有效侧都会输出 `stroke_cycle_duration_sec_{side}` 与 `stroke_rate_spm_{side}`。

### D.1 `stroke_rate_spm`
- **中文名**：划频（单侧完整划水次数/分钟）
- **定义（固定）**：**单侧完整划水次数 / 分钟** = `60 / 单侧周期`（单侧周期 = 相邻同 side `hand_entry` 帧间隔 / fps 的均值）
- **公式**：`stroke_rate_spm_avg = 60 / mean(同侧相邻 hand_entry 间隔 / fps)`
- **所需事件**：`hand_entry`（带 `side`）
- **单位**：次/分钟（strokes per minute）
- **输出 key**：`stroke_rate_spm_avg`（汇总）+ `stroke_rate_spm_{side}`（分侧）
- **缺失处理**：缺 `hand_entry` → 不产出（null），记 `missing_hand_entry` warning
- **MVP 报告**：✅ 进报告（关键）
- **注意**：此定义刻意区别于「双臂总划水频率」。它只数**一侧**的入水次数，符合游泳训练对单侧划频的惯用口径。

### D.2 `stroke_cycle_duration_sec`
- **中文名**：划水周期时长
- **公式**：单侧相邻 `hand_entry` 间隔 / fps（均值）
- **输出 key**：`stroke_cycle_duration_sec_avg` + `stroke_cycle_duration_sec_{side}`
- **单位**：秒（s）
- **缺失处理**：同上

### D.3 `stroke_count`
- **中文名**：单侧划水计数
- **公式**：参与计算的单侧 `hand_entry` 事件总数（跨所选侧）
- **输出 key**：`stroke_count`
- **单位**：次（无量纲）
- **MVP 报告**：✅ 进报告

### D.4 `stroke_length_m`
- **中文名**：划幅
- **公式（优先级 1）**：`distance_delta / stroke_count`，其中 `distance_delta = 末 distance_marker.distance_m − 首 distance_marker.distance_m`
- **公式（回退）**：无 `distance_markers` 时按 `average_speed_mps / (stroke_rate_spm_avg / 60)` 估算（本 MVP 仅在存在 distance_markers 时计算，回退路径暂未启用）
- **所需字段**：`distance_markers`（优先级1）
- **单位**：米（m）
- **输出 key**：`stroke_length_m_avg`
- **缺失处理**：缺 `distance_markers` → 不产出（null），记 `no_phase_context` warning
- **MVP 报告**：✅ 进报告（若有距离标定）

### D.5 `average_speed_mps`
- **中文名**：平均速度
- **公式**：`(末 distance_marker.distance_m − 首 distance_marker.distance_m) / ((末 frame − 首 frame) / fps)`
- **所需字段**：`distance_markers`（≥2）、`fps`
- **单位**：米/秒（m/s）
- **输出 key**：`average_speed_mps`
- **缺失处理**：缺 `distance_markers` 或 `fps` → 不产出
- **MVP 报告**：✅ 进报告（若有距离标定）

### D.6 `swolf`
- **中文名**：SWOLF 效率指数
- **公式**：`time_span + stroke_count`，其中 `time_span = (末 cycle 帧 − 首 cycle 帧) / fps`；保留 `distance_m` 上下文
- **输出结构**：
  ```json
  {
    "value": 81.3,
    "time_sec": 63.5,
    "stroke_count": 18,
    "distance_m": 50.0
  }
  ```
- **所需事件**：`hand_entry`（形成 ≥1 个 cycle）
- **单位**：无量纲（时间秒 + 划数）
- **输出 key**：`swolf`
- **缺失处理**：无 cycle（<1 个单侧周期） → 不产出
- **MVP 报告**：✅ 进报告（若有距离标定，展示 distance_m 上下文）

### D.7 `cycles[]`
- **中文名**：划水周期明细
- **结构**：`[{cycle_index, start_frame, end_frame, duration_sec, events:{hand_entry, next_hand_entry}}]`
- **MVP 报告**：⚠️ 作为明细数据，供前端时间轴展示

---

## E. 引擎聚合输出

### E.1 `technical_stability_score`
- **中文名**：技术稳定性综合分（MVP）
- **定义**：MVP 阶段 **等于 `streamline_index`**，作为整体复合分的占位；与 `streamline_index`（身体流线**子分**）明确区分，后续可扩展为融合多组指标的加权分
- **单位**：无量纲（0–100）
- **MVP 报告**：⚠️ 标注「MVP 占位」

### E.2 `phase_metrics`（条件生成）
- **生成条件**：仅当 `distance_markers` 存在且 ≥2 个、且能分出 ≥2 段速度时生成
- **分段逻辑**：按相邻 `distance_marker` 推导瞬时速度，分 `low_speed`（低速阶段）/ `middle_speed`（过渡阶段）/ `high_speed`（高速阶段）；每相给出 `representative_frame` 与 `body_angle_deg` 均值
- **输出 key**：`phase_metrics`（list）
- **缺失处理**：缺 `distance_markers` 或无法分 2 段 → `[]` + `no_phase_context` warning
- **MVP 报告**：⚠️ 高级对比视图，MVP 可选

### E.3 `time_series`
- **输出**：`{body_angle_deg: [{frame, time_sec, value}]}`，逐帧身体倾角
- **MVP 报告**：⚠️ 供趋势曲线展示

---

## F. 质量与缺失处理总表

### F.1 quality.level 判定
- `error`：触发任一错误码 → 核心指标无法计算
  - `missing_fps`：缺有效 fps
  - `insufficient_keypoint_frames`：关键点帧 < 3
  - `missing_core_keypoints`：缺 shoulder/elbow/wrist/hip/knee/ankle（任一前缀）
  - `unsupported_camera_view`：view_type ≠ side
- `warning`：有问题但不致命（如缺 waterline / scale / distance_markers / swim_direction / hand_entry）
- `good`：无警告

### F.2 缺失 → warning 映射
| 缺失项 | warning code | 受影响指标 |
|---|---|---|
| `scale.pixels_per_meter` | `missing_scale` | 所有距离/速度/划幅类 |
| `hand_entry` 事件 | `missing_hand_entry` | 划频/划幅/周期/SWOLF |
| `reference_lines.waterline` | `missing_waterline` | `hip_depth_cm` |
| `distance_markers` | `no_phase_context` | `phase_metrics` / `stroke_length_m`（距离版）/ `average_speed_mps` |
| `swim_direction` | `swim_direction_unset` | `front_reach_distance_cm`（按绝对值，方向未消歧） |

### F.3 `point.visibility` 门控规则
- `visibility == "missing"`：该点在任何帧/计算中**跳过**（几何函数 `_as_xy` 直接返回 None），不参与角度/距离。
- `visible` / `occluded` / `estimated`：MVP 阶段**等同处理**（均参与计算）。`occluded` 的**降权**为语义目标（design 约束 7），具体权重加权实现推迟到 v2；当前不影响数值，仅在后续可据 `visibility` 标注质量。
- 单帧某关键点 missing → 仅该帧涉及该点的指标跳过；其余帧与其余点不受影响，不整体报错。

### F.4 非 side 视角处理
- 端点 `POST /.../calculate-metrics` 在 `view_type != side` 时返回 **422**，附 `UnsupportedCameraView` 说明；`quality.level` 同时记为 `error`（code `unsupported_camera_view`）。

---

## G. 指标 → MVP 报告入场速查

| 指标 | 进 MVP 报告 | 关键度 |
|---|---|---|
| body_angle_deg_avg | ✅ | 关键 |
| hip_depth_cm_avg | ✅（需 waterline） | 关键 |
| streamline_index | ⚠️ 内部数值 | 子分 |
| entry_angle_deg_avg | ⚠️ 可选 | 辅助 |
| front_reach_distance_cm_avg | ✅ | 关键 |
| elbow_angle_deg_avg | ✅ | 关键 |
| forearm_drop_angle_deg_avg | ⚠️ 可选 | 辅助 |
| catch/pull_duration_sec | ✅（需事件） | 关键 |
| knee_angle_deg_avg | ✅ | 关键 |
| hip_angle_deg_avg | ⚠️ 可选 | 辅助 |
| ankle_extension_angle_deg_avg | ⚠️ 近似 | 辅助 |
| kick_frequency_hz | ✅（需事件） | 关键 |
| stroke_rate_spm_avg | ✅ | 关键 |
| stroke_length_m_avg | ✅（需距离标定） | 关键 |
| average_speed_mps | ✅（需距离标定） | 关键 |
| swolf | ✅（需距离标定） | 关键 |
| technical_stability_score | ⚠️ MVP 占位 | 复合 |
| phase_metrics | ⚠️ 可选 | 高级 |
| time_series.body_angle_deg | ⚠️ 趋势 | 辅助 |

---

## H. v2 延期项（明确不在 MVP）
- `body_line_deviation_cm`：身体线偏差，需拟合参考线，定义模糊。
- `kick_amplitude_cm`：打腿幅度，需踝部轨迹密度，标注稀疏时不准。
- `ankle_extension_angle_deg` 待 `foot/toe` 关键点补充后升级为膝-踝-趾三点角。
- `occluded` 点的显式权重降权。
- `streamline_index` / `technical_stability_score` 的教练校准参数（当前为固定 MVP 惩罚系数）。

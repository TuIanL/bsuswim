# Kinematic Visual Artifact Generation — Design

## 1. Context

当前指标引擎已经为视觉生成层提供了主要输入：

```text
AnnotationMetric
├── summary
├── time_series
├── ranges
├── representative_frames
├── source.revision
└── quality

NormalizedAnnotation
├── keypoint_frames
├── annotation_metadata.frame_mapping
├── coordinate_system
└── revision

SessionVideo
└── VideoFile.storage_path
```

`side_2d_kinematics` 当前的代表帧主要选取接近序列中位数的帧，而关键帧图还需要「最小值、最大值、运动尖峰」等展示型选择，因此视觉层必须有独立的 `FrameSelectionPolicy`，不能直接把已有代表帧等同于报告关键帧。

底座已核对（`main` 分支）：

- `side_2d_kinematics` 稳定输出四类指标，key 集见 `calculator.py` 的 `CANONICAL_KEYS`。
- `AnnotationMetric.source_revision` 已存在（nullable），因此本设计显式拒绝 null revision。
- `StorageService.save_bytes()` 已返回 `relative_path` / `absolute_path` / `size_bytes`，但尚不返回 `checksum_sha256`，本设计补充该字段。
- `resolve_frames(keypoint_frames: list[dict]) -> list[CanonicalKinematicFrame]` 是纯函数，无 ORM 耦合，可直接被视觉层复用。
- `reference_body_length.value_px` 已确认（`ReferenceBodyLength` schema）。
- `kick_periodicity.value.score` 已确认封装在 `value` 字典中。
- `arm_extension_ratio` 仅存在于 `summary`（标量均值），逐帧序列仅 `normalized_wrist_trajectory` 存在；`arm_extension_max` 关键帧须从逐帧腕—肩归一化距离派生。

## 2. Goals / Non-Goals

### Goals

```text
一条确定的 AnnotationMetric
        ↓
校验 revision 与输入可用性
        ↓
规划待生成资产
        ↓
提取视频帧 / 读取骨架和指标
        ↓
生成 PNG / SVG
        ↓
保存 ArtifactSet + Artifact rows
        ↓
返回稳定 manifest
```

### Non-Goals

- 不从 session 自动猜选最新 AnnotationMetric；
- 不把「画面水平线」写成「水面线」；
- 不对技术好坏做诊断；
- 不建立运动员等级常模；
- 不产生雷达图总分；
- 不在本阶段把资产写进 `ReportMetadata.report_data`。

## 3. Decision 1：生成入口绑定 AnnotationMetric

采用：

```http
POST /api/annotation-metrics/{annotation_metric_id}/artifacts/generate
GET  /api/annotation-metrics/{annotation_metric_id}/artifacts
```

不采用：

```http
POST /api/normalized-annotations/{id}/generate-artifacts
```

原因是同一标注可以存在 `side_view_metrics`、`side_2d_kinematics`、未来新 calculator、不同 `calculator_version`。视觉资产必须明确指向一条实际指标记录。

支持范围：

```text
calculator = side_2d_kinematics
schema_version = swim-side-kinematics.v1
```

其他 calculator 返回：

```json
{ "code": "unsupported_artifact_metric_schema" }
```

## 4. Decision 2：ArtifactSet + Artifact 两级结构

### `kinematic_artifact_sets`

代表一次完整生成结果：

```python
class KinematicArtifactSet(Base):
    id: int

    annotation_metric_id: int
    normalized_annotation_id: int
    session_video_id: int

    schema_version: str = "swim-kinematic-artifacts.v1"

    generator: str = "kinematics_visuals"
    generator_version: str = "1.0.0"
    style_profile: str = "kinematics_report_light_v1"

    source_annotation_revision: int
    source_metric_schema_version: str
    source_metric_calculator: str
    source_metric_calculator_version: str
    source_metric_hash: str

    generation_signature: str
    status: str            # generating / ready / partial / failed

    manifest: dict
    warnings: list

    created_by: int | None
    created_at: datetime
    updated_at: datetime
```

唯一约束：

```text
UNIQUE(annotation_metric_id, generation_signature)
```

### `kinematic_artifacts`

```python
class KinematicArtifact(Base):
    id: int
    artifact_set_id: int

    artifact_key: str
    artifact_type: str
    module_key: str
    metric_keys: list[str]

    status: str            # ready / skipped / failed

    annotation_frame: int | None
    source_video_frame: int | None

    annotation_frame_range: dict | None
    source_video_frame_range: dict | None

    storage_path: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    size_bytes: int | None
    checksum_sha256: str | None

    skip_reason: str | None
    metadata: dict
```

唯一约束：

```text
UNIQUE(artifact_set_id, artifact_key)
```

生成器版本和标注 revision 存在 ArtifactSet 中，但 API manifest 展开到每个 artifact，满足每个资产均具备完整追溯信息，同时避免数据库重复列。

## 5. Decision 3：Artifact manifest

API 返回结构：

```json
{
  "schema_version": "swim-kinematic-artifacts.v1",
  "artifact_set_id": 41,
  "annotation_metric_id": 27,
  "normalized_annotation_id": 16,
  "source_annotation_revision": 3,
  "source_metric": {
    "schema_version": "swim-side-kinematics.v1",
    "calculator": "side_2d_kinematics",
    "calculator_version": "1.0.0",
    "hash": "sha256..."
  },
  "generator": {
    "name": "kinematics_visuals",
    "version": "1.0.0",
    "style_profile": "kinematics_report_light_v1"
  },
  "status": "partial",
  "artifacts": [
    {
      "artifact_key": "body_posture.keyframe.body_axis_min",
      "artifact_type": "annotated_keyframe",
      "module_key": "body_posture",
      "metric_keys": ["body_axis_angle_deg"],
      "annotation_frame": 18,
      "source_video_frame": 49,
      "frame_range": null,
      "storage_path": "kinematic-artifacts/27/r3/.../body_axis_min.png",
      "url": "/uploads/kinematic-artifacts/27/r3/.../body_axis_min.png",
      "mime_type": "image/png",
      "width": 1600,
      "height": 900,
      "checksum_sha256": "...",
      "source_annotation_revision": 3,
      "generator_version": "1.0.0",
      "status": "ready",
      "presentation": {
        "title": "身体最接近水平关键帧",
        "label": "相对画面水平线",
        "value": "4.8°",
        "caption": "该角度基准为画面水平线，并非水面线。"
      }
    }
  ],
  "warnings": []
}
```

### 不只保存 `frame_index`

必须同时保存：

```text
annotation_frame
source_video_frame
```

时序图必须同时保存：

```text
annotation_frame_range
source_video_frame_range
frame_basis
mapping_status
```

## 6. Decision 4：资产类型与稳定 key

### 6.1 骨架叠加关键帧

`artifact_type`：`annotated_keyframe`

候选 key：

```text
body_posture.keyframe.body_axis_min
body_posture.keyframe.body_axis_max

upper_limb.keyframe.left_elbow_min
upper_limb.keyframe.left_elbow_max
upper_limb.keyframe.right_elbow_min
upper_limb.keyframe.right_elbow_max
upper_limb.keyframe.arm_extension_max

lower_limb.keyframe.left_knee_min
lower_limb.keyframe.left_knee_max
lower_limb.keyframe.right_knee_min
lower_limb.keyframe.right_knee_max

head_trunk.keyframe.head_motion_spike
```

其中：

- 肘角越小表示当前二维几何中的屈曲程度更大；
- 膝角同理；
- 不直接写「技术正确/错误」；
- 关键帧标题描述客观状态。

### 6.2 关节角时序图

```text
body_posture.chart.angle_timeseries
upper_limb.chart.elbow_angle_timeseries
lower_limb.chart.knee_angle_timeseries
```

内容：

```text
身体图：torso_axis_angle_deg、body_axis_angle_deg
上肢图：left_elbow_angle_deg、right_elbow_angle_deg
下肢图：left_knee_angle_deg、right_knee_angle_deg
```

### 6.3 关节轨迹图

```text
upper_limb.chart.joint_trajectories
body_posture.chart.hip_trajectory
lower_limb.chart.joint_trajectories
```

### 6.4 运动范围比较图

```text
overview.chart.range_comparison
```

### 6.5 稳定性雷达图

```text
overview.chart.stability_radar
```

标题必须固定为：`当前片段运动稳定性概览`

## 7. Decision 5：关键帧选择策略

新增：

```python
class FrameSelectionPolicy:
    def select(self, metrics, annotation) -> list[SelectedFrame]:
        ...
```

选择顺序：

1. 从对应 `time_series` 中选择最小值、最大值或尖峰；
2. 对同值按照较高 confidence 优先；
3. 再按照较早 source frame 保证结果稳定；
4. 如果时序不存在，回退到 `representative_frames`；
5. 如果 source-video mapping 未验证，保留 selection 记录，但不生成视频关键帧。

不得随机选帧。

完整序列用于选择关键帧，图表显示可以下采样。

`arm_extension_max` 关键帧：以 `arm_extension_ratio` 作为展示语义，从逐帧腕—同侧肩归一化距离（`normalized_wrist_trajectory` 或几何派生）取最大值对应的帧，在 artifact metadata 中记录 `selected_side` 与 `selection_formula_id`。

参考体长可用（`available` / `low_confidence`）时：使用腕—肩距离除以 `reference_body_length.value_px` 选择最大帧。参考体长 `unavailable` 时：使用原始腕—肩像素距离选择同一片段最大帧（分母在同一片段为常数，不改变最大帧排序，但结果**不得写成归一化比例**），记录 `metadata.selection_basis = pixel_distance_fallback` 并追加 `reference_body_length_unavailable` warning，不展示 `arm_extension_ratio` 数值。

头部运动尖峰帧：现有 `head_motion_spike_frames` 仅输出候选帧列表（`value=[...]`）与 `spike_count`，不含逐尖峰速度值。视觉层须回源 `CanonicalKinematicFrame` 重建 `head_center.y`，计算相邻帧绝对垂直速度，在**已检测的尖峰候选帧**中选择绝对垂直速度最大者（公式 id `max_abs_head_vertical_velocity_among_detected_spikes.v1`），并在 metadata 记录尖峰速度与公式。若无检测到尖峰：该关键帧标记 `skipped`，`skip_reason = metric_unavailable`，**不得回退到任意头部帧**。

## 8. Decision 6：视频帧提取门禁

关键帧图片只有满足以下条件才生成：

```text
AnnotationMetric.source_revision == NormalizedAnnotation.revision
frame_mapping.verified == true
source_video_frame != null
VideoFile.storage_path 存在且可读取
```

错误处理：

| 情况 | 行为 |
| --- | --- |
| metric revision stale | 整体返回 409 |
| source revision missing | 返回 422 |
| mapping unverified | 跳过关键帧，图表继续 |
| 视频不存在 | 跳过关键帧，图表继续 |
| 某一个 frame 无法解码 | 单资产 failed，其余继续 |
| 全部资产不可生成 | ArtifactSet = failed |

`force=true` 不允许绕过 stale revision，必须先重新计算指标。

关键帧是报告证据，视频帧提取必须返回精确帧，不容忍长 GOP 跳到相邻帧。`VideoFrameExtractor` SHALL 返回 `requested_frame`、`decoded_frame`、`exact_match`；当 `exact_match == false` 时该帧标记 `failed`（`skip_reason = video_decode_failed`）。实现须带关键帧间隔测试视频验证。若 OpenCV 无法稳定满足 exact frame，可切换到 FFmpeg 或 PyAV 实现，但接口契约不变。

## 9. Decision 7：图像处理技术方案

新增依赖：`opencv-python-headless`、`matplotlib`、`numpy`。

```text
OpenCV：视频随机帧提取、图像缩放裁切、骨架点和连线、身体轴线、关节角弧线、PNG 输出
Matplotlib Agg：时序图、轨迹图、范围图、雷达图、SVG 输出
```

不提交或打包字体文件。

字体策略：系统存在 CJK 字体则图内使用中文；否则图内使用英文短标签，中文标题和说明保留在 `manifest.presentation`。

图表输出为 SVG，关键帧输出为 PNG：

```text
annotated frame: 1600 × 900 PNG
chart: 1200 × 675 SVG
radar: 900 × 900 SVG
```

## 10. Decision 8：骨架叠加规则

绘制内容：

```text
原始画面 + COCO17 骨架连线 + 关键关节点 + 当前指标对应关节角
       + 身体轴线或关节射线 + 当前客观指标值
```

可见性样式：

```text
visible   → 实线和实心点
occluded  → 较低透明度
estimated → 虚线或空心点
missing   → 不绘制
```

关键帧裁切：获取当前帧所有有效骨架点 bbox → 向四周扩展 15% → 限制在源图像边界 → 保持输出宽高比 → 变换所有骨架坐标后绘制。

如果骨架坐标超出源视频尺寸且无法确定转换比例：`status = skipped`，`skip_reason = coordinate_space_mismatch`。系统不得静默猜测缩放比例。

**统一坐标来源**：Decision 8 的骨架叠加渲染器与 Decision 9 的轨迹渲染器**共用同一个 `KinematicFrameSequenceProvider`**（见 Decision 9），不得各自重新实现 bilateral midpoint 或 side-proxy fallback 逻辑。这样保证：

```text
calculator 的角度
= 关键帧叠加的身体轴
= 轨迹图的中点
```

不会因三套独立实现产生漂移。

## 11. Decision 9：Cartesian 轨迹统一回源 annotation 几何

所有腕、肘、髋、膝、踝的 **Cartesian 轨迹图** SHALL 从 `NormalizedAnnotation.keypoint_frames` 的确切 source revision 重建。生成器 SHALL 使用与 `side_2d_kinematics` calculator 相同的 `CanonicalKinematicFrame` resolver（`resolve_frames`），不得独立重新实现 bilateral midpoint 或单侧 fallback 规则。

`AnnotationMetric.time_series` 仍是标量指标图（角度、速度、ROM、周期性）的权威来源，但不要求它包含关节坐标序列。

新增只读适配器（不直接操作 ORM）：

```python
class KinematicFrameSequenceProvider:
    def build(self, annotation: NormalizedAnnotation) -> list[CanonicalKinematicFrame]:
        ...
```

指标 calculator 与 artifact generator 都调用同一套 `resolve_frames`，保证 `hip_mid` 等合成点在三处一致。

### Upper limb

- left wrist / elbow 相对 left shoulder
- right wrist / elbow 相对 right shoulder

### Body posture

- hip_mid 相对首个有效 hip_mid
- hip_mid 须保留其 construction_mode（bilateral_midpoint / left_proxy / right_proxy / unavailable）

### Lower limb

- left/right knee 与 ankle 相对 hip_mid

坐标优先除以 `reference_body_length.value_px`，单位 `body length ratio`；参考体长不可用时允许回退像素（`unit = px`，`availability = degraded`）。图中 y 轴转换为向上为正，并明确标注 `athlete-relative coordinate`。

轨迹图同时消费 `KinematicFrameSequenceProvider`，与 Decision 8 关键帧共享 resolver。

## 12. Decision 10：运动范围图禁止混用单坐标轴

原始需求包含：

```text
肘 ROM：deg
膝 ROM：deg
头部波动：px
髋部波动：px
身体角度范围：deg
```

不得把这些原值放在一个统一 y 轴上。采用三块 small-multiple：

```text
A. 关节 ROM（deg）：左肘、右肘、左膝、右膝
B. 垂直波动：头部、髋部，优先转换为 body-length percentage，否则使用 px
C. 身体轴角度范围（deg）：P05、P95、range
```

不得把它们归一化成所谓「能力评分」。

## 13. Decision 11：雷达图是展示指数，不是技术评分

标题固定：`当前片段运动稳定性概览`

五个轴：

```text
身体姿态稳定性
上肢运动稳定性
下肢节奏稳定性
头部控制稳定性
数据完整度
```

manifest 必须包含：

```json
{
  "semantics": "within_clip_visualization_only",
  "overall_score": null,
  "disclaimer": "仅用于当前片段内部运动稳定性展示，不代表经过验证的综合技术评分。",
  "index_method_version": "stability-display-index.v1"
}
```

每个轴必须保存：`display_value`、`source_metric_keys`、`source_raw_values`、`formula_id`、`availability`。

第一版转换配置采用独立配置文件，**必须包含可执行的映射参数**（原始值→0–100 的缩放、输入权重、方向、soft_cap、minimum_available_inputs）：

```text
backend/app/services/kinematic_artifacts/config/stability_display_index_v1.yaml
```

示例（实际数值以配置文件为准）：

```yaml
schema_version: stability-display-index.v1
axes:
  body_posture:
    formula: weighted_inverse_clamped
    minimum_available_inputs: 1
    inputs:
      posture_stability_cv: { weight: 0.6, direction: lower_is_more_stable, soft_cap: 0.30 }
      body_angle_std_deg:   { weight: 0.4, direction: lower_is_more_stable, soft_cap: 12.0 }
  upper_limb:
    formula: weighted_inverse_clamped
    minimum_available_inputs: 1
    inputs:
      elbow_angle_smoothness:  { weight: 0.6, direction: lower_is_more_stable, soft_cap: 20.0 }
      valid_sample_continuity: { weight: 0.4, direction: higher_is_more_stable, min: 0, max: 1 }
  lower_limb_rhythm:
    formula: weighted_direct
    minimum_available_inputs: 1
    inputs:
      kick_periodicity_score: { weight: 0.8, direction: higher_is_more_stable, min: 0, max: 1 }
      continuity_factor:      { weight: 0.2, direction: higher_is_more_stable, min: 0, max: 1 }
  head_control:
    formula: weighted_inverse_clamped
    minimum_available_inputs: 1
    inputs:
      trunk_vertical_stability: { weight: 0.5, direction: higher_is_more_stable, min: 0, max: 1 }
      head_excursion:           { weight: 0.3, direction: lower_is_more_stable, soft_cap: 0.15 }
      spike_ratio:              { weight: 0.2, direction: lower_is_more_stable, soft_cap: 0.30 }
  data_completeness:
    formula: direct
    inputs:
      valid_keypoint_ratio: { direction: higher_is_more_stable, min: 0, max: 1 }
      available_metric_ratio: { direction: higher_is_more_stable, min: 0, max: 1 }
      mapping_verified: { direction: higher_is_more_stable }
```

原则：

- 身体姿态轴来源于 `posture_stability_cv` 和 `body_angle_std_deg`；
- 上肢轴来源于左右肘角时序平滑性和有效样本连续度；
- 下肢轴来源于 `kick_periodicity.value.score` 与序列连续度（读取 `summary["kick_periodicity"]["value"]["score"]`，`value=None` 时轴显示 N/A，不得回填 0）；
- 头部轴来源于 `trunk_vertical_stability`、头部波动和尖峰比例；
- 数据完整度来源于有效关键点、可用 metric 比例和 mapping 状态；
- 无有效来源时显示 N/A，不得用 0 伪装成表现差；
- `soft_cap` 与缩放参数仅为片段内展示的可视化缩放，**不是运动员优秀/合格/不合格阈值**；
- 部分输入缺失时按剩余输入权重重新归一化（仍受 `minimum_available_inputs` 约束）；
- 不计算五轴平均分；
- 不设置优秀、合格、不合格阈值。

雷达图 N/A 绘制规则：

```text
可用轴 < 3           → 不生成雷达图，skip_reason = radar_inputs_insufficient
可用轴 ∈ [3, 4]      → 绘制 5 根轴；缺失轴标签显示 N/A；缺失轴不放置数值点；
                       不填充雷达面积，仅绘制可用点与虚线段
可用轴 = 5           → 可绘制闭合折线与半透明填充
```

## 14. Decision 12：生成签名与幂等

```text
generation_signature = SHA256(canonical_json({
    annotation_metric_id,
    source_annotation_revision,
    source_metric_hash,
    source_video_checksum,
    generator_version,
    artifact_plan_version,
    style_profile,
    style_profile_hash,
    stability_index_config_hash,
}))
```

其中 `source_video_checksum` 来自 `VideoFile.checksum_sha256`，`style_profile_hash` 与 `stability_index_config_hash` 为对应配置文件内容的 SHA-256。`source_metric_hash` 与签名本身都使用固定 canonical JSON 序列化，禁止直接对 Python `str(dict)` 哈希：

```python
canonical_json = json.dumps(
    payload, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False, allow_nan=False,
)
sha256(canonical_json.encode("utf-8")).hexdigest()
```

规则：

```text
相同 signature + force=false → 返回已有 ArtifactSet
相同 signature + force=true  → 原地重新生成同一 ArtifactSet（唯一约束禁止新建第二个）
不同 signature                → 生成新的 ArtifactSet
```

文件路径：

```text
kinematic-artifacts/{annotation_metric_id}/r{source_annotation_revision}/{signature前12位}/{artifact_key}.{png|svg}
```

文件名不包含运动员姓名、原视频文件名或其他个人信息。

`force=true` 原地再生流程（唯一约束保证只有一个 Set）：

```text
SELECT ArtifactSet FOR UPDATE
  → status = generating
  → 资产渲染到临时文件 body_axis_min.png.tmp-{uuid}
  → 全部单资产生成结束
  → os.replace(temp_path, final_path) 原子替换
  → 删除 obsolete Artifact rows 并重建
  → 重建 manifest
  → status = ready / partial / failed
```

关键约束：

- 不能一开始就覆盖旧文件，否则生成中途失败会破坏原本可用的资产；
- 旧的 ready manifest 与文件须保留到本次再生 finalization 完成；
- 并发 force 请求通过 `FOR UPDATE` 行锁串行化；
- 再生失败须保留上一版可用资产，新 attempts 标记 failed。

## 15. Decision 13：部分成功

ArtifactSet 状态：

```text
ready:    所有计划中的可生成资产均成功
partial:  至少一个资产成功，且存在 skipped 或 failed
failed:   没有任何 ready 资产，或出现系统性失败
generating: 生成进行中
```

结构化原因码：

```text
metric_unavailable
insufficient_series_points
metric_revision_stale
frame_mapping_unverified
source_video_missing
source_frame_missing
video_decode_failed
coordinate_space_mismatch
reference_body_length_unavailable
radar_inputs_insufficient
render_failed
```

### manifest 与 Artifact rows 的权威关系

```text
生成过程中：KinematicArtifact rows 是工作状态（source of truth）
生成完成时：根据最终 Artifact rows 构建 manifest snapshot
离开 generating 后：manifest 与 rows 均视为不可变
force 重新生成：重新进入 generating，完成后同时替换 rows 与 manifest
```

为避免双份信息漂移：

- `KinematicArtifactSet.manifest` 是最终快照，由 Artifact rows 稳定排序投影生成；
- 增加 `manifest_sha256` 列记录快照校验和；
- API 返回持久化 manifest snapshot，不直接从 rows 即时重建；
- 测试必须断言 `manifest.artifacts == Artifact rows 的稳定排序投影`。

## 16. Decision 14：存储与 URL

数据库只存相对路径：

```text
kinematic-artifacts/27/r3/abc123/body_axis_min.png
```

不得存 `/Users/xxx/project/uploads/...`。

API 动态生成：

```text
/uploads/kinematic-artifacts/27/r3/abc123/body_axis_min.png
```

`StorageService.save_bytes()` SHALL 执行路径安全校验，拒绝路径逃逸：

```python
root = self.upload_dir.resolve()
destination = (root / relative_path).resolve()

if Path(relative_path).is_absolute():
    raise UnsafeStoragePath()
if not destination.is_relative_to(root):
    raise UnsafeStoragePath()
# 同时拒绝：空路径段、.. 上溯、NUL 字符、符号链接逃逸
```

返回：

```json
{
  "relative_path": "...",
  "absolute_path": "...",
  "size_bytes": 182033,
  "checksum_sha256": "...",
  "mime_type": "image/png"
}
```

`checksum_sha256 = hashlib.sha256(data).hexdigest()`。`absolute_path` 仅在服务内部使用，不进入 API manifest。

SVG 资产的 `width` / `height` 定义为逻辑尺寸（`unit = css_px`），SVG 自身须写入 `viewBox` 与 `width` / `height` 属性，便于前端与 Playwright PDF 稳定排版。

## 17. Decision 15：与现有报告前端兼容

本 Change 不修改报告构建器，但每个 artifact 保存一个 `presentation` 投影：

```json
{
  "title": "右膝最大屈曲关键帧",
  "label": "右膝关节角",
  "value": "112.4°",
  "caption": "基于髋—膝—踝三点二维夹角。",
  "report_asset_type": "annotated_frame"
}
```

未来报告构建器可直接转换成现有前端的 `ReportAsset`（`image` / `annotated_frame` / `video_clip`）。现有前端已具备上述资产接口和 `<img>` 展示能力。

## 18. Decision 16：性能边界

- 关键帧最多生成 12 张；
- 时序图每条曲线最多显示 600 个点；
- 轨迹图每条轨迹最多显示 800 个点；
- 选择 extrema 使用完整数据，不使用下采样数据；
- 视频不整体加载到内存；
- 所有目标 source frame 排序后统一提取；
- 同一 source frame 在一次生成中只解码一次；
- Matplotlib 使用 Agg 后端；
- CPU 渲染通过线程池执行，不阻塞异步事件循环。

## 19. Decision 17：复用 resolver 的一致性要求

`KinematicFrameSequenceProvider` 是 renderer 与 calculator 之间唯一的骨架重建入口。禁止在渲染器内重新实现：

- `_build_bilateral`（bilateral midpoint 构造）
- 单侧 proxy fallback 规则
- visibility / construction_mode 解析

测试须验证：provider 输出与 calculator 内部的 canonical frames 完全一致（key 名、坐标、mode）。

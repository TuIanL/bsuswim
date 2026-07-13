## Context

当前系统仅支持 Kinovea 标注导入。Kinovea parser 产出 `ParsedKinoveaAnnotation`（含 events、keypoint_frames、trajectories、manual_tags），经由 `parse_annotation_file()` 写入 `NormalizedAnnotation`。后续 metrics → diagnostics → report 链路均读取 `NormalizedAnnotation`。

标注工具已切换到 CVAT，其 Task XML 格式仅输出 COCO 17 点骨架关键点，不含划水事件、轨迹或人工标签。同时当前 `NormalizedAnnotation` 的帧时间语义模糊——单个 `frame_count` 和 `fps` 无法区分原视频帧、标注任务帧和有标注帧。需要引入 CVAT parser 并借此厘清时间轴、覆盖范围和可见性语义。

设计原则：
- Parser 只负责忠实提取，不做数据推导
- 派生数据（trajectories、centers）由独立 Builder 层完成
- Metrics 层以 `timestamp_sec` 为唯一权威时间源
- 变更尽量向后兼容，`swim-annotation.v1` 继续支持
- NormalizedAnnotation 是唯一稳定的下游观测边界

## Goals / Non-Goals

**Goals:**
- 支持上传和解析 CVAT Task XML 骨架标注文件
- 在 parse 链路中自动完成轨迹推导
- 为每个 keypoint_frame 建立 `annotation_frame → source_video_frame → timestamp_sec` 时间映射
- 将 `visibility` 语义落地到 `KeypointPoint`（visible / occluded / missing / estimated）
- 质量系统按 `source=cvat` 按指标级声明可用性（角度/轨迹可用，速度/划频/距离因缺事件或标尺 blocked）
- schema_version 升级到 `swim-annotation.v2`

**Non-Goals:**
- 不删除 Kinovea parser 或破坏现有 `swim-annotation.v1` 兼容性
- 不实现骨架 → 划水事件的自动推导算法
- 不做轨迹插值、平滑或卡尔曼滤波
- 不修改 metrics 层的核心计算逻辑，只改造时间源接入方式
- 不支持 CVAT 视频帧级标签（Tag）解析（events 和 tags 后续阶段添加）
- 不支持 ZIP bundle 上传（MVP 使用独立 annotation_file）

## Decisions

### D1: Parse pipeline 结构

```
POST /api/annotations/{id}/parse
  │
  ├─ source == "cvat"?
  │   │
  │   ├─ CvatXmlParser.parse(file_path)
  │   │   → ParsedCvatAnnotation.raw_keypoint_frames
  │   │     (无时间戳，无轨迹，纯忠实提取)
  │   │
  │   ├─ FrameMappingResolver.resolve(
  │   │     cvat_meta, json_manifest, video_meta,
  │   │     user_provided_override    ← ParseAnnotationOptions
  │   │   ) → FrameMapping
  │   │
  │   ├─ CvatAnnotationNormalizer.normalize(
  │   │     raw_keypoint_frames, frame_mapping
  │   │   ) → KeypointFrame[]
  │   │     (带 annotation_frame / source_video_frame / timestamp_sec)
  │   │
  │   └─ AnnotationDerivedDataBuilder.build(keypoint_frames)
  │       → trajectories + visibility_summary
  │
  ├─ source == "kinovea"?
  │   └─ 现有 Kinovea parser 链路不变
  │
  └─ quality_check → NormalizedAnnotation
```

**Rationale**: 各层职责完全正交。Parser 只做 XML 结构提取，不碰时间映射。Normalizer 负责注入时间信息。Builder 只依赖已标准化的 KeypointFrame。任何一层都可以被其他 source 复用。

### D2: CVAT XML Parser — 文件组织

新建 `backend/app/services/parsers/cvat_xml.py`，使用 `xml.etree.ElementTree.iterparse`（streaming 模式避免 DOM 加载大文件）。

核心函数：
- `parse_cvat_xml(file_path) -> ParsedCvatAnnotation`
- `_extract_meta(root) -> CvatMeta` — 读 `<meta>` 中的 job 信息、标签定义、图片尺寸
- `_extract_tracks(root) -> list[RawSkeleton]` — streaming 遍历 `<track>`，提取 skeleton + points
- `_aggregate_by_frame(skeletons) -> list[RawCvatKeypointFrame]` — 按 frame 分组，验证单帧多 skeleton 约束
- `_reject_multiple_active(skeletons_in_frame) -> None` — 某帧 >1 个有效 skeleton 时阻止 parse

`ParsedCvatAnnotation` 包含：
- `raw_keypoint_frames: list[RawCvatKeypointFrame]`
  - 每个 RawCvatKeypointFrame 含 `{annotation_frame, points{dict[str, RawCvatPoint]}, source_track_ids: list[str]}`
  - 无 `source_video_frame`，无 `timestamp_sec`，无 `image_name`
- `native_metadata: CvatNativeMeta`（序列帧范围、标签定义、图片尺寸）
- `warnings: list[str]`

**关键规则**：同一 frame 出现两个以上 `outside=0` 的 skeleton 时，不自动合并，直接阻止 parse 并记录 `MULTIPLE_ACTIVE_SKELETONS` error。当前 MVP 只支持 single-subject 模式。

### D3: FrameMappingResolver — 时间映射解析

新建 `backend/app/services/parsers/frame_mapping.py`。

输入：
- CVAT meta（start_frame、stop_frame）
- JSON frame manifest（可选 companion annotation_file，提供图片文件名 → 帧号映射）
- session_video.video_file 元数据（fps、原视频帧数）
- `ParseAnnotationOptions.frame_mapping_override`（用户显式确认）

输出 `FrameMapping`：
```python
class FrameMapping(BaseModel):
    mode: Literal["explicit", "affine", "identity", "unknown"]
    verified: bool
    source_frame_offset: int | None = None
    source_frame_stride: int | None = None
    video_fps: float | None = None
    entries: list[FrameMappingEntry] | None = None  # explicit mode

class FrameMappingEntry(BaseModel):
    annotation_frame: int
    source_video_frame: int | None = None
    timestamp_sec: float | None = None
    image_name: str | None = None
```

`verified` 的赋值规则：
- 用户通过 `ParseAnnotationOptions.frame_mapping_override.confirmed = true` 显式确认 → `verified = true`
- `extraction_manifest` 包含逐帧 `source_video_frame` → `verified = true`
- 文件名连续推断出 `affine` → `verified = false`，验证理由记录为 `inferred_from_filename_sequence`
- 无法推断 → `unknown`，`verified = false`

**不允许**：仅凭文件名连续自动标注 `verified = true`。

#### ParseAnnotationOptions

parse endpoint 增加可选请求体：

```python
class ParseAnnotationOptions(BaseModel):
    companion_annotation_file_id: int | None = None
    frame_mapping_override: FrameMappingOverride | None = None
    analysis_ranges: list[AnalysisRange] = []

class FrameMappingOverride(BaseModel):
    mode: Literal["affine", "identity"]
    source_frame_offset: int | None = None
    source_frame_stride: int | None = None
    confirmed: bool = False
```

### D4: CvatAnnotationNormalizer

新建 `backend/app/services/parsers/cvat_normalizer.py`（或放在 `parsers/` 包内）。

职责：
- 接收 `RawCvatKeypointFrame[]` + `FrameMapping`
- 为每个 frame 注入 `source_video_frame`、`timestamp_sec`、`image_name`
- 输出标准 `KeypointFrame[]`
- 不做坐标变换、不做重采样、不做插值

```python
class CvatAnnotationNormalizer:
    @staticmethod
    def normalize(
        raw_frames: list[RawCvatKeypointFrame],
        mapping: FrameMapping,
    ) -> list[KeypointFrame]:
        ...
```

### D5: AnnotationDerivedDataBuilder

新建 `backend/app/services/annotation_derivation/` 目录，包含：

```
annotation_derivation/
├── __init__.py
├── builder.py              # AnnotationDerivedDataBuilder — 编排入口
├── trajectory_builder.py   # 从 keypoint_frames 串轨迹
├── body_center_builder.py  # 计算髋部中点（作为派生轨迹）
└── visibility_summary.py   # 统计关键点覆盖率
```

`builder.py`:
```python
class AnnotationDerivedDataBuilder:
    def build(self, keypoint_frames: list[KeypointFrame]) -> DerivedData:
        trajectories = TrajectoryBuilder.build(keypoint_frames)
        center_trajs = BodyCenterBuilder.build(keypoint_frames)
        trajectories.extend(center_trajs)
        visibility = VisibilitySummary.build(keypoint_frames)
        return DerivedData(trajectories=trajectories, visibility=visibility)
```

`BodyCenterBuilder` 输出派生轨迹（不新增顶层字段）：
```json
{
  "point_name": "hip_center",
  "source": "derived_from_keypoints",
  "samples": [...]
}
```

规则：双髋同时 visible 时计算 midpoint；单侧髋可见时本帧 skip，不制造估算中点；双髋不可见时本帧 skip。

Builder 由 `normalized_annotation_service.py` 的 `parse_annotation_file()` 调用，在 quality check 之前执行。异常捕获后降级为 warning 不阻止 parse。

### D6: KeypointPoint schema

```python
class KeypointPoint(BaseModel):
    x: float | None = None
    y: float | None = None
    visibility: Literal["visible", "occluded", "missing", "estimated"] = "visible"
    confidence: float | None = None

    @model_validator(mode="after")
    def validate_coordinate_visibility(self):
        if self.visibility == "missing":
            if self.x is not None or self.y is not None:
                raise ValueError("missing point must not contain coordinates")
        else:
            if self.x is None or self.y is None:
                raise ValueError("visible, occluded or estimated point requires coordinates")
        return self
```

- `estimated` 保留但不推荐使用（deprecated），确保 v1 数据中 `visibility: "estimated"` 可读
- CVAT 来源 `confidence` 统一设为 `null`，不自动派生
- `observation_weight` 由 quality/metrics 层派生，不伪造原始 confidence

### D7: NormalizedAnnotation 元数据存储

统一存入现有 `annotation_metadata` JSONB 列，结构为：

```json
{
  "video": { "fps": 60.0, "frame_count": 10800, "duration_sec": 180.0 },
  "annotation_sequence": { "frame_count": 356, "start_frame": 0, "end_frame": 355 },
  "frame_mapping": { "mode": "affine", "verified": false, ... },
  "annotation_coverage": { "annotated_frame_count": 56, "annotated_ranges": [...] },
  "analysis_ranges": [ { "start_annotation_frame": 0, "end_annotation_frame": 55 } ]
}
```

不新增独立 SQL 列。理由：
- 这些元数据按整份 annotation 整体读取，无独立 SQL 层过滤需求
- 避免迁移、避免 ORM 膨胀、避免每扩展字段就改表
- 未来如需查询（如 `frame_mapping.verified=false`），用 JSON expression index

### D8: AnnotationSource 枚举扩展

```python
class AnnotationSource(str, PyEnum):
    KINOVEA = "kinovea"
    DARTFISH = "dartfish"
    MANUAL_JSON = "manual_json"
    AI_POSE = "ai_pose"
    CVAT = "cvat"
    UNKNOWN = "unknown"
```

SQLAlchemy Enum 存储为字符串，添加 `cvat` 不需数据库迁移。

### D9: 文件类型支持

`annotation_file_service.py` 中 `.xml` 已在 `ALLOWED_FILE_EXTENSIONS` 中：

```python
".xml": "xml",
```

上传时 `source = AnnotationSource.CVAT` 且 `file_type = "xml"` 即可路由到 CVAT parser。companion JSON 以独立 `AnnotationFile` 上传，通过 `ParseAnnotationOptions.companion_annotation_file_id` 关联。

### D10: 指标级可用性矩阵

不按大模块笼统声明 availability。改为按具体计算指标声明依赖：

| 指标 | 必需条件 |
|------|---------|
| elbow_angle_deg, knee_angle_deg | 对应关键点 visible |
| body_axis_angle | 肩、髋关键点 |
| hip_depth_px | 髋点 |
| hip_depth_cm | 髋点 + waterline + scale |
| wrist_trajectory_shape | 连续 wrist 关键点 |
| wrist_speed_px_per_s | 关键点 + timestamp_sec |
| wrist_speed_m_per_s | 关键点 + timestamp_sec + scale |
| stroke_cycle_duration | cycle 边界事件 + timestamp_sec |
| stroke_rate | cycle 边界事件 + timestamp_sec |
| stroke_length | cycle 边界 + scale |
| swolf | distance + time + stroke_count |

指标 availability 聚合为模块 readiness：
- 所有核心指标可用 → `ready`
- 部分指标可用 → `degraded`（含可用的子集清单）
- 核心指标均不可用 → `blocked`

例如 `source=cvat` 无 events 无 scale 但有 timestamp_sec：
- `elbow_angle_deg` → ready
- `wrist_trajectory_shape` → ready
- `wrist_speed_px_per_s` → ready（有 timestamp）
- `wrist_speed_m_per_s` → blocked（缺 scale）
- `stroke_rate` → blocked（缺 cycle 边界）
- `hip_depth_cm` → blocked（缺 waterline + scale）

quality profile 根据 `source` 条件化计算。

### D11: v1/v2 时间源兼容

```
swim-annotation.v2 + mapping verified   → 使用 timestamp_sec
swim-annotation.v2 + mapping unverified  → 禁止回退到 frame/fps
                                          时间类指标 blocked
swim-annotation.v1                       → 继续使用 frame/fps 兼容计算
```

### D12: XML 上传安全

- 使用 `xml.etree.ElementTree.iterparse` 避免 DOM 全加载
- 拒绝包含 DTD 或实体声明的 XML（`defusedxml` 或手动检查）
- 最大上传大小：50 MB（复用现有限制）
- 最大 track 数：200
- 最大帧数：10000
- 最大单帧关键点：150
- 坐标值拒绝 NaN、Infinity、负数（允许 0）
- warning 收集上限：100 条，超限截断

### D13: Alembic 迁移

- 不需要为元数据新增列——统一使用 `annotation_metadata` JSONB
- `AnnotationSource` 枚举存储为字符串，`cvat` 值直接可用
- `KeypointPoint` schema 变更是 Pydantic 层，不需要迁移

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| frame_mapping 模式不可靠 | 时间类指标系统性偏移 | 默认 `unknown`，仅用户确认或 manifest 驱动 `verified=true` 才开启时间类指标 |
| CVAT 多人标注（同一帧 >1 skeleton） | parse 被阻止 | MVP single-subject 模式；多人场景单独 Change |
| XML 大文件解析性能 | 长耗时 API 请求 | streaming iterparse，设置数量上限 |
| v1 visibility=estimated 向后兼容 | old data rejected | 保留 `estimated` 在 Literal 中，不删除 |
| Builder 异常 | 下游 metrics 拿到不完整数据 | Builder 异常时 quality 记录 `derivation_failed`，metrics 层检查 quality 决定是否计算 |
| JSON companion 与 XML 不匹配（不同 session_video） | 错误关联数据 | parse 时验证两者归属同一 session_video |

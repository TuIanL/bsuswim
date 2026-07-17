## Context

当前代码已具备完整的 CVAT Skeleton XML 解析 → 帧映射解析 → 标准化标注 → 质量验证链路。但以下数据契约问题直接影响后续指标的正确性：

**帧映射真值漏洞**：`_resolve_explicit()` 只要 manifest entries 非空就返回 `verified=True`，而 service 层构造 manifest 时对 companion JSON 的 `images[]` 只提取了 `annotation_frame` 和 `image_name`，`source_video_frame` 和 `timestamp_sec` 全为 None。结果：只有文件名序列的 companion JSON 产生 `mode=explicit, verified=true` 的映射，时间类指标虚警通过。

**帧计数混用**：service 层 `frame_count = len(keypoint_frames)` 把有效标注帧数写入了本应是视频总帧数的顶层字段。旁边已有 `video_frame_count`（来自 video_file）和 CVAT task size（来自 XML `<job><size>`），但选择了错误的值。

**覆盖率范围伪造**：没有 `analysis_ranges` 时使用 `[{"start_frame": 0, "end_frame": annotated_frame_count - 1}]` 代替真实 annotation_frame 推导的区间。稀疏标注会被错误表示为完整连续区间。

**Quality checker 漏判**：`check_frame_mapping()` 只检查 `affine/identity + false`，`explicit + false` 和 `unknown + false` 均静默通过。

**Parser 性能与安全**：`ET.parse()` 完整加载 DOM 后二次 `iterparse` 遍历 tracks。`MAX_TRACK_COUNT=200` 对一帧一 track 的导出方式产生静默截断。

**规格代码漂移**：`normalized-annotation-schema/spec.md` 要求 CVAT 使用 `swim-annotation.v2`，但 ORM 默认值为 `swim-annotation.v1`，且 service 创建时未显式设置版本。

## Goals / Non-Goals

**Goals:**

- 帧映射仅在所有需要映射的 annotation_frame 均有 evidence 时 verified
- 文件名序列使用严格整数仿射推断，结果仅为 unverified candidate
- 顶层 `frame_count` 仅表示原视频总帧数，缺失时为 null
- Coverage 区间从真实 annotation_frame 生成，使用 `start_annotation_frame` / `end_annotation_frame`
- Quality checker 覆盖所有 unverified mapping 模式
- FPS 来源可信记录，未验证 FPS 不得用于推导 timestamp_sec
- manifest 直接提供 timestamp_sec 时不依赖 fps_verified
- CVAT XML parser 改为单次流式遍历
- 容量限制改为文件大小+记录总数，超限直接 parse_failed
- RawCvatPoint x/y 改为 nullable，missing 点用 None
- 规格对齐 ORM 默认 `swim-annotation.v1`
- 旧 CVAT 记录需要重新 parse，标记 contract_version

**Non-Goals:**

- 不修改 metrics engine、diagnostics engine、report builder
- 不涉及前端工作流
- 不改动 Kinovea 或其他非 CVAT 来源的解析路径
- 不自动确认文件名推断或猜测视频帧率
- 不插值生成不存在的关键帧
- 不修改数据库 `fps` 列的非空约束
- 不新增 SQL 列或 alembic 迁移

## Decisions

### D1: Frame mapping verified 条件 — 四项同时满足

`_resolve_explicit()` 中 verified 条件改成四项同时满足：

1. entries 非空
2. annotation_frame 无重复
3. 每个需要的 annotation_frame 都有对应 entry
4. 每条 entry 都包含 `source_video_frame` 或 `timestamp_sec`

```python
FrameMappingResolver.resolve(
    cvat_meta,
    video_fps,
    options,
    json_manifest,
    required_annotation_frames={f.annotation_frame for f in raw_keypoint_frames},
)
```

条件 1 + 2 保证结构完整性，条件 3 保证覆盖完整性，条件 4 保证时间证据完整性。

| 条件 | mode | verified |
|------|------|----------|
| 四项全满足 | explicit | true |
| 满足 1‑3 但 4 部分缺失 | explicit | false |
| 无法满足 1‑3 | unknown | false |
| 全部无 + 文件名可推断 affine | affine | false |
| 全部无 + 文件名无法推断 | unknown | false |

**关于 manifest 来源**：仅受信任的 extraction manifest schema（由系统 parse 流程自身构建）才可进入 explicit verified 路径。普通 COCO JSON 中碰巧出现 `source_video_frame` 字段但来源不可控时，不应仅凭字段存在自动 verified。本 Change 中 manifest 均由 service 层 `normalized_annotation_service.py` 的 parse 流程构建，不属于不可控来源。

### D2: 文件名严格整数仿射推断

提取规则：basename 中、扩展名前最后一段数字（`re.compile(r"(\d+)(?=\.[^.]+$)")`）。

验证算法：

```
输入: [(annotation_frame, source_frame_number), ...]
1. 按 annotation_frame 排序
2. 不足 2 条 → 无法推断
3. annotation_delta = pairs[1][0] - pairs[0][0]
4. source_delta = pairs[1][1] - pairs[0][1]
5. source_delta <= 0 或 source_delta % annotation_delta != 0 → 无法推断
6. stride = source_delta // annotation_delta
7. offset = pairs[0][1] - pairs[0][0] * stride
8. 验证全部条目满足 source = offset + annotation * stride
9. 通过 → affine, unverified
```

保护条件：
- 重复 annotation_frame → 拒绝
- 重复 source_video_frame → 拒绝

**严格性选择**：宁可漏判（用户可通过 override 确认）也不宽松误判。

### D3: 三层帧计数语义

| 字段 | 来源 | 语义 |
|------|------|------|
| `frame_count`（顶层） | `video_file.frame_count` | 原视频总帧数，缺失时 null |
| `annotation_sequence.frame_count` | CVAT `<job><size>` | CVAT 任务序列帧数 |
| `annotation_coverage.annotated_frame_count` | `len(keypoint_frames)` | 实际含有效骨架的帧数 |

不使用默认值回填。

### D4: Coverage 区间使用真实帧号

新增 `AnnotationFrameRange(BaseModel)`：

```python
class AnnotationFrameRange(BaseModel):
    start_annotation_frame: int
    end_annotation_frame: int
```

`build_contiguous_frame_ranges()` 从 `[kf.annotation_frame for kf in keypoint_frames]` 生成连续区间。

新写入使用 `start_annotation_frame` / `end_annotation_frame`。读取端短期兼容 `start_frame` / `end_frame`。

`analysis_ranges` 与 `annotated_ranges` 保持独立语义。

### D5: RawCvatPoint 改为 nullable

```python
class RawCvatPoint(BaseModel):
    x: float | None = None
    y: float | None = None
    visibility: Literal["visible", "occluded", "missing"]

    @model_validator(mode="after")
    def validate_visibility_coordinates(self):
        if self.visibility == "missing":
            if self.x is not None or self.y is not None:
                raise ValueError("missing raw point must not contain coordinates")
        elif self.x is None or self.y is None:
            raise ValueError("visible or occluded raw point requires coordinates")
        return self
```

### D6: FPS 来源可信与 timestamp 派生职责拆分

**FPS 来源可信度**：

| 来源 | fps_verified | fps_source |
|------|-------------|------------|
| `session_video.fps` | true | `session_video` |
| `annotation_file.annotation_fps` + metadata 标记 user_provided | true | `annotation_file` |
| `annotation_fps` 非空但无来源 metadata | false | `annotation_file_unverified` |
| 无可用 FPS（fallback 60.0） | false | `compatibility_default` |

`annotation_fps` 的来源 metadata 写入 `annotation_file.metadata` 或上传阶段的上下文中，不在本 Change 中新建 SQL 列。

**timestamp 派生职责拆分**：

```
manifest 明确提供 timestamp_sec
  → mapping verified 时直接保留
  → 不依赖 fps_verified

manifest 只提供 source_video_frame
  → 仅当 fps_verified 时推导 timestamp_sec
  → 推导式：timestamp_sec = source_video_frame / fps
  → 推导在 CvatAnnotationNormalizer 中完成，不在 resolver 中

文件名推断出的 source_video_frame
  → mapping 未验证
  → 不生成权威 timestamp_sec
```

职责边界：

```
FrameMappingResolver
  → 只解析、验证和保存 manifest 中原本存在的时间证据
  → 不通过 FPS 派生 timestamp

CvatAnnotationNormalizer
  → verified mapping + verified FPS 时：
      从 source_video_frame 派生 timestamp_sec
  → manifest 明确提供 timestamp_sec：
      mapping verified 时直接保留
  → 否则不生成 timestamp_sec
```

### D7: Quality checker 简化与扩展

`check_frame_mapping()` 改为只检查 `verified` 字段：

```python
def check_frame_mapping(frame_mapping, required=False):
    if not frame_mapping:
        return [TIME_MAPPING_MISSING] if required else []
    if frame_mapping.get("verified") is True:
        return []
    return [TIME_MAPPING_UNVERIFIED]
```

新增 issue codes：

- `FPS_UNVERIFIED`：`video.fps_verified=false` 时产生，blocking
- `ANALYSIS_RANGE_NOT_COVERED`：analysis_ranges 未被 annotated_ranges 覆盖时产生，blocking
- `TIME_MAPPING_MISSING`：CVAT 来源但 frame_mapping 为 None

新增 `contiguous_ranges_cover()` 函数验证区间包含：

```python
def contiguous_ranges_cover(
    annotated_ranges: list[dict],
    analysis_ranges: list[dict],
) -> bool:
    """验证 analysis_ranges 中每个 range 是否被 annotated_ranges 完全覆盖。"""
```

检查逻辑：

| 条件 | issue | severity | blocking |
|------|-------|----------|----------|
| annotated_frame_count < sequence_frame_count | SEQUENCE_COVERAGE_LOW | info | false |
| analysis_ranges 未被 annotated_ranges 覆盖 | ANALYSIS_RANGE_NOT_COVERED | error | true |

`side_technical_v1_cvat.yaml` 增加 FPS 和 mapping 依赖，使时间类模块依赖 `mapping_verified` 和 `fps_verified`。

### D8: 单次流式 parser

移除 `ET.parse()` 完整 DOM 加载，仅使用 `ET.iterparse()` 单次遍历同时读取 meta 和 tracks：

```
安全头部检查 (read 4096 bytes)
    ↓
ET.iterparse(start/end) 单次遍历
    ├── 收集 meta 元素
    ├── 逐 track 处理 skeleton
    └── elem.clear()
```

### D9: 容量模型

移除 `MAX_TRACK_COUNT=200` 静默截断。改用：

```python
MAX_XML_FILE_SIZE_BYTES = 100 * 1024 * 1024   # 100MB
MAX_SKELETON_RECORDS = 50000                   # 单文件最多骨架记录
MAX_ACTIVE_FRAMES = 20000                      # 单文件最多有效帧
MAX_POINTS_PER_SKELETON = 150                  # 单幅骨架最多关键点
MAX_WARNINGS = 100
```

超限时直接 `parse_failed`，不返回部分数据。

### D10: Schema version 与 contract version

ORM 默认值、server_default 均为 `swim-annotation.v1`。现有规格第 393-398 行要求 v2，改为 v1。

因旧记录与新记录同为 v1 但语义不同（旧记录 frame_count=annotated 而新记录 frame_count=source video），增加 `contract_version` 区分：

```json
{
  "contract_version": "cvat-import-contract.v1.1"
}
```

**旧记录处理**：
- 审计所有 `NormalizedAnnotation.frame_count` 的读取位置，确认无代码将其当 annotated frame count 使用
- 既有 CVAT normalized annotation 需重新 parse 以刷新 contract_version 和帧语义
- 未重新 parse 的旧记录在 quality 中标记为 `stale_contract`

### D11: KeypointFrame 增加 source_track_ids

`KeypointFrame` 增加可选字段 `source_track_ids: list[str] = Field(default_factory=list)`，从 `RawCvatKeypointFrame.source_track_ids` 传递。

```python
class KeypointFrame(BaseModel):
    frame: int
    time_sec: float
    phase: str = ""
    points: dict[str, KeypointPoint] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    annotation_frame: int | None = None
    source_video_frame: int | None = None
    timestamp_sec: float | None = None
    image_name: str | None = None
    source_track_ids: list[str] = Field(default_factory=list)
```

这是向后兼容的可选字段。

### D12: 错误结构化

`CvatParseError` 增加结构化信息：

```python
class CvatParseError(Exception):
    def __init__(self, code: str, message: str,
                 frame: int | None = None,
                 track_ids: list[str] | None = None):
        self.code = code
        self.frame = frame
        self.track_ids = track_ids
        self.message = message
```

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| 文件名推断严格导致合法场景被拒 | 用户需要手动 override | 提供 `ParseAnnotationOptions.frame_mapping_override` 途径 |
| 现存记录使用旧 coverage key（`start_frame`） | 质量检查读不到正确区间 | 读取端兼容新旧 key 六个月 |
| 移除 `MAX_TRACK_COUNT` 的静默截断 | 超大文件直接失败，用户需拆分 | 100MB / 50000 条的阈值对单运动员单侧视图已足够宽松 |
| 未验证 FPS 和 mapping 导致时间指标 blocked | 用户觉得"解析成功了但指标不可用" | quality 响应中明确说明阻断原因和解除方法 |
| 收紧后的时间可信度规则导致部分时间指标降级 | 同版本 v1 但语义不同 | quality 中标记旧记录为 `stale_contract`，通知用户重新 parse |
| annotation_fps 缺少来源 metadata | 无法区分用户填写和程序默认 | 本 Change 仅识别已带 metadata 的场景，其余标记为 unverified |

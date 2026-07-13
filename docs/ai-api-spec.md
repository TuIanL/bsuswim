# AI 接口规范

## 1. 目标

本规范定义业务后端与模型服务之间的接口边界，保证即使后续替换 YOLO、MMPose 或推理框架，业务 API 和前端消费方式也尽量保持稳定。

当前相关实现位于：

- [backend/app/schemas.py](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/backend/app/schemas.py)
- [backend/app/services/model_client.py](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/backend/app/services/model_client.py)
- [model_service/app/schemas.py](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/model_service/app/schemas.py)
- [model_service/app/main.py](/Users/tuian/Documents/大学/竞赛/大创/游泳/swim/model_service/app/main.py)

## 2. 接口职责

### 业务后端负责

- 上传视频并保存元数据
- 创建分析任务
- 将任务参数转发给模型服务
- 校验模型响应
- 保存分析结果和报告结果

### 模型服务负责

- 接收标准化分析请求
- 执行模型推理和后处理
- 返回结构化分析结果

## 3. 模型服务接口

### 健康检查

```http
GET /health
```

响应示例：

```json
{
  "status": "ok",
  "service": "model_service"
}
```

### 分析接口

```http
POST /api/v1/analyze
Content-Type: application/json
```

## 4. 请求结构

当前请求模型：`AnalysisRequest`

```json
{
  "task_id": 1001,
  "video_path": "uploads/abc123.mp4",
  "video_url": "/uploads/abc123.mp4",
  "metadata": {
    "session_title": "自由泳技术评估",
    "venue": "50m pool",
    "session_date": "2026-06-16",
    "swimmer_label": "A 组运动员",
    "stroke_type": "freestyle",
    "level": "competitive",
    "capture_mode": "side_view"
  }
}
```

字段说明：

- `task_id`: 业务后端任务 ID
- `video_path`: 模型服务可访问的视频物理路径或本地路径
- `video_url`: 用于前端回放或调试的资源引用
- `metadata`: 训练与分析上下文

## 5. 响应结构

当前响应模型：`AnalysisResponse`

```json
{
  "schema_version": "swim-analysis.v1",
  "status": "completed",
  "detections": [],
  "keypoint_frames": [],
  "phases": [],
  "metrics": {},
  "diagnostics": [],
  "error_message": null
}
```

字段说明：

- `schema_version`: 结果 schema 版本号，前后端兼容关键字段
- `status`: `completed` 或 `failed`
- `detections`: 检测框序列
- `keypoint_frames`: 关键点帧序列
- `phases`: 动作阶段结果
- `metrics`: 技术指标
- `diagnostics`: 诊断结论
- `error_message`: 失败时返回原因

## 6. 字段约定

### 6.1 `detections`

建议结构：

```json
[
  {
    "time": 0.0,
    "bbox": [0.18, 0.36, 0.34, 0.18],
    "label": "swimmer",
    "confidence": 0.93
  }
]
```

约定：

- `time` 以秒为单位
- `bbox` 使用归一化坐标 `[x, y, w, h]`
- `confidence` 范围建议为 `0-1`

### 6.2 `keypoint_frames`

建议结构：

```json
[
  {
    "time": 0.0,
    "points": [
      { "name": "head", "x": 0.28, "y": 0.39, "score": 0.92 }
    ]
  }
]
```

约定：

- 一条记录对应一个时间点或一个关键帧
- 点坐标建议归一化到 `0-1`
- `name` 使用稳定命名，不要前后版本随意变

### 6.3 `phases`

建议结构：

```json
[
  {
    "start": 0.0,
    "end": 1.2,
    "label": "入水与前伸"
  }
]
```

约定：

- 使用区间表达动作阶段
- `label` 为前端可直接展示的语义标签

### 6.4 `metrics`

建议结构：

```json
{
  "overall_score": 81,
  "body_line_score": 78,
  "rhythm_score": 83,
  "symmetry_score": 74,
  "kick_score": 76
}
```

约定：

- 指标 key 尽量稳定
- 数值范围和单位要固定
- 如果某项暂不可得，不要伪造，允许缺失

### 6.5 `diagnostics`

建议结构：

```json
[
  {
    "title": "身体中线轻微摆动",
    "severity": "medium",
    "evidence": "髋部关键点在推水阶段出现横向波动",
    "suggestion": "增加侧身打腿和单臂划水练习",
    "expected_improvement": "减少阻力并提高划水连续性",
    "priority": 1
  }
]
```

约定：

- `severity` 建议统一为 `low | medium | high`
- `priority` 用于前端排序
- `evidence` 与 `suggestion` 都要面向教练和运动员可读

## 7. 错误处理约定

模型服务失败时建议返回：

```json
{
  "schema_version": "swim-analysis.v1",
  "status": "failed",
  "detections": [],
  "keypoint_frames": [],
  "phases": [],
  "metrics": {},
  "diagnostics": [],
  "error_message": "模型推理超时"
}
```

业务后端收到后：

- 将任务状态置为 `failed`
- 保存 `error_message`
- 前端通过任务详情或任务列表展示稳定错误状态

## 8. 版本演进原则

- 新增字段优先向后兼容
- 破坏性变更必须升级 `schema_version`
- 前端工作台应根据 `schema_version` 决定是否支持渲染
- 后端应继续保存 `raw_result`，便于后期重放和排查

## 9. 当前实现状态

当前 `model_service/app/runtime.py` 返回的是 stub 结果，用来验证：

- 请求链路
- 结果校验
- 数据库存储
- 工作台 Canvas 叠加
- HTML 报告渲染

接入真实 YOLO / MMPose 时，优先保持这份接口规范不变，只替换 runtime 内部实现。

## 10. NormalizedAnnotation — 标准化标注输入层

### 概述

`NormalizedAnnotation`（当前版本 `swim-annotation.v2`）是业务后端与模型服务之间的**稳定观测输入格式**。它统一了 Kinovea 人工标注、CVAT 骨架标注、Dartfish、AI 姿态识别和人工 JSON 补录等多种来源的标注数据，作为下游 metrics engine 和 diagnostics engine 的唯一输入。

### 在整体架构中的位置

```text
annotation_files (原始文件: XML / JSON / CSV)
  → parse（source=cvat 或 source=kinovea）
    → FrameMappingResolver（仅 CVAT：帧号 → 时间戳映射）
    → CvatAnnotationNormalizer（仅 CVAT：注入时间信息）
    → AnnotationDerivedDataBuilder（仅 CVAT：推导轨迹/身体中心）
    → NormalizedAnnotation (标准化观测输入, swim-annotation.v2)
      → Metrics Engine → Diagnostics Engine
        → analysis_results → report_metadata
```

### 关键原则

- NormalizedAnnotation **只描述观测事实**（在哪个帧、哪个关节、什么位置），不包含计算结论
- `analysis_results` **只存储计算结果**（角度、划频、SWOLF、诊断），不重复存储观测数据
- 不同来源（Kinovea / CVAT / AI / manual）的输出只要转换为 `swim-annotation.v2` schema，即可复用后续整条分析链路
- CVAT 来源的 parse 链路包含三层：Parser（忠实提取）→ Normalizer（时间映射）→ Builder（数据派生），各层职责完全正交

### 支持的数据来源

| 来源 | 文件格式 | 特点 |
|------|---------|------|
| Kinovea | `.json` / `.csv` | 含 events、trajectories、manual_tags |
| CVAT | `.xml` + 可选 `.json` | COCO 17 点骨架，仅关键点，无 events/轨迹 |
| AI Pose | `.json` | 模型推理输出（待接入） |
| Manual JSON | `.json` | 直接构造的符合 schema 的 JSON |

### CVAT 标注导入流程

#### 文件上传

CVAT 标注包含两个文件：
- **主文件**：`annotations.xml`（CVAT Task XML 格式，必须上传）
- **Companion 文件**：`instances_default.json`（COCO JSON 格式，可选，提供帧名→帧号映射）

上传时分别创建两个 `AnnotationFile`，source 均为 `cvat`。XML 作为主 annotation_file，JSON 在 parse 时通过 `ParseAnnotationOptions.companion_annotation_file_id` 关联。

#### Parse 请求

```http
POST /api/v1/annotations/{annotation_file_id}/parse
Content-Type: application/json

{
  "companion_annotation_file_id": 123,
  "frame_mapping_override": {
    "mode": "affine",
    "source_frame_offset": 32,
    "source_frame_stride": 1,
    "confirmed": true
  },
  "analysis_ranges": [
    {"start_annotation_frame": 0, "end_annotation_frame": 55}
  ]
}
```

##### ParseAnnotationOptions 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `companion_annotation_file_id` | int | 否 | CVAT JSON companion 文件的 annotation_file_id，用于获取精确帧映射 |
| `frame_mapping_override` | object | 否 | 用户手动指定的帧映射参数，优先级高于自动推断 |
| `frame_mapping_override.mode` | `"affine"` / `"identity"` | 是 | 映射模式：affine 为线性映射，identity 为直接对应 |
| `frame_mapping_override.source_frame_offset` | int | 否 | 首帧在原视频中的帧号（affine 模式需要） |
| `frame_mapping_override.source_frame_stride` | int | 否 | 帧间隔步长（affine 模式需要，通常为 1） |
| `frame_mapping_override.confirmed` | bool | 否 | 用户确认映射准确，设为 `true` 时时间类指标可用 |
| `analysis_ranges` | array | 否 | 指定感兴趣的分析帧范围，格式 `[{start_annotation_frame, end_annotation_frame}]` |

##### Frame Mapping 四种模式

| 模式 | 触发条件 | verified | 时间类指标 |
|------|---------|----------|-----------|
| `explicit` | Companion JSON 提供逐帧 `source_video_frame` | `true` | 可用 |
| `affine` | 文件名连续，用户提供 offset/stride | 用户确认后 `true` | 确认后方可用 |
| `identity` | annotation_frame = source_video_frame | 用户确认后 `true` | 确认后方可用 |
| `unknown` | 无法推断映射关系 | `false` | 被 blocked |

当 `verified = false` 时，姿态类指标（角度）仍可计算，但时间类指标（速度、划频、阶段时长）均被 blocked。

#### Parse 响应

```json
{
  "normalized_annotation_id": 42,
  "annotation_file_id": 1,
  "source": "cvat",
  "status": "parsed",
  "schema_version": "swim-annotation.v2",
  "revision": 1,
  "summary": {
    "keypoint_frame_count": 56,
    "trajectory_count": 19,
    "event_count": 0,
    "warnings": ["FRAME_MAPPING_UNVERIFIED: 时间映射未经验证"]
  },
  "quality": {
    "level": "degraded",
    "score": 0.65,
    "issues": [...]
  },
  "analysis_readiness": {
    "kinematic": "ready",
    "temporal": "blocked",
    "strength": "ready"
  },
  "warnings": [
    "FRAME_MAPPING_UNVERIFIED: 时间映射未经验证，时间类指标不可用"
  ]
}
```

### 数据派生层 (CVAT 特有)

CVAT 只有骨架关键点，没有轨迹和 events。parse 完成后自动执行数据派生：

| 派生数据 | 说明 |
|---------|------|
| Trajectories | 串联各帧同一关键点位置的时序轨迹 |
| Body Center (hip_center) | 双髋 visible 时取 midpoint，单髋时跳过 |
| Visibility Summary | 各关键点 visible/occluded/missing 帧数统计 |

派生层异常时降级为 warning，不阻止 parse。

### 当前实现状态

- Schema 版本：`swim-annotation.v2`
- 表：`normalized_annotations`（关联 `session_videos`）
- API：`POST /api/v1/session-videos/{id}/normalized-annotations`（JSON 创建）
- API：`POST /api/v1/annotations/{id}/parse`（支持 source = kinovea / cvat / manual_json）
- 解析器：Kinovea JSON/CSV parser、CVAT XML parser
- 示例文件：`backend/samples/side-view-freestyle-v1.json`
- 元数据存储：`annotation_metadata` JSONB 列，包含 `video`、`annotation_sequence`、`frame_mapping`、`annotation_coverage`、`analysis_ranges`

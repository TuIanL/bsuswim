## Why

系统已经能够把 CVAT COCO17 二维骨架转换成 `swim-side-kinematics.v1` 指标，包含四类运动学指标、逐帧时序、取值范围、代表帧和质量信息。但当前指标仍然只是 JSON 数值，报告 section 中的 assets 为空，无法形成教练可直接阅读和复核的「原始画面 + 骨架证据 + 趋势图」视觉表达。需要新增视觉资产生成层，将确切的一条 AnnotationMetric、对应的 NormalizedAnnotation 和原始视频转换成可持久化、可追溯、可被 HTML、PDF 和未来复测报告重复引用的资产集。

## What Changes

- 新增 `swim-kinematic-artifacts.v1` 资产清单 schema
- 新增 `KinematicArtifactSet`，表示一次完整、可追溯的视觉资产生成结果
- 新增 `KinematicArtifact`，保存每个图像或图表资产的元数据
- 以准确的 `annotation_metric_id` 作为生成入口
- 校验 AnnotationMetric 的 calculator、schema_version 和 source_revision
- 从原视频提取经过验证映射的关键帧
- 在关键帧上绘制 COCO17 骨架、身体轴线、关节角和指标值
- 生成关节角时序图
- 生成关节相对轨迹图（统一回源 `NormalizedAnnotation.keypoint_frames`，通过现有 `CanonicalKinematicFrame` resolver 重建，指标只提供数值、质量、范围和选择依据）
- 生成分单位的运动范围比较图
- 生成标题固定为「当前片段运动稳定性概览」的雷达图
- 资产文件使用相对路径持久化到 StorageService
- 生成稳定 artifact manifest，记录输入版本、指标来源、尺寸、校验和和生成器版本
- 支持部分生成：关键帧无法提取时，仍允许生成不依赖视频帧的图表
- 提供生成和读取 artifact manifest 的 API
- 不修改现有指标计算结果，不在本 Change 中接入诊断或报告装配

## Capabilities

### New Capabilities

- `kinematics-visual-artifacts`：从 `swim-side-kinematics.v1` 指标和对应视频生成五类视觉资产（骨架叠加关键帧、关节角时序图、关节相对轨迹图、运动范围比较图、稳定性雷达图），保存稳定、版本化、可追溯的资产清单，支持资产部分可用与结构化失败原因。

### Modified Capabilities

- `backend-platform-core`：新增视觉资产 API、持久化模型和通用存储 URL 构造能力。
- `storage-service`：`save_bytes()` 返回文件大小和 SHA-256，支持安全的嵌套相对路径。

## Impact

- 新增数据库表：`kinematic_artifact_sets`、`kinematic_artifacts`
- 新增 Alembic migration 0009
- 新增：`backend/app/models/kinematic_artifact.py`、`backend/app/schemas/kinematic_artifact.py`、`backend/app/services/kinematic_artifacts/`、`backend/app/api/routes/kinematic_artifacts.py`
- 修改：`backend/app/models/__init__.py`、`backend/app/api/router.py`、`backend/app/services/storage.py`、`backend/requirements.txt`
- 新增单元测试、API 测试和视觉资产 golden fixture

## Non-Goals

- 不重新计算或修改 side_2d_kinematics 指标
- 不增加动作阶段识别
- 不生成水面夹角、真实距离、真实速度或推进力
- 不生成诊断结论或训练建议
- 不在本 Change 中修改 ReportData 或前端报告页面
- 不修改 PDF 导出流程
- 不引入后台任务队列
- 不把雷达图解释为经过验证的技术能力评分

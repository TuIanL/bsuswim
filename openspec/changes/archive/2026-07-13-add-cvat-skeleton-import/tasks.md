## 1. Schema 和数据模型变更

- [x] 1.1 `AnnotationSource` 枚举新增 `CVAT = "cvat"`，更新 `models/annotation.py`
- [x] 1.2 `KeypointPoint` 的 `x`、`y` 改为 `float | None`，`visibility` 扩展 `"missing"`，保留 `"estimated"`（deprecated），更新 `schemas/normalized_annotation.py`
- [x] 1.3 为 `KeypointPoint` 增加 `@model_validator` 校验坐标-可见性一致性（missing→null，visible/occluded→有值）
- [x] 1.4 `KeypointFrame` 新增 `annotation_frame`、`source_video_frame`、`timestamp_sec`、`image_name` 字段，`frame` 保留作为 `annotation_frame` 别名
- [x] 1.5 定义 `FrameMapping`、`FrameMappingEntry`、`ParseAnnotationOptions`、`FrameMappingOverride`、`AnalysisRange` Pydantic schema
- [x] 1.6 定义 `ParsedCvatAnnotation`（含 `raw_keypoint_frames`）、`RawCvatKeypointFrame`、`RawCvatPoint` 纯数据类

## 2. CVAT XML Parser

- [x] 2.1 新建 `services/parsers/cvat_xml.py`，使用 `xml.etree.ElementTree.iterparse` 实现 `parse_cvat_xml(file_path) -> ParsedCvatAnnotation`
- [x] 2.2 实现 `_extract_meta()` — 从 XML `<meta>` 提取 job、帧范围、标签定义和图片尺寸
- [x] 2.3 实现 `_extract_tracks()` — streaming 遍历所有 `<track>`，提取 skeleton 和 points
- [x] 2.4 实现 `_aggregate_by_frame()` — 按 frame 分组，验证单帧多 skeleton 约束；遇到同一帧 >1 个 `outside=0` 的 skeleton 时产生 `MULTIPLE_ACTIVE_SKELETONS` error 阻止 parse
- [x] 2.5 实现 `_skeleton_to_raw_frame()` — 将单个原始 skeleton 转为 `RawCvatKeypointFrame`（无时间戳），处理 outside/occluded 映射，记录 `source_track_ids`
- [x] 2.6 实现 COCO 17 点名称映射（kebab-case → snake_case），保留脸部 5 点
- [x] 2.7 处理 `outside="1"` 全骨架跳过和部分点 missing 场景，丢弃 outside=1 残留坐标
- [x] 2.8 实现安全校验：拒绝 DTD/entity、拒绝 NaN/Infinity/负数坐标、限制最大 track 数（200）、最大帧数（10000）、最大单帧关键点（150）、warning 上限（100）
- [x] 2.9 更新 `services/parsers/__init__.py` 导出 CVAT parser 相关函数

## 3. 帧映射 (Frame Mapping)

- [x] 3.1 新建 `services/parsers/frame_mapping.py`，定义 `FrameMappingResolver`
- [x] 3.2 实现 `resolve_explicit()` — 从 extraction_manifest 逐帧映射，`verified = true`
- [x] 3.3 实现 `resolve_affine()` — 根据 offset + stride 批量计算；文件名连续推断时 `verified = false`
- [x] 3.4 实现 `resolve_identity()` — annotation_frame = source_video_frame
- [x] 3.5 实现 `resolve_unknown()` — 保守模式，不推导时间戳，`verified = false`
- [x] 3.6 集成 `ParseAnnotationOptions.frame_mapping_override`：用户显式确认时 `verified = true`
- [x] 3.7 新建 `services/parsers/cvat_normalizer.py`，实现 `CvatAnnotationNormalizer.normalize(raw_frames, mapping) -> KeypointFrame[]`，将 FrameMapping 注入每个 KeypointFrame

## 4. 数据派生层 (Annotation Derivation)

- [x] 4.1 创建 `services/annotation_derivation/` 包目录结构
- [x] 4.2 实现 `trajectory_builder.py` — 按关键点名称串联 visible/occluded 点，source 标记为 `derived_from_keypoints`，missing 点形成轨迹缺口
- [x] 4.3 实现 `body_center_builder.py` — 计算 hip_center 以派生轨迹形式输出（不新增顶层字段）；双髋 visible 时 midpoint，单髋或双髋不可见时本帧 skip
- [x] 4.4 实现 `visibility_summary.py` — 统计每个关键点 visible/occluded/missing 帧数及覆盖率
- [x] 4.5 实现 `builder.py` — `AnnotationDerivedDataBuilder` 编排入口，捕获异常降级为 warning
- [x] 4.6 Builder 不做插值，不做置信度自动派生（CVAT confidence = null）

## 5. Parse 链路集成

- [x] 5.1 在 `normalized_annotation_service.py` 的 `parse_annotation_file()` 中新增 `source == "cvat"` 分支
- [x] 5.2 CVAT 分支按序调用：`CvatXmlParser` → `FrameMappingResolver` → `CvatAnnotationNormalizer` → `AnnotationDerivedDataBuilder`
- [x] 5.3 将 parser 输出（keypoint_frames）、派生数据（trajectories）和元数据（video/annotation_sequence/frame_mapping/coverage）写入 NormalizedAnnotation
- [x] 5.4 派生层异常降级为 warning，不阻断 parse
- [x] 5.5 同一帧多 skeleton 时阻止 parse 并写 `parse_failed` 状态
- [x] 5.6 验证 companion JSON 与 XML 归属同一 session_video，不一致时阻止 parse
- [x] 5.7 验证 Kinovea 分支不受影响

## 6. 上传入口和文件类型

- [x] 6.1 在 `annotation_file_service.py` 确认 `source = "cvat"` 时可上传 `xml` 和 `json` 文件类型
- [x] 6.2 更新 `validate_annotation_file()` 说明允许 CVAT XML
- [x] 6.3 实现 companion annotation_file 关联：XML 按主文件上传，JSON 按独立 annotation_file 上传，parse 时通过 `ParseAnnotationOptions.companion_annotation_file_id` 关联（不做 ZIP bundle）

## 7. Quality 适配

- [x] 7.1 新建 `side_technical_v1_cvat` quality profile，按指标级声明 availability
- [x] 7.2 实现指标级 availability 矩阵：角度/轨迹指标依赖关键点可见性，速度/距离指标依赖 scale 和 timestamp_sec，划水周期指标依赖 events
- [x] 7.3 `events` 为空且 `source=cvat` 时 quality = warning，cycle-based 指标 blocked（通过 profile 无 event 要求实现）
- [x] 7.4 `scale` 缺失且 `source=cvat` 时物理距离/速度指标 blocked
- [x] 7.5 v2 `frame_mapping.verified = false` 时时间类指标 blocked，包含 `TIME_MAPPING_UNVERIFIED` issue code
- [x] 7.6 `annotated_frame_count < annotation_sequence.frame_count` 且无 `analysis_ranges` 时生成 info 级 `SEQUENCE_COVERAGE_LOW`
- [x] 7.7 声明 `analysis_ranges` 且全覆盖时抑制 `SEQUENCE_COVERAGE_LOW`
- [x] 7.8 确认 Kinovea source 的 quality 评估不受 CVAT 规则影响（通过 profile_id 参数选择）

## 8. 数据库

- [x] 8.1 确认 `annotation_metadata` JSONB 列已存在，不需新增独立列
- [x] 8.2 确认 `AnnotationSource` 枚举值（字符串）在数据库约束下的兼容性，添加 `cvat`

## 9. 测试

- [x] 9.1 编写 CVAT XML parser 单元测试（正常解析、多 track 分组、outside 全/部分映射、occluded 映射）
- [x] 9.2 编写 MULTIPLE_ACTIVE_SKELETONS 测试 — 同一帧两个 skeleton 时 blocked
- [x] 9.3 编写 XML 安全测试（DTD 拒绝、NaN/Infinity 坐标拒绝、超大文件）
- [x] 9.4 编写 FrameMappingResolver 单元测试（四种模式、文件名推断 verified=false、user override verified=true）
- [x] 9.5 编写 CvatAnnotationNormalizer 单元测试（时间戳注入、字段填充）
- [x] 9.6 编写 TrajectoryBuilder 单元测试（串联、缺口、occluded 标记、无插值）
- [x] 9.7 编写 BodyCenterBuilder 单元测试（双髋 midpoint、单髋 skip、无髋 skip、输出为派生轨迹格式）
- [x] 9.8 编写 VisibilitySummary 单元测试
- [x] 9.9 编写 KeypointPoint model_validator 测试（missing+坐标拒绝、visible+null 拒绝、occluded+null 拒绝）
- [x] 9.10 编写 parse 集成测试（通过 service 层 mock 测试 CVAT parse 链路完整）
- [x] 9.11 编写 quality 适配测试 — 12 个测试覆盖 check_frame_mapping + check_sequence_coverage
- [x] 9.12 编写 backward compatibility 测试（旧 v1 visibility="estimated" 可读 model_validator 测试）
- [x] 9.13 编写 companion JSON 验证测试 — 2 个测试覆盖 mismatched session + not found 场景
- [x] 9.14 编写 56 帧真实模式测试 — 3 个测试：帧数正确、无重复帧、17 点 COCO 全覆盖
- [x] 9.15 准备 CVAT XML 测试夹具文件（cvat_56_frames.xml + cvat_multi_skeleton.xml + pytest 动态生成 56 帧夹具）

## 10. 结束工作

- [x] 10.1 运行全部已有测试确保回归通过（201 passed, 1 skipped；2 个 side_view_metrics 测试为前置 quality v2 迁移遗留问题，不属本 Change）
- [x] 10.2 更新 API 文档：CVAT XML 上传流程、ParseAnnotationOptions 使用方式、companion JSON 关联
- [x] 10.3 手动端到端验证：上传真实 CVAT XML → parse → 查看 NormalizedAnnotation → 触发 metrics 计算

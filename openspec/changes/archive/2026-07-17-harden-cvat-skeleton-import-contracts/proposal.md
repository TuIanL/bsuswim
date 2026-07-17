## Why

CVAT Skeleton XML 导入功能已经在代码层面完成，但帧映射真值条件、帧计数语义、覆盖范围计算和品质检查逻辑存在四个数据契约问题，会导致后续运动学指标引用错误的视频位置或时间轴：

1. `frame_mapping.verified` 对仅有文件名的 companion JSON 错误设为 `true`，时间类指标虚警通过；
2. `frame_count` 错误使用 `len(keypoint_frames)`，而非原视频总帧数；
3. 默认 annotation coverage 使用连续计数推断，而非真实 annotation_frame；
4. quality checker 对 `explicit + false` 和 `unknown + false` 漏判 `TIME_MAPPING_UNVERIFIED`。

此外，parser 实现需要从混合 DOM+流式改为纯流式，容量限制和错误报告也需要加固。

本 Change 的目标是：**确保 CVAT 标注能够准确、可追溯地转换成后续指标可以直接消费的 NormalizedAnnotation，且在证据不足时明确阻断，不产生看似完整但错误的时间轴。**

## What Changes

- 修复 `_resolve_explicit()`：verified 需四项同时满足（entries 非空、annotation_frame 唯一、全部所需帧有 entry、每 entry 有时间证据）
- 新增文件名序列严格整数仿射推断（恒定 offset + stride），结果仅为 unverified affine candidate
- 修复 `frame_count` 顶层字段：仅表示 source video frame count，缺失时为 null
- 根据真实 annotation_frame 生成覆盖率区间，使用 `start_annotation_frame` / `end_annotation_frame` 规范命名
- 修复 quality checker 中 `check_frame_mapping()`：所有 unverified mode 均产生 `TIME_MAPPING_UNVERIFIED`
- 增加 `FPS_UNVERIFIED` 和 `ANALYSIS_RANGE_NOT_COVERED` quality issue codes
- 拆分 timestamp 派生职责：manifest 直接提供 timestamp_sec 时不依赖 fps_verified；resolver 不派生 timestamp，派生在 normalizer 中完成
- 增加 FPS 来源可信记录（`fps_source` / `fps_verified`），`annotation_fps` 需要来源 metadata 才标记 verified
- 时间类模块同时依赖 mapping_verified 和 fps_verified（但直接提供的 timestamp_sec 例外）
- 将 CVAT XML parser 改为单次流式遍历，移除 `ET.parse()` 完整 DOM 加载
- 移除 `MAX_TRACK_COUNT=200` 静默截断行为，改为基于文件大小和记录总数的安全限制，超限直接 parse_failed
- `RawCvatPoint.x` / `y` 改为 nullable，missing 点使用 None 而非 (0,0) sentinel
- 错误从纯文本提升为结构化代码（含 code / frame / track_ids）
- 增加 parser metadata（name / version / source_format）和 `contract_version`
- `KeypointFrame` 增加 `source_track_ids` 可选字段，保留 track 溯源
- 旧 CVAT 记录需重新 parse；quality 标记未重解析记录为 `stale_contract`
- 规格统一：`schema_version` 确认使用 `swim-annotation.v1`（匹配 ORM 默认值），修正 existing spec 中的 v2 要求
- 修改 CVAT quality profile YAML 使模块依赖 mapping_verified 和 fps_verified
- 增加 golden fixture 测试：真实 XML + companion JSON

## Capabilities

### Modified Capabilities

- `cvat-xml-parse`: parser 改为单次流式，raw point 模型可空，容量限制从 track 计数改为记录总数与文件大小，错误结构化，未确认帧映射和 FPS 不得生成时间戳
- `annotation-time-mapping`: 文件名推断为严格 affine，仅当含 source_time 证据时才 verified，quality checker 覆盖所有未验证模式
- `normalized-annotation-schema`: 新增 `AnnotationFrameRange`，coverage 和 analysis_ranges 统一命名，schema_version 确认 v1
- `annotation-quality`: `check_frame_mapping()` 简化，新增 `FPS_UNVERIFIED` issue code，区间覆盖检查不再仅依赖帧数对比

## Impact

- `backend/app/services/parsers/cvat_xml.py`
- `backend/app/services/parsers/frame_mapping.py`
- `backend/app/services/parsers/cvat_normalizer.py`
- `backend/app/services/normalized_annotation_service.py`
- `backend/app/schemas/normalized_annotation.py`
- `backend/app/services/annotation_quality/checks/cvat_checks.py`
- `backend/app/services/annotation_quality/issue_codes.py`
- `openspec/specs/cvat-xml-parse/spec.md`
- `openspec/specs/annotation-time-mapping/spec.md`
- `openspec/specs/normalized-annotation-schema/spec.md`
- `openspec/specs/annotation-quality/spec.md`
- `backend/tests/`（新增 golden fixture 和回归测试）
- 不修改 metrics engine、diagnostics engine、report builder、前端

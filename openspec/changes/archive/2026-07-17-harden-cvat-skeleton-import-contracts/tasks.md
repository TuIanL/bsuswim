## 0. Capability specifications

- [x] 0.1 修改 `cvat-xml-parse` delta spec（streaming parser / nullable raw point / capacity limits / structured errors）
- [x] 0.2 修改 `annotation-time-mapping` delta spec（4 项 verified 条件 / required_annotation_frames / timestamp 派生职责拆分 / 文件名推断）
- [x] 0.3 修改 `normalized-annotation-schema` delta spec（AnnotationFrameRange / contract_version / KeypointFrame.source_track_ids / Frame-count semantics / coverage range）
- [x] 0.4 修改 `annotation-quality` delta spec（check_frame_mapping 简化 / FPS_UNVERIFIED / ANALYSIS_RANGE_NOT_COVERED / 区间包含检查）

## 1. Frame mapping truthfulness — P0

- [x] 1.1 `_resolve_explicit()` 增加四项 verified 条件：entries 非空、annotation_frame 唯一、全部所需帧有 entry、每 entry 有时间证据
- [x] 1.2 `FrameMappingResolver.resolve()` 新增参数 `required_annotation_frames: set[int]`，验证覆盖完整性
- [x] 1.3 实现文件名最终数字 token 提取函数 `extract_final_numeric_token(image_name: str) -> int | None`
- [x] 1.4 实现严格整数 affine 检查函数 `infer_affine_from_filenames(entries) -> FrameMapping`
- [x] 1.5 支持恒定正整数 stride（如 1、2、5），拒绝非恒定序列
- [x] 1.6 单条 filename entry 不足以推断 affine
- [x] 1.7 重复 annotation_frame 或重复 source_video_frame 阻止推断
- [x] 1.8 部分 entry 有时间证据、部分没有时返回 explicit + unverified
- [x] 1.9 修复 quality checker 的 `check_frame_mapping()`：所有 `verified=false` 均产生 `TIME_MAPPING_UNVERIFIED`，不再按 mode 分支
- [x] 1.10 CVAT mapping 缺失时产生 `TIME_MAPPING_MISSING`（仅 CVAT 来源）
- [x] 1.11 normalizer 中：manifest 直接提供 timestamp_sec 且 mapping verified 时保留，不依赖 fps_verified
- [x] 1.12 normalizer 中：从 source_video_frame 派生 timestamp_sec 必须同时满足 mapping_verified 和 fps_verified
- [x] 1.13 resolver 不得使用未验证的 FPS 派生时间戳（职责移交给 normalizer）
- [x] 1.14 测试：manifest 只有部分帧有 source_video_frame 时返回 explicit + unverified
- [x] 1.15 测试：manifest 覆盖不完整（缺某些 annotation_frame）返回 explicit + unverified
- [x] 1.16 测试：manifest 明确提供 timestamp_sec 且 mapping verified 时保留 timestamp
- [x] 1.17 测试：companion JSON 仅含 filenames 时产生 unverified affine
- [x] 1.18 测试：companion JSON 全部含 source_video_frame 时产生 verified explicit
- [x] 1.19 测试：非恒定 stride 文件名序列返回 unknown
- [x] 1.20 测试：explicit + unverified 产生 quality warning

## 2. FPS trust contract — P0

- [x] 2.1 在 `annotation_metadata.video` 中增加 `fps_source` 和 `fps_verified` 字段
- [x] 2.2 `session_video.fps` 可用时标记为 `fps_verified=true, fps_source="session_video"`
- [x] 2.3 `annotation_file.annotation_fps` 需要附带来源 metadata（`user_provided`）才标记 verified，否则为 unverified
- [x] 2.4 兼容默认 60.0 标记为 `fps_verified=false, fps_source="compatibility_default"`
- [x] 2.5 新增 `FPS_UNVERIFIED` issue code
- [x] 2.6 quality checker 在 `fps_verified=false` 时产生 `FPS_UNVERIFIED` issue
- [x] 2.7 时间类模块同时依赖 `mapping_verified` 和 `fps_verified`，任一 false 则 blocked（直接提供的 timestamp_sec 除外）
- [x] 2.8 修改 `side_technical_v1_cvat.yaml`：时间类模块依赖 `frame_mapping.verified` 和 `video.fps_verified`
- [x] 2.9 测试：无 FPS 来源时产生 `FPS_UNVERIFIED` warning
- [x] 2.10 测试：verified FPS 不产生 `FPS_UNVERIFIED`
- [x] 2.11 测试：直接提供 timestamp_sec 时不依赖 fps_verified

## 3. Frame-count semantics — P0

- [x] 3.1 顶层 `frame_count` 只表示 source video frame count，值来自 `video_file.frame_count`
- [x] 3.2 缺少 source video frame count 时保持 null，不用 CVAT task size 回填
- [x] 3.3 `annotation_sequence.frame_count` 使用 CVAT `<job><size>`
- [x] 3.4 `annotation_coverage.annotated_frame_count` 使用实际骨架帧数量 `len(keypoint_frames)`
- [x] 3.5 审计所有 `NormalizedAnnotation.frame_count` 的读取位置，确认无代码仍将其当 annotated frame count 使用
- [x] 3.6 测试：三个帧数在真实 XML 上产生正确且互不混淆的值
- [x] 3.7 测试：缺少 video_file.frame_count 时顶层 frame_count 为 null

## 4. Coverage contracts — P1

- [x] 4.1 新增 `AnnotationFrameRange` schema（start_annotation_frame / end_annotation_frame）
- [x] 4.2 实现 `build_contiguous_frame_ranges(frames: list[int]) -> list[AnnotationFrameRange]`
- [x] 4.3 连续、稀疏、单帧和非零起始帧的区间生成
- [x] 4.4 service 写入 coverage 使用真实 annotation_frame，而非连续计数
- [x] 4.5 新写入统一使用 `start_annotation_frame` / `end_annotation_frame`
- [x] 4.6 读取端兼容旧 `start_frame` / `end_frame`
- [x] 4.7 `annotated_ranges` 与 `analysis_ranges` 保持独立
- [x] 4.8 实现 `contiguous_ranges_cover()` 函数验证区间包含
- [x] 4.9 quality 检查：analysis_ranges 未被 annotated_ranges 覆盖时产生 `ANALYSIS_RANGE_NOT_COVERED`（blocking）
- [x] 4.10 `SEQUENCE_COVERAGE_LOW` 保持 info 级别，不阻止分析
- [x] 4.11 测试：稀疏帧生成多段区间
- [x] 4.12 测试：analysis_ranges 未被 annotated_ranges 覆盖时产生 blocking issue
- [x] 4.13 测试：等量但错位的区间产生 blocking 而非通过

## 5. Raw visibility contract — P1

- [x] 5.1 `RawCvatPoint.x` / `y` 改为 `float | None`
- [x] 5.2 新增 Pydantic validator 确保 missing 时 x/y 为 None，visible/occluded 时不为 None
- [x] 5.3 parser 对 `outside=1` 输出 `x=None, y=None, visibility="missing"`
- [x] 5.4 normalizer 不再承担 (0,0) → None 的哨兵转换
- [x] 5.5 测试：outside=1 产生 null 坐标
- [x] 5.6 测试：missing 点带坐标被 validator 拒绝

## 6. Harden parser implementation — P2

- [x] 6.1 移除 `ET.parse()` 完整 DOM 加载，仅使用单次 `ET.iterparse()`
- [x] 6.2 单次遍历同时读取 meta 和 tracks
- [x] 6.3 元素处理完毕后调用 `elem.clear()`
- [x] 6.4 保留 DTD/entity 安全拒绝逻辑
- [x] 6.5 移除 `MAX_TRACK_COUNT=200` 静默截断行为
- [x] 6.6 新增 `MAX_XML_FILE_SIZE_BYTES=100MB` 限制
- [x] 6.7 新增 `MAX_SKELETON_RECORDS=50000` 和 `MAX_ACTIVE_FRAMES=20000` 限制
- [x] 6.8 超限时直接 `parse_failed`，不返回部分数据
- [x] 6.9 测试：超过 200 个 one-frame track 仍完整解析
- [x] 6.10 测试：真正超限时阻断

## 7. Structured errors — P2

- [x] 7.1 `CvatParseError` 增加 `code`、`frame`、`track_ids` 结构化字段
- [x] 7.2 `MULTIPLE_ACTIVE_SKELETONS` 包含 frame 和 track_ids
- [x] 7.3 未知点名称记录 warning，不破坏 COCO 17 点
- [x] 7.4 API 层将结构化错误映射为响应体
- [x] 7.5 测试：多骨架返回结构化错误

## 8. Traceability metadata — P3

- [x] 8.1 写入 parser name/version/source_format
- [x] 8.2 `KeypointFrame` 增加 `source_track_ids: list[str]` 可选字段
- [x] 8.3 normalizer 从 `RawCvatKeypointFrame.source_track_ids` 传递到 `KeypointFrame.source_track_ids`
- [x] 8.4 写入 `contract_version: "cvat-import-contract.v1.1"`
- [x] 8.5 写入 frame_mapping 完整结果
- [x] 8.6 清理规格中残留的 v2 表述

## 9. Legacy record migration — P3

- [x] 9.1 审计既有 CVAT normalized annotation 的 frame_count 和 coverage 语义
- [x] 9.2 未重新 parse 的旧记录在 quality 中标记为 `stale_contract`
- [x] 9.3 通知策略：重新 parse 以刷新 contract_version 和帧语义

## 10. Golden fixture and regression — P3

- [x] 10.1 将真实 `annotations.xml` 缩减为稳定 golden fixture
- [x] 10.2 将 `instances_default.json` 保存为 companion manifest fixture
- [x] 10.3 记录预期基线：sequence size、annotated count、first/last frame、COCO 17 点覆盖、outside/occluded 分布
- [x] 10.4 验证真实 XML 解析得到预期有效骨架帧数
- [x] 10.5 验证每个有效完整帧包含 COCO 17 点
- [x] 10.6 验证 source video / annotation sequence / coverage 三类帧数不混淆
- [x] 10.7 验证 companion filename mapping 不被错误标记为 verified
- [x] 10.8 验证同一帧多个 active skeleton 明确阻断
- [x] 10.9 现有 Kinovea tests 全部通过
- [x] 10.10 后端全部 tests 通过
- [x] 10.11 `openspec validate harden-cvat-skeleton-import-contracts --strict`

## 1. Ownership Check Integration

- [x] 1.1 将 `parse_annotation_file` 中的裸 `db.get(AnnotationFile, annotation_file_id)` 替换为 `annotation_repository.get_with_ownership_check(db, annotation_file_id, current_user_id)`
- [x] 1.2 将 service 参数 `created_by` 重命名为 `current_user_id`，语义更准确
- [x] 1.3 更新 route 调用：`parse_annotation_file(db, annotation_file_id, current_user_id=current_user.id)`

## 2. Parser Service

- [x] 2.1 创建 `backend/app/services/parsers/__init__.py`
- [x] 2.2 创建 `backend/app/services/parsers/kinovea_parser.py`，定义 `KinoveaParseError` 异常和 `ParsedKinoveaAnnotation` Pydantic 模型
- [x] 2.3 实现 `parse_kinovea_json(file_path) → ParsedKinoveaAnnotation`：读取 JSON → 提取 events/keypoint_frames/trajectories/manual_tags/scale → 规范化
- [x] 2.4 实现 `parse_kinovea_csv(file_path, fallback_fps) → ParsedKinoveaAnnotation`：读取 CSV → 按 type 分派行 → 聚合 keypoint → 规范化
- [x] 2.5 实现事件名中英映射表（"入水" → "hand_entry" 等）和关键点别名映射表（"肩" → "right_shoulder" 等）
- [x] 2.6 实现 `resolve_time_sec(row, fps)` 推导逻辑
- [x] 2.7 实现 `build_semantic_warnings(events)` 检查推荐事件（hand_entry、catch_start、pull_end、cycle_start、cycle_end）
- [x] 2.8 实现 `build_parse_summary(parsed)` 生成 events/keypoint_frames/trajectories/manual_tags 计数
- [x] 2.9 实现 `parse_kinovea_annotation(file_path, file_type, fallback_fps) → ParsedKinoveaAnnotation` 调度函数

## 3. Service Integration

- [x] 3.1 在 `normalized_annotation_service.py` 中新增 `ParseAnnotationResult` 数据类（annotation + summary + warnings）
- [x] 3.2 修改 `parse_annotation_file`：对 `source=kinovea` 调用 `parse_kinovea_annotation`，对 `source=manual_json` 保持原有 JSON 路径
- [x] 3.3 将 parser 产出的 raw data 送交已有的 `evaluate_quality` + upsert 流程
- [x] 3.4 构造并返回 `ParseAnnotationResult`

## 4. Schema Extension

- [x] 4.1 在 `schemas/normalized_annotation.py` 中新增 `ParseSummary` 模型
- [x] 4.2 扩展 `ParseResponse`：增加 `annotation_file_id`、`source`、`summary`、`warnings`
- [x] 4.3 更新 `schemas/__init__.py` 导出 `ParseSummary`

## 5. Route Update

- [x] 5.1 parse endpoint 使用 `response_model=ParseResponse`
- [x] 5.2 route 调用 service 获取 `ParseAnnotationResult`，装配为 `ParseResponse` 返回
- [x] 5.3 保留 parse endpoint 的 201 状态码

## 6. Sample Data

- [x] 6.1 创建 `backend/samples/kinovea-side-freestyle.json` 示例（完整 Kinovea JSON）
- [x] 6.2 创建 `backend/samples/kinovea-side-freestyle.csv` 示例（固定列名 CSV）

## 7. Tests

- [x] 7.1 Parser 单元测试：解析有效 Kinovea JSON
- [x] 7.2 Parser 单元测试：解析有效 Kinovea CSV
- [x] 7.3 Parser 单元测试：CSV keypoint 行按 frame 聚合
- [x] 7.4 Parser 单元测试：time_sec 从 frame/fps 推导
- [x] 7.5 Parser 单元测试：缺少 fps 且无 fallback 时抛 KinoveaParseError
- [x] 7.6 Parser 单元测试：坐标字段非数字抛 KinoveaParseError
- [x] 7.7 Parser 单元测试：中文点名称映射到标准关键点
- [x] 7.8 Parser 单元测试：缺少 hand_entry 生成 semantic warning
- [x] 7.9 Parser 单元测试：CSV 缺少必要列抛 KinoveaParseError
- [x] 7.10 API 集成测试：parse CSV annotation file 成功，响应含 ParseResponse 所有字段
- [x] 7.11 API 集成测试：parse 成功后 annotation_file.status = parsed
- [x] 7.12 API 集成测试：parse 失败后 annotation_file.status = parse_failed + parse_error
- [x] 7.13 API 集成测试：重复 parse 同一个 annotation_file → revision += 1
- [x] 7.14 API 集成测试：无权限返回 404（ownership check）

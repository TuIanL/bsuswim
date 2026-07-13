## Why

Change #1 建立了 `annotation_files` 的持久化与上传能力，Change #2 建立了 `normalized_annotations` 标准化标注层。但两者之间仍有一个断点：`POST /annotations/{annotation_file_id}/parse` 对 CSV 类型标注文件返回 501，Kinovea 导出的原始标注文件无法自动转换为标准化标注。本 change 实现 Kinovea parser，打通"上传标注文件 → 解析 → NormalizedAnnotation → quality validation"的完整链路，使标注导入不再依赖手工 JSON。

## What Changes

- 新增 `backend/app/services/parsers/kinovea_parser.py`，支持 Kinovea JSON 和固定列名 CSV 两种格式的解析，输出 `ParsedKinoveaAnnotation` 纯数据对象
- Parser 负责格式解析、事件/关键帧/轨迹/人工标签标准化、`time_sec` 自动推导（由 `frame/fps` 补齐）、关键点别名映射、语义 warnings
- 替换 `parse_annotation_file` 中的 CSV 501 分支，接入 Kinovea parser；原有的 JSON/manual_json 路径保持不变
- 复用已有的 `annotation_repository.get_with_ownership_check` 替换裸 `db.get`，补上 parse endpoint 的权限校验
- 扩展 `ParseResponse` 增加 `annotation_file_id`、`source`、`summary`、`warnings`，route 使用 `response_model=ParseResponse`
- Quality checker 保持 source-agnostic 结构检查，不加游泳专项语义检查

## Capabilities

### New Capabilities
- `kinovea-annotation-import`: Kinovea 标注文件解析器，支持 JSON 和 CSV 格式，输出标准化标注数据

### Modified Capabilities
- `annotation-file-persistence`: `parse_annotation_file` 替换 CSV 501 分支，接入 Kinovea parser；parse endpoint 启用已有的 `get_with_ownership_check` 权限校验
- `normalized-annotation-schema`: `ParseResponse` 扩展 `annotation_file_id`、`source`、`summary`、`warnings`；parse route 使用 `response_model`

## Impact

- 受影响代码：`backend/app/services/parsers/`（新增）、`backend/app/services/normalized_annotation_service.py`（改造 CSV 分支）、`backend/app/api/routes/normalized_annotations.py`（扩展响应）、`backend/app/schemas/normalized_annotation.py`（扩展 ParseResponse）
- 不修改数据库表结构，不改 `annotation_files` 或 `normalized_annotations` 的 schema
- 不修改 quality checker 的检查逻辑，保持其 source-agnostic
- 前端 parse 响应结构变化（新增 `summary`、`warnings` 字段），但字段增量向后兼容

## Context

Change #1 建立了 `annotation_files` 的持久化能力，Change #2 建立了 `normalized_annotations` 标准化标注层。当前 `POST /annotations/{annotation_file_id}/parse` 对 JSON 文件已可解析，但对 CSV（典型 Kinovea 导出格式）直接返回 501。

本 change 在现有的 parse skeleton 上接入真正的 Kinovea parser，不新建表、不改 DB schema，只替换 `parse_annotation_file` 中"数据从哪里来"的部分。

## Goals / Non-Goals

**Goals:**
- 实现 Kinovea parser，支持 JSON 和固定列名 CSV 两种格式
- 将 parser 产物通过已有的 quality checker + upsert 流程写入 `normalized_annotations`
- 复用已有 `get_with_ownership_check` 替换裸 `db.get`
- 扩展 `ParseResponse` 并让 route 使用 `response_model`
- Parser 纯函数设计：file → data，不写数据库

**Non-Goals:**
- 不计算身体角度、肘角、膝角等指标
- 不生成 diagnostics 或 report
- 不做 AI 姿态识别或多机位融合
- 不支持万能 CSV（不支持变体列名或自动嗅探格式）
- 不修改 `annotation_files` 或 `normalized_annotations` 表结构
- Quality checker 不加游泳专项语义检查

## Decisions

### Decision 1: Use and extend ParseResponse

**选择**：扩展 `ParseResponse` 增加 `annotation_file_id`、`source`、`summary`、`warnings`，route 使用 `response_model=ParseResponse`

**替代方案**：继续手写 dict

**理由**：`ParseResponse` 已定义但未使用。扩展后 route 有类型安全，前端可依赖稳定的响应 schema。

### Decision 2: Trust annotation_file.file_type in MVP

**选择**：根据 `annotation_file.file_type` 选择 parser（`json` → JSON parser，`csv` → CSV parser），不做格式嗅探

**替代方案**：JSON 失败后 fallback CSV

**理由**：`file_type` 在上传时已识别。sniff 会模糊错误原因（file_type 错了 vs 文件坏了），增加测试矩阵。MVP 错误信息应引导用户检查 file_type。

### Decision 3: Quality checker stays structural, parser warnings are semantic

**选择**：`evaluate_quality()` 保持 source-agnostic 结构检查（fps、events、keypoint_frames、scale）。Kinovea 专项语义提醒（缺少 `hand_entry`、`catch_start` 等）在 parser 层生成 warnings，不阻塞 parse 成功

**理由**：quality checker 对所有 source 通用。游泳专项 domain knowledge 不应污染通用检查层。语义 warnings 通过 API 返回但不阻止 parse。

### Decision 4: Reuse existing ownership check

**选择**：`parse_annotation_file` 调用已有的 `annotation_repository.get_with_ownership_check(db, annotation_file_id, current_user_id)`，替换裸 `db.get`

**理由**：该函数已实现 `annotation → session_video → training_session → coach` 权限链路。不需要新建 repository。

### Decision 5: Infer time_sec during parser normalization

**选择**：CSV 行缺 `time_sec` 时，parser 通过 `frame / fps` 自动推导。推导逻辑属于 parser normalize 阶段，不进入 quality checker

**理由**：`time_sec` 是导出质量属性，不是标注语义属性。推导过程对下游（quality checker、metrics）透明。

### Decision 6: Parser returns plain data, service handles DB

**选择**：parser 返回 `ParsedKinoveaAnnotation`（Pydantic model，纯数据），service 负责 quality → upsert → commit

**理由**：保持 parser 可独立测试（不依赖 DB）。后续 Dartfish/AI parser 复用同一 service 流程。

### Decision 7: CSV uses fixed column names

**选择**：第一版 CSV 固定 11 列：`type, name, label, frame, time_sec, side, point, x, y, tag, severity, comment`。不支持列名变体

**理由**：基地试用追求可控。固定规范降低 parser 复杂度，错误信息明确。

## Risks / Trade-offs

- **[Risk] `file_type` 可能在上传时被误识别**（如 JSON 文件被标为 csv）→ parse 失败，错误信息引导用户检查 file_type。→ **Mitigation**：后续如果频繁出现，可加轻量 sniff（尝试 JSON parse，失败才按 CSV 处理）作为策略 B，但 MVP 不实现。

- **[Risk] CSV 列名变化导致 parse 失败**：教练或工具导出的 CSV 列名可能不同。→ **Mitigation**：parser 错误信息列出缺失的必要列名。后续可持续扩展 alias 映射。

- **[Risk] ParseResponse 扩展影响前端**：新增 `summary` 和 `warnings` 字段虽然向后兼容（增量字段），但若前端有严格 schema 校验可能报错。→ **Mitigation**：前端暂无 parse 响应消费者（parse endpoint 还是骨架），影响为零。

## Open Questions

- 无。所有设计决策已在 explore 阶段充分讨论并收敛。

## MODIFIED Requirements

### Requirement: Ingestion result is reloadable
摄取结果 SHALL 不依赖单次 HTTP 响应；前端在导入后进行质量修复时，刷新列表或详情仍 SHALL 能恢复当前 normalized annotation、revision、quality 和 analysis readiness。

#### Scenario: Page reload after successful ingestion
- **WHEN** 用户刷新上传页面
- **THEN** 列表响应 MUST 返回 `normalized_annotation_id`
- **AND** 返回 `quality_status`
- **AND** 返回 `analysis_readiness`
- **AND** 返回持久化的 parse warnings

#### Scenario: Page reload after quality repair
- **WHEN** 用户已保存一次或多次质量修复后刷新页面
- **THEN** 列表或详情 MUST 返回最新 `normalized_annotation_id` 和 `normalized_revision`
- **AND** quality MUST 对应最新 revision
- **AND** 页面 MUST 能继续打开质量修复工作台而不要求重新上传原始文件


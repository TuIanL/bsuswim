## MODIFIED Requirements

### Requirement: Ingestion result is reloadable
摄取结果 SHALL 不依赖单次 HTTP 响应，且标注列表响应 SHALL 提供刷新后恢复解析摘要、质量详情与四类模块可用状态所需的数据。

#### Scenario: Page reload after successful ingestion
- **WHEN** 用户刷新上传页面
- **THEN** 列表响应 MUST 返回 `normalized_annotation_id`
- **AND** 返回 `normalized_revision`
- **AND** 返回 `quality_status`
- **AND** 返回 `analysis_readiness`
- **AND** 返回持久化的 `parse_summary`
- **AND** 返回完整的 `quality` 报告
- **AND** 返回 `kinematics_module_readiness`（body_posture / upper_limb / lower_limb / head_trunk，状态为 ready|degraded|blocked）
- **AND** 返回持久化的 parse warnings

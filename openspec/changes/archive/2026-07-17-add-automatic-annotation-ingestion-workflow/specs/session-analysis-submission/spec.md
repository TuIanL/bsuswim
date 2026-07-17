## MODIFIED Requirements

### Requirement: Analysis submission requires explicit annotation selection

系统 SHALL 在分析提交时根据可用标注状态执行三态判断。

#### Scenario: Submittable annotations exist but no ID provided
- **WHEN** session 存在 quality 为 valid 或 warning 的侧视 NormalizedAnnotation
- **AND** `normalized_annotation_id` 未提供
- **THEN** 系统 MUST 返回 422
- **AND** 错误 code MUST 为 `ANNOTATION_SELECTION_REQUIRED`
- **AND** 错误 MUST 包含 `candidate_normalized_annotation_ids`

#### Scenario: Only invalid or failed annotations exist
- **WHEN** session 存在 NormalizedAnnotation
- **AND** 所有标注 quality 为 invalid 或 file_status 为 parse_failed
- **AND** `normalized_annotation_id` 未提供
- **THEN** 系统 MUST 返回 422
- **AND** 错误 code MUST 为 `ANNOTATION_INPUT_UNAVAILABLE`
- **AND** MUST NOT 静默执行 video-only

#### Scenario: No annotations at all, video-only compatible
- **WHEN** session 没有任何 NormalizedAnnotation
- **AND** `normalized_annotation_id` 未提供
- **THEN** 系统 MUST 允许 video-only 分析继续

#### Scenario: Explicit ID provided
- **WHEN** 调用方提供 `normalized_annotation_id`
- **THEN** 系统 MUST 使用该 ID 精确查找 NormalizedAnnotation
- **AND** MUST NOT 执行自动选择

### Requirement: Candidate query limited to side view

候选标注查询 SHALL 限定 `SessionVideo.view_type = "side"`。

#### Scenario: Front-view annotation not in candidates
- **WHEN** 正面视频存在 parsed 标注
- **AND** 侧视视频没有标注
- **THEN** 系统 MUST 允许 video-only
- **AND** MUST NOT 因正面标注的存在而要求选择

### Requirement: Invalid quality blocks analysis input

quality.status 为 invalid 的 NormalizedAnnotation SHALL 不作为分析输入。

#### Scenario: Invalid annotation excluded from candidates
- **WHEN** NormalizedAnnotation.quality.status = "invalid"
- **THEN** 系统 MUST 从候选列表中排除该记录
- **AND** MUST NOT 将其作为 fallback

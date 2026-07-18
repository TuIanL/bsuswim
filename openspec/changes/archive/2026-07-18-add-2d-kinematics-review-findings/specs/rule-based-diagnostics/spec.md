## ADDED Requirements

### Requirement: Rule registry supports declarative output_kind
`RuleRegistry` SHALL 支持在规则集元数据中声明 `output_kind`，取值为 `diagnostic` 或 `review_finding`。旧 `diagnostic` 规则集行为保持不变；公共结构化条件评估器（`evaluate_trigger` / `evaluate_severity_branch`）可被 `review_finding` 引擎复用。

#### Scenario: Diagnostic rule set keeps default kind
- **WHEN** 加载 `side_freestyle_v1` 且未显式声明 `output_kind`
- **THEN** 注册表 MUST 默认视为 `diagnostic`，行为与现有一致

#### Scenario: Review rule set declares review_finding
- **WHEN** 加载 `side_2d_kinematics_v1` 且声明 `output_kind: review_finding`
- **THEN** 注册表 MUST 读取该声明并计入规则版本元数据（含规则文件 checksum）

### Requirement: Engines reject mismatched rule sets
`RuleBasedDiagnosticsEngine` SHALL 只接受 `output_kind=diagnostic` 的规则集；`KinematicReviewFindingsEngine` SHALL 只接受 `output_kind=review_finding`。传入不匹配的规则包 MUST 返回 `rule_output_kind_mismatch` 错误。

#### Scenario: Review engine given diagnostic rule set
- **WHEN** 将 `side_freestyle_v1` 交给 `KinematicReviewFindingsEngine`
- **THEN** 引擎 MUST 拒绝并报 `rule_output_kind_mismatch`

#### Scenario: Diagnostic engine given review rule set
- **WHEN** 将 `side_2d_kinematics_v1` 交给 `RuleBasedDiagnosticsEngine`
- **THEN** 引擎 MUST 拒绝并报 `rule_output_kind_mismatch`

## ADDED Requirements

### Requirement: AI interpretation can ground narrative in optional visual evidence

系统 SHALL 允许支持视觉输入的 provider 使用当前报告的受控多模态证据包；视觉证据 SHALL 只辅助解释，不能成为生成数值、修改指标或确定性诊断的独立事实来源。

#### Scenario: Visual evidence is used in a valid interpretation
- **WHEN** provider 在视觉模式下生成并引用关键姿态图或时序图
- **THEN** 每个 `evidence_ref` SHALL 存在于本次输入 evidence manifest
- **AND** 每个包含指标值、阈值、帧号或技术含义的内容块 SHALL 仍包含有效 `fact_ref`
- **AND** 输出 SHALL 不得把视觉观察表述为确定性病因、伤病、能力缺陷或综合评分

#### Scenario: Output invents a visual numeric claim
- **WHEN** 输出包含无法由引用 fact 支撑的图像测量值、角度、次数、周期或阈值
- **THEN** 本地护栏 SHALL 拒绝该输出
- **AND** 系统 SHALL NOT 将其标记为 ready

### Requirement: Visual evidence participates in reproducibility and staleness

系统 SHALL 将实际使用的视觉模式、evidence manifest hash、证据资产版本和曲线摘要版本纳入解读 generation signature、trace 和审计记录。

#### Scenario: Evidence asset changes after an interpretation is ready
- **WHEN** 当前报告的已选证据资产、资产 generation signature 或曲线摘要版本发生变化
- **THEN** 既有解读 SHALL 被解析为 stale
- **AND** 重新生成 SHALL 使用新的 generation signature

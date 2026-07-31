## ADDED Requirements

### Requirement: Five-page report exposes optional AI interpretation separately from deterministic content

`side_2d_kinematics_5page_v1` 的读取模型 SHALL 可关联当前 AI 解读状态和 ready 内容，但确定性 `report_data`、五个 section、指标、发现、资产、质量说明和基础 generation signature SHALL 不因 AI 解读生成而被改写。

#### Scenario: Current ready interpretation exists

- **WHEN** 用户读取当前五页报告且存在匹配基础报告 generation signature 的 ready AI 解读
- **THEN** 响应 SHALL 包含该 AI 解读及其独立 generation signature 和追溯信息
- **AND** 基础报告 SHALL 仍包含恰好五个 section
- **AND** 基础报告 generation signature SHALL 保持不变

#### Scenario: No current ready interpretation exists

- **WHEN** AI 解读未配置、生成中、失败或 stale
- **THEN** 五页基础报告 SHALL 完整返回
- **AND** 响应 SHALL 暴露明确的 AI 解读状态
- **AND** SHALL NOT 用模板化占位内容伪装成 ready AI 解读

### Requirement: AI interpretation presentation preserves page ownership and report boundaries

五页报告的 AI 解读展示 SHALL 保持现有页面职责：总体通俗总结归属页面 1，身体与头躯干、上肢、下肢模块解释分别归属页面 2、3、4，优先关注项、条件式训练建议、复测目标和限制归属页面 5。

#### Scenario: AI interpretation is mapped to report pages

- **WHEN** ready AI 解读在 Web 或 PDF 中渲染
- **THEN** 页面 1 SHALL 只展示总体解释和 AI 来源状态
- **AND** 页面 2 至 4 SHALL 只展示与当前 source module 对应的模块解释
- **AND** 页面 5 SHALL 展示优先关注项、条件式训练建议、复测目标、限制和引用
- **AND** 报告 SHALL 继续保持五页，不得新增第六页

#### Scenario: AI content conflicts with deterministic report

- **WHEN** AI 解读中的引用或表述无法与当前报告事实一致
- **THEN** 渲染层 SHALL 忽略该 AI 解读并展示基础报告
- **AND** SHALL 显示结构化的 AI 内容不可用状态


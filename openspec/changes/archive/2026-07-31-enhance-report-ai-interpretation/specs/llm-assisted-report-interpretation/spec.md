## MODIFIED Requirements

### Requirement: AI interpretation output is structured and versioned

系统 SHALL 要求 provider 返回符合版本化 schema 的结构化输出，至少包含通俗总体总结、分模块解释、优先关注项、条件式训练建议、复测目标、限制说明以及事实、知识和证据引用。技术含义块 SHALL 能够独立表达客观观测、可能解释、潜在影响和行动建议；训练建议 SHALL 能够独立表达目标指标、练习、执行条件、剂量或强度、停止条件和复测标准。

#### Scenario: Valid interpretation is generated

- **WHEN** provider 返回通过 schema 和护栏校验的 v3 结构化结果
- **THEN** 系统 SHALL 保存 `plain_language_summary`
- **AND** SHALL 保存按 `body_posture_head_trunk`、`upper_limb`、`lower_limb` 分类的 `module_explanations`
- **AND** SHALL 保存 `priority_focus`、`training_suggestions`、`retest_targets` 和 `limitations`
- **AND** 每个技术含义块 SHALL 包含客观观测、可能解释、潜在影响或其明确不可用说明
- **AND** 每条训练建议 SHALL 包含目标指标、具体练习、执行条件和复测标准
- **AND** 每个产生技术含义的内容项 SHALL 至少包含一个有效 `fact_ref`
- **AND** 使用知识内容的训练建议 SHALL 至少包含一个有效 `knowledge_ref`

#### Scenario: Legacy interpretation is read

- **WHEN** 当前报告关联的 ready 解读使用 v1 或 v2 output schema
- **THEN** API、Web 和 PDF SHALL 继续读取并展示已有文本内容
- **AND** 系统 SHALL 不要求为历史解读补造结构化字段
- **AND** 重新生成后 SHALL 使用当前 v3 schema

#### Scenario: Model returns unsupported extra fields

- **WHEN** provider 返回 schema 未定义的决策字段、评分字段、阈值修改或未声明的结构化字段
- **THEN** 系统 SHALL 拒绝该输出
- **AND** SHALL NOT 将其标记为 ready

### Requirement: Generated claims remain grounded and non-diagnostic

系统 SHALL 在保存前校验 AI 解读中的引用、数值、置信度等级和表述边界，禁止大模型重算事实、修改规则结论、生成无依据评分或将待复核发现表述为确定性诊断。低置信度、仅待复核或不可用事实 SHALL 受到解释等级门控。

#### Scenario: Interpretation cites report facts

- **WHEN** 解读内容包含指标值、单位、置信度、证据帧、阶段、周期或规则发现
- **THEN** 对应 `fact_ref` SHALL 存在于本次输入 fact catalog
- **AND** 数值、单位、阶段/周期范围 SHALL 与引用事实一致
- **AND** SHALL NOT 引用其他报告或旧 revision 的事实

#### Scenario: Low-quality fact is used as a main conclusion

- **WHEN** 输出将 `unavailable`、`review_only` 或仅有低置信度事实作为主要技术结论或训练建议的唯一依据
- **THEN** 护栏校验 SHALL 失败
- **AND** 该输出 SHALL NOT 被标记为 ready

#### Scenario: Caution fact is used conditionally

- **WHEN** 输出引用 `caution` 事实
- **THEN** 内容 SHALL 明确保留复核条件和不确定性
- **AND** SHALL NOT 表述为确定病因、能力缺陷、必然因果或直接训练处方

#### Scenario: Interpretation overstates a review finding

- **WHEN** 输出将 `review_required` 发现改写为确定病因、能力缺陷、伤病结论或必然因果关系
- **THEN** 护栏校验 SHALL 失败
- **AND** 该输出 SHALL NOT 被展示或写入 ready 结果

#### Scenario: Interpretation invents a performance score

- **WHEN** 当前基础报告没有经过校准的综合技术评分
- **THEN** AI 解读 SHALL NOT 生成综合分数、运动员等级或优秀/一般/较差评级

### Requirement: Interpretation focus is selected deterministically

系统 SHALL 在 provider 调用前基于当前报告的发现状态、attention level、事实 availability、confidence、证据帧存在性和受限周期重复性生成最多三个稳定排序的 focus candidates。provider SHALL 只能解释这些 candidates，不得自行新增主要关注项。

#### Scenario: Focus candidates are built

- **WHEN** 当前报告准备生成 AI 解读
- **THEN** 系统 SHALL 为每个 candidate 保存稳定 ID、关联 fact refs、模块、排序和排序原因
- **AND** 排序 SHALL 使用版本化的确定性规则
- **AND** 无有效候选时 SHALL 记录空候选集并允许仅生成事实摘要

#### Scenario: Provider returns an unapproved priority

- **WHEN** `priority_focus` 不引用任何 focus candidate 关联事实，或引入 candidate 之外的主要技术问题
- **THEN** validator SHALL 拒绝该输出
- **AND** SHALL NOT 将其标记为 ready

### Requirement: Interpretation evidence and references are resolvable in reports

系统 SHALL 为 ready 解读生成非敏感 reference catalog，将 `fact_id`、`knowledge_id` 和 `evidence_id` 映射到报告页、模块、指标/发现标签、关键帧或时序图目标。catalog SHALL NOT 包含绝对路径、访问 token、原始视频或 provider 原始请求。

#### Scenario: User opens a valid reference

- **WHEN** Web 用户查看 ready 解读中的事实或证据引用
- **THEN** 系统 SHALL 显示可读标签并支持跳转到对应指标、发现、关键帧或时序图
- **AND** 跳转目标 SHALL 属于当前基础报告和当前 revision

#### Scenario: Reference cannot be resolved

- **WHEN** 输出引用的 fact、knowledge 或 evidence 不存在，或对应资产不属于当前报告 revision
- **THEN** validator 或 API 组装 SHALL 拒绝该 ready 输出
- **AND** 基础报告 SHALL 继续可读

#### Scenario: Print report renders references

- **WHEN** PDF 读取同一份 ready 解读
- **THEN** PDF SHALL 展示与 Web 相同的结构化内容和可读引用标记
- **AND** SHALL 不在打印期间调用 provider

### Requirement: Interpretation input includes bounded phase and cycle context when available

系统 SHALL 在报告已有阶段标签、代表帧、周期统计或曲线摘要时，将其以版本化、限长、可追溯的摘要投影给 provider；系统 SHALL 保留字段缺失和摘要不可用原因。

#### Scenario: Phase and cycle summaries exist

- **WHEN** 当前报告包含有效阶段或周期摘要
- **THEN** 输入 SHALL 包含阶段/周期 ID、范围、采样方式、重复性摘要和关联 fact/evidence refs
- **AND** provider SHALL 不接收完整逐帧关键点或未限制的原始曲线

#### Scenario: Phase or cycle summaries are unavailable

- **WHEN** 当前报告没有可靠阶段或周期摘要
- **THEN** 输入 SHALL 显式标记对应上下文 `not_available`
- **AND** AI 解读 SHALL NOT 生成未经引用支持的阶段、周期或重复性结论

## MODIFIED Requirements

### Requirement: Web and PDF use the same persisted interpretation

Web 报告和 PDF SHALL 读取同一份已持久化且通过校验的 ready AI 解读，包括 v3 结构化字段、generation signature 和 reference catalog；任何渲染路径 SHALL NOT 在读取或打印期间调用大模型。

#### Scenario: Ready interpretation is rendered

- **WHEN** 当前报告存在 ready AI 解读
- **THEN** Web 与 PDF SHALL 展示相同的 generation signature、总体总结、模块解释、结构化建议、复测目标、限制和可读引用

#### Scenario: Pending or failed interpretation is rendered

- **WHEN** AI 解读状态不是 ready
- **THEN** Web SHALL 展示对应的生成状态和基础报告
- **AND** PDF SHALL 导出基础五页报告并包含简短的 AI 解读不可用说明
- **AND** 两者 SHALL NOT 使用未通过校验的部分输出

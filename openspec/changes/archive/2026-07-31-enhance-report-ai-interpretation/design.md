## Context

当前 `llm-assisted-report-interpretation` 已经完成受控报告投影、知识库检索、像素指标归一化、视觉证据限制、事实引用校验和 Web/PDF 共用持久化结果。现有输出 schema 以 `text` 为主，虽然提示词要求“观测→可能解释→潜在影响→建议”，但结构校验和前端展示无法稳定表达这些层次。

本变更跨越后端投影、优先级计算、provider 输出校验、API 响应和前端报告渲染。基础五页报告仍是唯一事实来源，AI 只负责解释，不改变指标、规则发现或基础报告状态。

## Goals / Non-Goals

**Goals:**

- 用版本化结构表达技术观察、可能解释、潜在影响、训练建议和复测标准。
- 用确定性规则筛选有限的重点候选，再让模型在候选范围内组织语言。
- 将低置信度、不可用和待复核事实区分处理，避免其直接变成确定性训练结论。
- 让 Web 和 PDF 能根据稳定引用回到指标、发现、关键帧和时序图。
- 在报告已有数据时提供受限的动作阶段、周期和曲线摘要；缺失数据必须显式保留不可用状态。
- 保持现有 v1/v2 解读读取兼容、异步生命周期、权限控制、隐私边界和非诊断护栏。

**Non-Goals:**

- 不实现教练评分、人工反馈收集或自动评测闭环。
- 不要求接入个人历史报告，也不在本变更中实现跨报告趋势分析。
- 不生成综合技术评分、运动员等级、伤病结论或自动训练计划。
- 不发送原始视频、完整关键点或未筛选标注文件。
- 不引入向量数据库或替换当前知识库检索方式。

## Decisions

### 决策 1：输出 schema 采用版本化结构化扩展

新增 `swim-report-interpretation.v3`。技术解释块保留兼容的 `text` 和引用字段，同时增加结构化的 `observation`、`possible_explanations`、`potential_impact` 和 `action` 字段；训练建议增加 `goal`、`drill`、`dose_or_condition`、`stop_conditions` 和 `success_criterion`；复测目标增加当前事实引用、比较方向和成功判据。

读取端继续支持 v1/v2。v1/v2 内容按旧文本展示，v3 内容优先使用结构化字段。这样可以先升级后端和前端，再逐步切换 provider，不影响已保存的历史解读。

备选方案是只修改提示词继续输出长文本，成本较低，但无法可靠校验四层结构，也无法让前端对建议和证据进行精确展示，因此不采用。

### 决策 2：重点候选由后端确定，模型不得自由扩展

投影阶段新增 bounded focus candidates。候选由发现状态、attention level、事实 availability、confidence、证据帧存在性和跨周期重复性计算排序，最多保留三个，并带有稳定 candidate ID 和排序原因。

provider 只能从候选中生成 `priority_focus`。validator SHALL 检查每个重点块至少引用一个候选关联 fact，禁止模型凭空新增重点。排序规则使用稳定的显式权重，避免同一报告因模型随机性产生重点漂移。

备选方案是完全交给模型排序，表达灵活但重点不稳定；不采用。

### 决策 3：置信度分层在投影层完成，训练建议使用硬门控

每个事实在输入中增加解释等级：`primary`、`caution`、`review_only` 或 `unavailable`。availability 优先于 confidence；`unavailable` 不得成为技术判断依据，低置信度或 `review_only` 事实只能用于待复核说明。

训练建议至少引用一个可用的 metric、finding 或 retest fact；仅引用 `review_only` 或 `unavailable` 事实时 SHALL 被拒绝。若建议引用 `caution` 事实，必须包含复核条件，且不得使用确定性因果表述。

备选方案是只把 confidence 作为提示词文字，不做校验门控，实施简单但无法防止模型把低质量数据写成主结论；不采用。

### 决策 4：引用目录由服务端生成，模型只返回稳定 ID

AI 解读响应增加非敏感的 reference catalog。catalog 将 `fact_id`、`knowledge_id` 和 `evidence_id` 映射到报告页、模块、指标标签、发现标题、关键帧/曲线范围和可用跳转目标，不暴露绝对路径、token、原始请求或视频内容。

前端将引用渲染为可点击的报告内锚点；打印版使用简短引用标记。无法解析的引用不影响基础报告展示，但 ready 解读不得包含未解析引用。

备选方案是前端直接猜测 fact ID 与页面元素的关系，耦合高且容易在报告 profile 变化时失效；不采用。

### 决策 5：阶段与周期只投影受限摘要

projector 仅读取基础报告已有的阶段标签、代表帧、曲线摘要和周期统计，按配置限制数量和字符数。输入记录摘要来源、时间/帧范围、采样方式及缺失原因，不重新打开原始标注文件，也不将完整时序发送给 provider。

没有阶段或周期数据时，输入明确标记 `not_available`，模型不得自行补齐阶段或周期结论。

### 决策 6：Web/PDF 使用同一持久化 v3 结果

AI 生成仍然异步执行，Web 与 PDF 均只读取已通过 validator 的持久化结果。v3 结构化字段和 reference catalog 进入同一 generation signature；基础报告、证据资产或 prompt/schema 变化时旧解读进入 stale。

## Risks / Trade-offs

- **[旧数据兼容]** 历史 v1/v2 解读没有结构化字段 → 读取端提供明确的 legacy 展示分支，重新生成才产生 v3。
- **[模型输出变长]** 结构化字段可能增加 token 和超时概率 → 限制每模块、重点、建议和复测目标数量，沿用输入/输出预算和重试策略。
- **[重点规则过于机械]** 确定性排序可能遗漏教练认为重要的细节 → 将排序原因和候选事实提供给模型，但不允许扩展候选范围；后续可独立调整权重。
- **[引用目录与页面漂移]** 报告页面或资产 key 变化可能导致跳转失效 → catalog 使用稳定 fact/evidence ID，并在 API 组装时校验目标存在；无法解析时阻止 ready。
- **[数据缺失]** 部分报告没有阶段或周期摘要 → 保留 `not_available`，降级为指标和代表帧解释，不伪造阶段结论。
- **[PDF 空间有限]** 结构化内容可能造成页面溢出 → PDF 使用紧凑摘要和固定数量限制，继续执行现有五页布局预检。

## Migration Plan

1. 先扩展输入/输出 schema、validator 和持久化字段，保留 v1/v2 读取能力。
2. 实现 focus candidate、置信度分层和 bounded phase/cycle projection。
3. 更新 provider prompt 与 fake provider，生成并校验 v3 输出。
4. 扩展 API 的引用目录，更新 Web/PDF 组件和前端类型。
5. 用无资产、低置信度、不可用指标、待复核发现、阶段缺失和视觉模式样例验证降级行为。
6. 发布后若发现 v3 输出问题，可关闭自动生成并继续展示基础报告及历史 v1/v2 解读；不需要数据回滚。

## Open Questions

- focus candidate 的默认权重和 `caution` 置信度阈值需要在实现前根据当前 finding schema 固定，并写入版本化配置。
- 现有报告资产中哪些字段能够稳定提供周期边界，需要在实现期逐项盘点；无法稳定提供的字段应保持 `not_available`。
- v3 API 是否直接返回完整 reference catalog，还是仅返回当前页面所需的引用子集，需要结合响应体积决定。

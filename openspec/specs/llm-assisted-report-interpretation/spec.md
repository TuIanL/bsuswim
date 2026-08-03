# llm-assisted-report-interpretation Specification

## Purpose

定义基于已持久化五页运动学报告和经审核游泳知识库生成大模型辅助解读的输入边界、异步生命周期、结构化输出、事实护栏、审计追溯与 Web/PDF 展示约束。
## Requirements
### Requirement: AI interpretation consumes a controlled report projection

系统 SHALL 从已持久化的 `side_2d_kinematics_5page_v1` 基础报告构造版本化的 AI 解读输入，并且 SHALL NOT 将原始视频、完整逐帧关键点或未筛选标注文件发送给大模型 provider。

#### Scenario: Ready base report is projected

- **WHEN** 系统为当前基础报告生成 AI 解读
- **THEN** 输入 SHALL 只包含必要的运动员与测试上下文、报告指标、待复核发现、证据帧引用、质量说明、分析边界和检索到的知识条目
- **AND** 每个输入事实 SHALL 包含稳定的 `fact_id`、来源 key、值与单位（可用时）、可用性、置信度和来源定位
- **AND** 输入 SHALL 记录其 schema 版本和基础报告 generation signature

#### Scenario: Metric is unavailable

- **WHEN** 报告指标的 availability 为 `unavailable`
- **THEN** 输入 SHALL 保留该指标不可用及其原因
- **AND** SHALL NOT 将其投影为数值 `0`、估算值或可用于技术判断的事实

### Requirement: 像素距离指标在解读输入中归一化

系统 SHALL 在构造 AI 解读输入时读取基础报告的参考体长，为像素距离/波动指标派生归一化事实；AI 解读输出 SHALL NOT 以原始像素作为用户可见数值，且 SHALL 在参考体长不可用时仅允许定性描述。

#### Scenario: 髋部垂直波动指标被归一化

- **WHEN** 报告包含 `hip_vertical_range_px` 且 `reference_body_length_px` 可用
- **THEN** 解读输入 SHALL 同时包含原始 px 事实与归一化事实（`hip_vertical_range_norm`，值 = px ÷ 参考体长）
- **AND** 输入 SHALL 记录参考体长的来源与置信条件

#### Scenario: 输出泄露原始像素单位

- **WHEN** 解读文本含 `px` 或 `像素` 单位（含 `px/frame` 等派生像素单位）
- **THEN** 本地护栏 SHALL 拒绝该输出
- **AND** 系统 SHALL NOT 将其标记为 ready

#### Scenario: 像素速度指标归一化

- **WHEN** 报告包含 `px/frame` 单位的速度指标（如 `wrist_velocity_px_per_frame`）且参考体长可用
- **THEN** 解读输入 SHALL 派生 `*_norm` 归一化速度事实（体长/帧）
- **AND** 策略 SHALL 禁止输出 `px/frame` 原始单位

#### Scenario: 训练建议剂量数字豁免

- **WHEN** 训练建议在执行条件中包含剂量数值（如 `4×25米`、组数、次数、时长）
- **THEN** 该剂量数字 SHALL 被视为推荐内容，不要求可追溯到报告事实
- **AND** 报告指标值、比率、百分比、帧号等事实性数字仍 SHALL 要求事实引用

#### Scenario: 参考体长不可用

- **WHEN** `reference_body_length_px` 缺失、样本不足或不可靠
- **THEN** 输入 SHALL 不派生归一化事实，并在对应 px 事实的 limitations 注明"无法归一化，仅可定性描述"
- **AND** 策略 SHALL 仅允许定性表述（如"波动幅度较大"），SHALL NOT 输出具体像素数

### Requirement: AI interpretation has an asynchronous non-blocking lifecycle

系统 SHALL 在基础报告成功持久化后异步生成 AI 解读，并以 `not_configured`、`pending`、`generating`、`ready`、`failed` 或 `stale` 表示独立状态。

#### Scenario: Base report is persisted

- **WHEN** `annotation_kinematics` pipeline 成功持久化基础五页报告
- **THEN** pipeline SHALL 可在 AI provider 已配置时创建或复用对应的 AI 解读生成记录
- **AND** SHALL 在不等待模型返回的情况下完成基础分析任务
- **AND** 基础报告 SHALL 立即可读

#### Scenario: Provider is not configured

- **WHEN** 大模型 provider 或必要凭据未配置
- **THEN** AI 解读状态 SHALL 为 `not_configured`
- **AND** 基础报告生成、读取和 PDF 导出 SHALL 保持可用

#### Scenario: Model generation fails

- **WHEN** 模型调用超时、配额不足、返回无效结构或未通过护栏校验
- **THEN** AI 解读状态 SHALL 为 `failed`
- **AND** 系统 SHALL 保存结构化错误码和可重试性
- **AND** SHALL NOT 删除或修改最近一次 ready 解读
- **AND** SHALL NOT 将基础报告状态改为 partial 或 failed

### Requirement: AI interpretation output is structured and versioned

系统 SHALL 要求 provider 返回符合版本化 schema 的结构化输出，至少包含通俗总体总结、分模块解释、优先关注项、条件式训练建议、复测目标、限制说明以及事实和知识引用。

#### Scenario: Valid interpretation is generated

- **WHEN** provider 返回通过 schema 和护栏校验的结果
- **THEN** 系统 SHALL 保存 `plain_language_summary`
- **AND** SHALL 保存按 `body_posture_head_trunk`、`upper_limb`、`lower_limb` 分类的 `module_explanations`
- **AND** SHALL 保存 `priority_focus`、`training_suggestions`、`retest_targets` 和 `limitations`
- **AND** 每个产生技术含义的内容项 SHALL 至少包含一个有效 `fact_ref`
- **AND** 使用知识内容的训练建议 SHALL 至少包含一个有效 `knowledge_ref`

#### Scenario: Model returns unsupported extra fields

- **WHEN** provider 返回 schema 未定义的决策字段、评分字段或阈值修改
- **THEN** 系统 SHALL 拒绝该输出
- **AND** SHALL NOT 将其标记为 ready

### Requirement: Generated claims remain grounded and non-diagnostic

系统 SHALL 在保存前校验 AI 解读中的引用、数值和表述边界，禁止大模型重算事实、修改规则结论、生成无依据评分或将待复核发现表述为确定性诊断。

#### Scenario: Interpretation cites report facts

- **WHEN** 解读内容包含指标值、单位、置信度、证据帧或规则发现
- **THEN** 对应 `fact_ref` SHALL 存在于本次输入 fact catalog
- **AND** 数值与单位 SHALL 与引用事实一致
- **AND** SHALL NOT 引用其他报告或旧 revision 的事实

#### Scenario: Interpretation overstates a review finding

- **WHEN** 输出将 `review_required` 发现改写为确定病因、能力缺陷、伤病结论或必然因果关系
- **THEN** 护栏校验 SHALL 失败
- **AND** 该输出 SHALL NOT 被展示或写入 ready 结果

#### Scenario: Interpretation invents a performance score

- **WHEN** 当前基础报告没有经过校准的综合技术评分
- **THEN** AI 解读 SHALL NOT 生成综合分数、运动员等级或优秀/一般/较差评级

### Requirement: 解读策略允许有依据的实质技术解释并保持非诊断边界

系统 SHALL 允许 AI 在引用事实与知识条目前提下给出实质性技术解释，并 SHALL 强制采用"观测→可能解释→潜在影响→建议"的表述顺序；超出证据或知识的确定性因果、能力缺陷、伤病结论或未校准评分 SHALL 仍被拒绝。

#### Scenario: 有知识背书的解释被允许

- **WHEN** 输出在引用事实与知识条目前提下解释某指标组合的可能含义（含替代解释）
- **THEN** 该输出通过护栏校验并进入 ready 结果
- **AND** 相应内容块 SHALL 同时包含 `fact_ref` 与 `knowledge_ref`

#### Scenario: 无依据的确定性结论仍被拒绝

- **WHEN** 输出将单个二维指标直接判定为"力量不足""推进力不足""核心能力不足"或给出伤病/疾病名称
- **THEN** 护栏校验 SHALL 失败
- **AND** 系统 SHALL NOT 将其标记为 ready

#### Scenario: 四层表述顺序不满足

- **WHEN** 技术含义内容块直接给出结论而未先描述客观观测，或给出训练建议而未说明目标、练习与复测指标
- **THEN** 内容校验 SHALL 失败或降级该块进入待复核

### Requirement: Swimming knowledge is curated, versioned, and retrieved by relevance

系统 SHALL 只从已审核且处于 active 状态的版本化游泳知识条目中检索内容，并 SHALL 保留知识条目的稳定 ID、版本、适用范围、来源和审核状态。

#### Scenario: Relevant knowledge is retrieved

- **WHEN** 输入包含某个泳姿、指标 key、发现 code、运动员水平或训练目标
- **THEN** 检索器 SHALL 返回适用范围匹配的 active 知识条目
- **AND** SHALL 使用稳定排序和配置的数量上限
- **AND** 投影给模型的每个知识条目 SHALL 包含 `knowledge_id`、版本、摘要、适用条件、限制和来源标题

#### Scenario: No reviewed knowledge matches

- **WHEN** 没有 active 且适用的知识条目
- **THEN** 系统 SHALL 允许生成仅基于报告事实的解释
- **AND** SHALL NOT 让模型依赖未注册的训练处方知识
- **AND** 输出 SHALL 明确没有可引用的专项训练知识

#### Scenario: Knowledge version changes

- **WHEN** 已用于生成的知识库版本不再是当前版本
- **THEN** 既有解读 SHALL 保留并可追溯
- **AND** 系统 SHALL 将其识别为可重新生成
- **AND** SHALL NOT 静默改写既有 ready 输出

### Requirement: 知识检索按泳姿/机位过滤并解析指标别名

系统 SHALL 在知识检索时先按泳姿与机位硬过滤知识条目，再通过集中指标别名表解析知识条目指标名与实际事实 key 的匹配；当前分析链路无对应指标的知识条目 SHALL 标记为 inactive 且不参与检索。

#### Scenario: 指标别名命中

- **WHEN** 知识条目声明 `elbow_angle_deg`，而实际事实 key 为 `left_elbow_angle_deg` 与 `right_elbow_angle_deg`
- **THEN** 别名解析后 SHALL 判定为匹配并返回该条目
- **AND** 输入中的知识条目 SHALL 保留原始声明的指标名以供追溯

#### Scenario: 泳姿或机位不匹配

- **WHEN** 当前分析为 `side_2d` 而知识条目 `view` 仅含 `front`，或泳姿不匹配
- **THEN** 检索器 SHALL 排除该条目，不进入打分

#### Scenario: 当前链路无对应指标

- **WHEN** 知识条目仅引用 `swolf`、`lactate_*`、`vo2peak` 等当前管线不存在的指标
- **THEN** 该条目 SHALL 被标记为 inactive（或按 `applicable_pipelines` 标注）
- **AND** SHALL NOT 出现在检索结果中，即使指标存在部分交集

### Requirement: Interpretation generation is reproducible and auditable

每次 AI 解读生成 SHALL 保存基础报告 generation signature、输入 hash、provider、model、模型参数、提示词版本、输出 schema 版本、知识库版本、知识条目 ID、生成签名、状态、时间戳、错误信息和校验结果。

#### Scenario: Identical generation request is repeated

- **WHEN** 基础报告、输入投影、provider、model、模型参数、提示词和知识库版本均未变化
- **THEN** 系统 SHALL 计算相同的 generation signature
- **AND** 非 force 请求 SHALL 复用已有 ready 解读而不重复调用 provider

#### Scenario: Base report changes

- **WHEN** 当前基础报告 generation signature 与解读记录中的签名不同
- **THEN** 该解读 SHALL 被标记或解析为 `stale`
- **AND** SHALL NOT 作为当前报告的 ready AI 解读展示

### Requirement: Users can read and regenerate interpretation safely

后端 SHALL 提供读取 AI 解读状态和触发重新生成的鉴权 API，并 SHALL 对生成请求执行所有权检查、幂等控制和并发去重。

#### Scenario: Authorized user reads interpretation

- **WHEN** 有权访问 session 的用户读取报告
- **THEN** API SHALL 返回当前 AI 解读状态、ready 内容或结构化失败信息
- **AND** SHALL NOT 返回 provider 凭据、完整内部提示词或未经筛选的 provider 原始响应

#### Scenario: Authorized user requests regeneration

- **WHEN** 有权用户对当前报告请求重新生成 AI 解读
- **THEN** 系统 SHALL 创建或复用当前 generation signature 对应的生成任务
- **AND** 同一签名同时 SHALL 最多存在一个 generating 任务
- **AND** force 语义 SHALL 被显式记录

#### Scenario: Unauthorized user requests interpretation

- **WHEN** 用户无权访问目标 session
- **THEN** 读取和重新生成 API SHALL 拒绝请求
- **AND** SHALL NOT 泄露报告内容或生成状态

### Requirement: Sensitive data and provider payloads are minimized

系统 SHALL 使用服务端配置管理 provider 凭据，并 SHALL 对发送内容、日志和持久化原始响应执行数据最小化。

#### Scenario: Provider request is sent

- **WHEN** 系统调用外部大模型 API
- **THEN** 凭据 SHALL 只从服务端配置读取
- **AND** 请求 SHALL NOT 包含原始视频、完整标注、访问 token、存储绝对路径或无关个人信息
- **AND** 应用日志 SHALL NOT 记录 API key 或完整 provider 请求正文

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


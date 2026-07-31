## Context

当前 `annotation_kinematics` pipeline 依次生成运动学指标、可视化资产、规则型待复核发现和固定五页 `swim-report.v1`，然后将基础报告整体写入 `ReportMetadata.report_data`。这条链路具有确定性 generation signature、来源 revision、质量门控、证据帧和失败不吞咽约束，适合作为大模型解释的事实底座。

大模型引入了外部网络、非确定性输出、费用、延迟、隐私和事实幻觉等新的故障模式。AI 解读不能成为基础分析任务的必经步骤，也不能覆盖现有的指标、规则发现或报告 generation signature。目标用户包括教练和普通运动员：教练需要来源和边界，运动员需要通俗且可执行的表达。

## Goals / Non-Goals

**Goals:**

- 在基础报告完成后异步生成易懂、结构化、可引用的 AI 解读。
- 保持指标计算、规则判断、质量门控和五页报告结构的确定性。
- 允许替换大模型 provider，并对超时、重试、并发、成本和错误进行治理。
- 使用经审核、版本化、可追溯的游泳知识内容增强解释和训练建议。
- 让每条技术含义、数值和建议能够回指本次报告事实或知识条目。
- 让 Web 和 PDF 使用同一份持久化结果，并在 AI 不可用时无损降级。

**Non-Goals:**

- 不让大模型读取整段原始视频、完整标注文件或全部逐帧关键点。
- 不让大模型重算运动学指标、修改规则阈值、产生新的确定性诊断或自动综合评分。
- 不实现报告自由问答、实时流式对话、教练协同编辑或自动发布训练计划。
- 不进行模型微调，不在第一期引入向量数据库，也不建立未经审核的开放网络知识抓取。
- 不改变现有五页顺序、基础报告 schema 语义或 PDF 导出主链路。

## Decisions

### 1. 基础报告与 AI 解读分开持久化

新增独立的 `ReportInterpretation`（命名可在实现时贴合现有模型约定）记录，通过 `report_metadata_id` 和 `base_report_generation_signature` 关联基础报告。记录保存生命周期状态、解释内容、输入与配置 hash、模型追溯信息和错误信息。`ReportMetadata.report_data` 不因 AI 生成完成而整体改写。

这样可以保持基础报告的 last-successful-write 和 generation signature 语义，避免 AI 重试导致已导出 PDF 无意义地 stale，也允许保留最近一次 ready 结果用于审计。备选方案是直接把 AI 文本写入 `report_data`；该方案混合确定性与非确定性产物、增加并发覆盖风险，因此不采用。

### 2. 在基础报告提交后触发独立后台生成

pipeline 先持久化基础报告并完成原有成功语义，再通过独立生成服务创建 pending 记录并调度后台任务。后台执行 `pending → generating → ready/failed`，不复用 pipeline 的 `assembling_report` 事务。首期可复用项目现有后台任务机制，但领域服务不依赖 FastAPI `BackgroundTasks`，以便后续迁移到 Redis 队列或 worker。

自动触发与用户手动重新生成共用同一个幂等服务。同一 generation signature 通过唯一约束或带锁查询去重。备选方案是在 pipeline 内同步等待 provider；该方案会增加分析失败面和响应延迟，因此不采用。

### 3. 使用 allowlist 投影构造最小事实包

`InterpretationInputProjector` 从已持久化报告读取以下内容：必要的泳姿、运动员水平和测试上下文；各页面公开指标；review findings；证据帧定位；quality notes；analysis boundaries；复测指标。每项被规范化为稳定 `fact_id`，例如 `metric:body_angle_std_deg`、`finding:body_axis_variation_review`、`frame:body_axis_variation_review:0`。

`unavailable` 指标只作为限制事实出现，不携带伪造数值。输入不包含资产绝对存储路径、视频二进制、完整关键点、内部用户标识或 provider 无需知道的个人信息。备选方案是将完整 `report_data` 直接序列化给模型；该方案 token 成本更高且扩大隐私与提示注入面，因此不采用。

### 4. provider adapter 只接受和返回领域 schema

定义 provider-neutral adapter，输入为 system policy、结构化事实包、检索知识和严格 JSON Schema，输出为原始结构化对象及最小调用元数据。配置包含 provider、base URL、model、timeout、最大重试次数、temperature 和 token 上限，凭据只从服务端环境读取。

adapter 不负责业务校验；schema 解析、事实核验和护栏位于 provider 之外。第一期只需实现一个 provider adapter，但服务层不得引用该 provider 的专有响应类型。备选方案是把 SDK 调用散落在 pipeline 和 API route 中；该方案难以测试和替换，因此不采用。

### 5. 输出采用带引用的内容块而不是无约束长文本

解释 schema 使用内容项数组。每个 `summary_block`、`module_explanation`、`priority_focus`、`training_suggestion` 和 `retest_target` 都带 `fact_refs`；训练建议还带 `knowledge_refs`、适用条件和注意事项。顶层保存 `limitations` 与生成追溯。

所有技术含义块必须至少引用一个 fact。出现数值的文本必须与被引用事实的数值和单位一致；知识引出的训练周期、动作方式或安全注意事项必须引用知识条目。备选方案是仅生成 Markdown；Markdown 易展示但难以做逐条事实校验和稳定映射，因此不采用。

### 6. 保存前执行多层校验并采用全有或全无发布

校验顺序为：JSON Schema/Pydantic 校验 → fact/knowledge 引用存在性 → revision 与 signature 一致性 → 数值和单位一致性 → 禁止评分与确定性因果措辞 → 模块归属校验。任一层失败，当前 attempt 记为 failed，不发布部分内容；最近一次 ready 记录不被覆盖。

禁止断言词表复用并扩展现有 review finding 护栏，同时要求建议使用“可尝试”“建议教练结合原视频确认”等条件式语气。校验器输出结构化错误码，provider 原始输出默认不长期保存，只在开发配置下保留经脱敏的短期调试摘要。

### 7. 第一版知识库使用版本化条目和确定性标签检索

知识条目以仓库内受版本控制的 YAML/Markdown 或等价结构化注册表维护，字段包括 `knowledge_id`、version、title、summary、stroke_types、metric_keys、finding_codes、athlete_levels、training_goals、contraindications、source_title、source_locator、review_status 和 reviewed_at。只有 active 且 reviewed 的条目进入索引。

检索按泳姿、metric key、finding code、运动员水平和目标做加权标签匹配，结果按相关度、稳定 ID 排序并限制条数。知识库整体计算版本 hash，写入生成签名。该方案规模小、可解释、无需新基础设施；当知识量和召回评估证明有必要时，再增加 embedding 检索作为候选召回，但仍需适用范围过滤和稳定重排。

### 8. AI 生成签名独立于基础报告签名

AI generation signature 由基础报告 generation signature、输入 schema/version 与 hash、provider、model、推理参数、prompt policy version、output schema version、knowledge base version 和选中 knowledge IDs 共同计算。非 force 请求命中相同 ready signature 时直接复用。

基础报告变化时，旧解释按读取时解析为 stale；知识或提示词变化不删除旧结果，只允许重新生成。force 请求创建新的 attempt，但仍记录相同或新的 signature，便于审计实际调用。

### 9. 报告读取层组合结果，渲染层不调用模型

报告读取服务将基础五页报告与当前 interpretation 状态组合成 API 响应。总体总结映射到页面 1；三类模块解释映射到页面 2 至 4；关注项、训练建议、复测目标、限制和引用映射到页面 5。组合是读取投影，不回写基础 `report_data`。

Web 轮询或刷新状态；PDF 导出只读取导出开始时已持久化的 ready 结果。pending、failed、stale 或 not_configured 时，PDF 仍导出基础五页并写入简短状态说明。打印过程绝不触发模型调用，因此 Web/PDF 对同一 interpretation signature 保持一致。

### 10. API 和权限沿用报告所有权边界

在现有报告读取响应中增加可选 interpretation envelope，并提供读取状态与生成/重新生成 endpoint。route 通过当前 session/report 的既有所有权检查授权。服务端返回校验后的内容、追溯摘要和结构化错误，不返回 API key、完整内部 system prompt 或未经校验的 provider 原文。

生成 endpoint 使用幂等语义并限制同一报告的并发生成；实现阶段同时增加按用户或部署配置的速率限制与调用指标，避免重复点击造成费用放大。

## Risks / Trade-offs

- [模型仍可能生成语义上微妙但形式合法的错误解释] → 采用逐块事实引用、数值校验、禁止措辞和教练评测集；第一期明确标记“AI 辅助解读”。
- [异步任务在单进程重启后丢失] → 领域状态先持久化为 pending；首期提供可恢复扫描，生产部署可迁移到 Redis worker。
- [标签检索召回能力有限] → 保持知识规模精简并建立检索测试；只有在有评测证据后才引入 embedding。
- [外部 API 延迟、限流或费用不可控] → 基于 generation signature 缓存、限制输入和输出 token、配置超时重试、记录用量并提供关闭开关。
- [运动员信息发送给第三方带来隐私风险] → 默认只发送泳姿、水平等必要类别信息，不发送姓名、联系方式、视频和绝对路径；部署方需选择符合数据政策的 provider。
- [Web/PDF 内容增加导致五页溢出] → 使用固定内容上限、截断优先级和打印预检；完整引用可在 Web 展开，PDF 保留高优先级内容。
- [知识内容本身不准确或不适用] → 仅允许 reviewed/active 条目，保存来源、适用条件和版本，训练建议始终为条件式并保留注意事项。

## Migration Plan

1. 新增解释记录表、状态枚举和索引，不修改现有 `ReportMetadata.report_data` 数据。
2. 部署 provider-neutral 领域服务、输入投影、知识注册表、校验器和读取 API；默认功能开关关闭。
3. 加入一个 provider adapter 和服务端配置，在测试环境使用固定 fake provider 完成契约与失败降级验证。
4. 部署前端和 PDF 的可选 interpretation envelope 兼容读取；历史报告显示 not_configured 或 unavailable，不需要数据回填。
5. 小范围启用自动生成，记录事实校验失败率、延迟、token、费用和教练审核反馈，再逐步扩大。
6. 回滚时关闭自动生成与重新生成 endpoint；保留解释记录用于审计，基础报告与 PDF 链路不受影响。

## Open Questions

- 第一批知识条目的权威来源、授权范围和教练审核责任人尚需确定。
- 生产环境首选 provider/model、数据保留政策和单报告费用上限尚需确定。
- AI 训练建议是否默认对运动员展示，还是先仅对教练展示并由教练确认后发布。
- 首期后台执行使用现有进程内机制还是直接接入 Redis worker，需要结合当前部署拓扑决定。

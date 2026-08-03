## 1. 扩展解读契约与持久化模型

- [x] 1.1 将 `InterpretationInput` 升级为可表达 focus candidates、事实解释等级、阶段/周期摘要的版本化 schema，并保持 v1/v2 输入兼容。
- [x] 1.2 新增 v3 结构化输出模型，拆分技术解释层次，补充训练建议的目标、练习、剂量/条件、停止条件和成功标准。
- [x] 1.3 扩展复测目标与 reference catalog 模型，确保引用只暴露当前报告内的非敏感元数据。
- [x] 1.4 更新 `ReportInterpretation` 持久化字段、迁移和 serializer，使 v1/v2 历史记录可读、v3 记录可审计。
- [x] 1.5 更新 generation signature，使输出 schema、focus candidate 规则、阶段/周期摘要和 reference catalog 版本变化可触发 stale。

## 2. 构造受控上下文与确定性重点

- [x] 2.1 在 projector 中根据 availability、confidence 和 finding 状态生成 `primary`、`caution`、`review_only`、`unavailable` 解释等级。
- [x] 2.2 实现版本化 focus candidate scorer，综合 attention level、事实质量、证据帧、重复性和模块覆盖，稳定返回最多三个候选及排序原因。
- [x] 2.3 从当前报告已有字段投影限长的动作阶段、周期范围、重复性和曲线摘要，并保留采样方式与缺失原因。
- [x] 2.4 扩展 evidence/reference resolver，将事实、知识、关键帧、时序图和报告页映射为可解析的稳定引用目录。
- [x] 2.5 增加输入大小、候选数量、阶段/周期条目数量、曲线点数和引用目录大小限制，确认不读取原始视频或完整标注。

## 3. Provider 提示词与本地护栏

- [x] 3.1 更新系统策略和 output schema prompt，要求模型严格返回 v3 结构化内容并只能解释 focus candidates。
- [x] 3.2 约束训练建议必须包含目标、具体练习、执行条件、停止条件和复测标准，并继续要求知识引用和非诊断表述。
- [x] 3.3 扩展 validator，校验四层解释完整性、训练建议字段、低质量事实门控、focus candidate 归属、阶段/周期数值和引用目录一致性。
- [x] 3.4 更新 Qwen/兼容 provider 的请求和响应解析，保持结构化 JSON、超时、重试、失败状态和敏感数据最小化行为。
- [x] 3.5 更新 `FakeProvider` 及对抗样例，覆盖无候选、低置信度、不可用指标、阶段缺失、未授权重点、无依据训练建议和旧版本输出。

## 4. API、Web 与 PDF 展示

- [x] 4.1 扩展后端解读 envelope，返回 v3 内容、generation signature、状态和当前报告对应的 reference catalog。
- [x] 4.2 更新前端类型和报告 adapter，兼容 v1/v2 文本解读，并识别 v3 结构化字段。
- [x] 4.3 重构 `AIInterpretationPanel`，分层展示观测、可能解释、潜在影响、训练目标、动作、执行条件、停止条件和复测标准。
- [x] 4.4 渲染 `cautions`、低置信度/待复核状态和使用边界，不把不可用事实显示为数值。
- [x] 4.5 将 fact、knowledge、evidence 引用渲染为可读标签和报告内锚点，支持跳转到指标、发现、关键帧和时序图。
- [x] 4.6 更新打印报告，使用与 Web 相同的持久化 v3 内容和引用标记，并保持五页布局、溢出预检和无 provider 调用。

## 5. 测试与兼容性验证

- [x] 5.1 增加 projector 和 focus scorer 单元测试，覆盖稳定排序、模块覆盖、质量等级、阶段/周期摘要和输入预算。
- [x] 5.2 增加 schema/validator 测试，覆盖四层缺失、建议字段缺失、低质量事实越权、未授权 priority、幻觉数值和引用失效。
- [x] 5.3 增加 provider contract 测试，验证 v3 JSON 输出、视觉/文本模式、重试失败和 v1/v2 读取兼容。
- [x] 5.4 增加 API 权限、reference catalog 当前 revision、stale signature 和历史解读读取测试。
- [x] 5.5 增加前端组件测试，验证 v3 分层展示、警示条件、引用跳转、旧版本兼容和各状态不展示部分输出。
- [x] 5.6 增加 Web/PDF 一致性测试，验证结构化内容、引用标记、generation signature 和五页输出一致。
- [x] 5.7 运行后端解读测试、前端测试、类型检查、生产构建和 OpenSpec 校验，记录迁移前后兼容结果。

## 6. 发布与回滚

- [x] 6.1 增加 v3 解读的功能开关和配置说明，默认保留基础报告可用性。
- [x] 6.2 在开发环境用正常、低置信度、不可用、无资产、阶段缺失和视觉证据样例完成冒烟验证。
- [x] 6.3 更新 AI 解读运维文档，说明 v3 schema、引用目录、stale 条件、失败码和回滚路径。
- [x] 6.4 验证关闭 v3 自动生成后，基础 Web 报告、历史解读读取和五页 PDF 导出仍然可用。

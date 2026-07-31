## 1. 实现边界与配置

- [x] 1.1 确定首期 provider/model、数据保留策略、单报告 token/费用上限和功能开关默认值，并记录部署配置约定
- [x] 1.2 确定首期后台执行机制和 pending 任务恢复策略，保证领域服务不依赖具体 Web 调度实现
- [x] 1.3 确定 AI 训练建议的可见角色策略，默认采用仅教练可见或明确标记为 AI 辅助建议
- [x] 1.4 在服务端配置中加入 provider、base URL、model、API key、timeout、retry、temperature、token 上限、自动生成开关和调试保留开关
- [x] 1.5 增加配置测试，验证未配置、无凭据和功能关闭时统一解析为 `not_configured` 且不泄露密钥

## 2. 数据模型与迁移

- [x] 2.1 定义 AI 解读状态、输出 schema、追溯 schema、错误 schema 和 API envelope 的 Pydantic 模型
- [x] 2.2 新增 `ReportInterpretation` 持久化模型，保存 report 关联、基础报告签名、输入 hash、生成签名、provider/model/参数、提示词与知识库版本、内容、状态、校验结果、错误和时间戳
- [x] 2.3 设计并实现同一报告和 generation signature 的幂等/并发唯一约束，以及读取当前 ready attempt 所需索引
- [x] 2.4 创建 Alembic migration，并验证 upgrade/downgrade 不修改既有 `ReportMetadata.report_data`
- [x] 2.5 增加模型与迁移测试，覆盖状态持久化、ready 保留、failed attempt 和历史报告无解释记录的情况

## 3. 受控事实输入投影

- [x] 3.1 定义版本化 interpretation input schema 和稳定 `fact_id` 命名规则
- [x] 3.2 实现基础报告 allowlist projector，提取必要上下文、指标、review findings、证据帧、质量说明、分析边界和复测指标
- [x] 3.3 对 `unavailable` 指标实现无数值投影，并保留结构化原因；禁止将缺失值映射为 0 或估算值
- [x] 3.4 实现模块归属、来源定位、confidence、unit、revision 和基础报告 generation signature 的事实目录投影
- [x] 3.5 增加隐私最小化测试，证明投影不含姓名、联系方式、视频内容、完整关键点、访问 token、绝对路径或无关内部 ID
- [x] 3.6 增加稳定序列化和 input hash 测试，验证相同基础报告产生相同事实包和 hash

## 4. 游泳知识注册与检索

- [x] 4.1 定义知识条目 schema，包含稳定 ID、版本、摘要、泳姿、指标、发现、运动员水平、目标、禁忌/限制、来源和审核元数据
- [x] 4.2 建立版本控制的知识注册表与加载器，只接受 schema 合法且 reviewed/active 的条目
- [x] 4.3 与教练或指定审核责任人确定首批知识来源和授权范围，并录入覆盖身体姿态、上肢、下肢和复测建议的最小知识集
- [x] 4.4 实现基于泳姿、metric key、finding code、运动员水平和训练目标的加权标签检索、适用范围过滤、稳定排序和数量上限
- [x] 4.5 计算知识库版本 hash，并将选中知识 ID/版本纳入生成输入和 generation signature
- [x] 4.6 增加知识 schema、审核过滤、适用范围、稳定排序、无匹配降级和版本变化测试

## 5. Provider、提示词与结构化输出

- [x] 5.1 定义 provider-neutral adapter protocol、请求/响应类型和结构化 provider 错误分类
- [x] 5.2 实现 deterministic fake provider，覆盖正常输出、超时、限流、无效 JSON、额外字段和断言性内容场景
- [x] 5.3 实现首个真实 provider adapter，支持严格结构化输出、timeout、有限重试和最小调用元数据采集
- [x] 5.4 编写版本化 system policy 和 prompt builder，明确事实不可修改、不得评分、不得确定性诊断、建议需条件化和逐块引用
- [x] 5.5 确保 provider 请求仅包含受控事实包、检索知识和输出 schema，日志不记录 API key、完整请求正文或未经脱敏的原始响应
- [x] 5.6 增加 adapter 契约测试，确保领域服务不依赖 provider 专有类型并正确归类可重试与不可重试错误

## 6. 事实校验与内容护栏

- [x] 6.1 实现严格输出 schema 校验，拒绝未知评分、诊断、阈值修改和其他未定义决策字段
- [x] 6.2 实现 fact/knowledge 引用存在性、基础报告 signature/revision 一致性和模块归属校验
- [x] 6.3 实现文本数值与单位校验，确保出现的报告数字与所引事实一致，并允许知识引用支持的训练参数
- [x] 6.4 扩展禁止断言护栏，拒绝确定病因、能力缺陷、伤病判断、必然因果和未经校准的综合评分/等级
- [x] 6.5 实现全有或全无发布语义，校验失败时保存结构化错误但不发布部分输出、不覆盖最近一次 ready 解读
- [x] 6.6 增加对抗性测试，覆盖虚构指标、跨报告引用、unavailable 当 0、错误单位、无来源训练建议、隐藏评分和断言性改写

## 7. 生成签名与领域服务

- [x] 7.1 实现独立 AI generation signature，纳入基础报告签名、输入 hash、provider/model/参数、prompt、输出 schema、知识库版本和知识 ID
- [x] 7.2 实现创建或复用生成记录的幂等服务，非 force 请求命中相同 ready 签名时不调用 provider
- [x] 7.3 实现 `pending → generating → ready/failed` 执行服务、有限重试、错误落库和最近一次 ready 结果保留
- [x] 7.4 实现基础报告签名变化后的 stale 解析，以及提示词/知识库变化后的可重新生成判断
- [x] 7.5 实现 pending/generating 任务的启动恢复或超时回收逻辑，避免进程重启后永久卡住
- [x] 7.6 增加领域服务事务、并发去重、force attempt、缓存复用、stale 和失败不覆盖测试

## 8. Pipeline 与鉴权 API 集成

- [x] 8.1 在基础五页报告成功提交后触发非阻塞 AI 解读调度，确保原 pipeline 不等待 provider 且 AI 失败不改变基础任务结果
- [x] 8.2 为历史报告和未配置部署实现统一 `not_configured`/无记录读取投影，不执行数据回填
- [x] 8.3 扩展报告读取服务，用读取时组合方式返回基础报告和当前 interpretation envelope，不回写 `report_data`
- [x] 8.4 新增 AI 解读状态读取和生成/重新生成 API，复用 session/report 所有权检查
- [x] 8.5 为生成 API 实现幂等、并发限制、force 审计和按用户/部署配置的速率限制
- [x] 8.6 确保 API 不返回 provider 凭据、完整内部提示词或未经校验的原始响应
- [x] 8.7 增加 API 与 pipeline 集成测试，覆盖授权、越权、自动触发、手动重试、并发请求、未配置、超时和基础报告即时可读

## 9. Web 报告体验

- [x] 9.1 扩展前端 ReportData 类型和归一化层，兼容 interpretation 缺失及全部生命周期状态
- [x] 9.2 在页面 1 展示 ready 总体通俗总结和 AI 来源状态，并为 pending/failed/not_configured/stale 提供紧凑状态
- [x] 9.3 在页面 2 至 4 按 source module 展示对应模块解释，不跨模块复制内容
- [x] 9.4 在页面 5 展示优先关注项、条件式训练建议、复测目标、限制以及可展开的事实/知识来源
- [x] 9.5 为有权限用户增加重新生成命令、进行中防重复和完成/失败刷新行为
- [x] 9.6 保证 AI 内容不可用或校验冲突时完整展示基础五页报告，不渲染 provider 部分输出
- [x] 9.7 增加前端单元与组件测试，覆盖所有状态、长中文内容、引用展开、角色可见性和五页模块映射

## 10. PDF 一致性与布局

- [x] 10.1 让 print route 读取与 Web 相同的持久化 ready interpretation signature，打印时禁止触发 provider
- [x] 10.2 将总体、模块和页面 5 内容按既定页面职责加入打印布局，继续保持恰好五页
- [x] 10.3 对非 ready 状态导出基础报告和简短不可用说明，不包含未校验或部分生成内容
- [x] 10.4 设置每类 AI 内容的打印上限和优先级，处理长中文、来源列表和分页溢出
- [x] 10.5 增加 Web/PDF 内容一致性、五页数量、非 ready 降级和打印溢出预检测试

## 11. 评测、可观测性与文档

- [x] 11.1 建立固定报告事实包与教练期望的 AI 解读评测集，覆盖正常、低置信度、缺失数据、空 findings 和高风险措辞场景
- [x] 11.2 增加事实引用覆盖率、事实一致性、护栏拒绝率、延迟、重试、token 和估算费用指标
- [x] 11.3 运行后端、前端、pipeline、PDF 和对抗性测试，并记录第一期质量门槛与已知限制
- [x] 11.4 更新 `.env.example`、部署说明、API 文档、知识条目审核流程、隐私边界和故障排查文档
- [ ] 11.5 在小范围功能开关下进行教练审核试运行，记录可读性、正确性、建议可执行性和误导性反馈
- [ ] 11.6 根据试运行结果确定逐步放量或关闭策略，并验证关闭 AI 功能后基础报告与 PDF 完全可用

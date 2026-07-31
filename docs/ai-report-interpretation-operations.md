# AI 报告解读部署、审核与试运行

## 首期部署约定

AI 解读是可选增强，`AI_INTERPRETATION_ENABLED=false` 和
`AI_INTERPRETATION_AUTO_GENERATE=false` 为生产默认值。默认 adapter 使用
`qwen`，默认模型为 `qwen-plus`，通过阿里云业务空间的 OpenAI-compatible endpoint
调用并要求 `json_object` 输出；返回后仍经过本地严格 schema 和事实护栏。测试环境使用
`fake` provider。替换模型后必须重新执行固定评测与教练试运行。

`qwen-plus` 当前按文本模型配置。仅当部署者同时确认目标 Qwen 模型支持图片输入和
结构化 JSON 输出，并设置 `AI_INTERPRETATION_VISUAL_ENABLED=true`、
`AI_INTERPRETATION_MODEL_SUPPORTS_VISION=true`、
`AI_INTERPRETATION_MODEL_SUPPORTS_STRUCTURED_OUTPUT=true` 时，系统才会发送关键姿态图
和时序图。否则会明确按文本事实模式生成，绝不伪称图像已经被模型分析。

单报告默认限制为 24,000 输入事实字符、最多 6 条知识内容、120 秒超时和 2 次重试。
DeepSeek 思考模式默认开启，且不发送 `max_tokens`，输出长度采用 provider 默认值。因此
0.02 美元只用于调用前的输入费用检查，不能构成输出费用硬上限；系统会在调用后记录实际费用。
DeepSeek V4 Flash 的
cache-miss 输入价 0.14 美元/百万 token、输出价 0.28 美元/百万 token 只是预算参数，
provider 调价后必须同步更新。
超出输入或预估费用上限的请求在调用 provider 前失败。

每个用户每小时默认最多发起 10 个生成 attempt。相同签名的非 force 请求会复用，
但 force 请求计入限额。自动生成仅在基础报告提交并标记完成后调度，不阻塞基础报告。

## 数据保留与隐私边界

发送给 provider 的内容只包含泳姿/水平/距离/视角、公开指标、规则型待复核发现、
证据帧编号、质量边界、复测事实和检索到的已审核知识。视觉模式额外发送当前报告中
已选择的派生关键姿态图和时序图，以及限长、下采样的曲线摘要；每个证据均带 asset
hash、revision、关联 facts 和选择理由。不得发送姓名、联系方式、原始视频、完整标注、
完整关键点、访问 token、绝对路径或无关内部 ID。

可用 `backend/scripts/configure_qwen_from_csv.py` 将阿里云导出的双列 API key CSV 写入
被 Git 忽略的 `backend/.env`。脚本不打印 key，默认设置 `qwen-plus` 和关闭视觉模式：

```bash
cd backend
python scripts/configure_qwen_from_csv.py --csv /path/to/api-key.csv
```

系统持久化结构化且通过校验的解读、引用、provider/model、签名、用量、错误码和
时间戳。provider 原始请求和原始响应不持久化，`DEBUG_RETENTION` 首期必须保持
false。解释记录随基础报告删除而级联删除；数据库备份保留期沿用报告数据政策。
第三方 provider 自身的数据保留、训练使用、地域和删除政策必须由部署责任人另行确认。

## 知识条目审核

知识文件位于 `backend/app/services/report_interpretation/knowledge/`。新增或修改条目时：

1. 使用稳定 `knowledge_id`，内容变化时提升 `version`。
2. 填写适用泳姿、指标、finding、运动员水平、目标、禁忌、来源和定位信息。
3. 由指定教练或审核责任人核对准确性、授权范围与适用边界。
4. 仅在 `review_status=active` 且 `reviewed_by/reviewed_at` 完整后合入。
5. 运行 `PYTHONPATH=. pytest -q tests/test_report_interpretation.py`，确认 schema、稳定排序、版本 hash 和护栏。

知识库版本变化不会静默修改旧结果，只会使报告具备重新生成条件。

## 可观测性与质量门槛

每次 attempt 的 `validation_result` 保存块级 grounding coverage、fact catalog coverage、
fact consistency 和 guardrail rejection；`usage` 保存延迟、重试、输入/输出/总 token
及估算费用。`summarize_observability` 可按部署监控窗口汇总失败率、护栏拒绝率、
平均引用覆盖、延迟、重试、token 和费用。

首期进入教练试运行前的门槛：

- 固定评测和对抗性测试的事实一致性必须为 100%。
- 已发布内容的块级事实引用覆盖率必须为 100%。
- 虚构数值、无效引用、确定性诊断、隐藏评分必须全部被拒绝。
- AI 失败、超时、未配置或 stale 时，基础 Web 报告和五页 PDF 必须完整可用。
- Web 与 PDF 必须读取同一个 interpretation generation signature。

已知限制：当前标签检索不使用 embedding；进程内调度不适合多实例生产；字符到 token
的预算换算是保守估算，最终账单以 provider 为准；结构护栏不能替代教练对微妙语义和
训练可执行性的审核；首期不支持自由问答或自动训练计划。

### 2026-07-30 工程验证记录

- 后端全量：470 passed、1 skipped；跳过项是仅在显式 `DATABASE_URL` 环境运行的既有真实 PostgreSQL 诊断集成门禁，本轮其余数据库测试已连接 Docker PostgreSQL。
- 前端全量：9 个文件、44 个测试通过；AI 状态、五页映射、Web/打印一致性和溢出预检均在内。
- 前端生产构建：`vue-tsc --noEmit && vite build` 通过。
- pipeline、PDF 与对抗性用例包含在后端/前端全量结果中；固定 AI 评测覆盖正常、低置信度、缺失数据、空 findings 和风险措辞。
- 非阻断警告：既有 pipeline 仍有 `datetime.utcnow()` 弃用提示；既有 Vue 测试存在组件 stub/lifecycle 警告；主 bundle 超过 500 kB。这些不改变本期 AI 解读行为，但应进入后续技术债计划。

## 故障排查

| 状态/错误 | 含义 | 处理 |
|---|---|---|
| `not_configured` | 功能关闭、缺模型或缺凭据 | 检查开关和服务端环境变量；基础报告无需处理 |
| `provider_timeout` | provider 超时且有限重试耗尽 | 检查网络/限额，稍后手动重试 |
| `provider_unavailable` | 429 或服务端错误 | 检查配额，避免 force 连续点击 |
| `provider_output_truncated` | 模型输出达到 token 上限，JSON 未闭合 | 提高输出上限或收紧提示词后重新生成 |
| `provider_empty_response` | JSON Output 偶发返回空内容 | 重新生成；持续发生时检查模型状态和提示词 |
| `interpretation_rate_limited` | 用户小时限额已用完 | 等待窗口恢复或由运维调整限额 |
| `interpretation_input_too_large` | 受控事实包仍超过输入限制 | 检查报告异常膨胀，不要直接提高限制 |
| `interpretation_cost_limit_exceeded` | 最大预估费用超过上限 | 核对单价、模型和 token 配置 |
| `output_schema_invalid` | provider 未返回严格结构 | 核对模型结构化输出支持情况 |
| `grounding_reference_invalid` / `numeric_claim_ungrounded` | 引用或数值不一致 | 保留失败记录，检查 prompt/provider，不发布部分内容 |
| `assertive_claim_forbidden` | 出现诊断、能力缺陷或必然因果措辞 | 保留失败状态，由教练审阅后再调整策略 |
| `stale` | 基础报告已变化 | 对当前报告重新生成；旧记录仅用于审计 |

## 教练试运行记录

试运行必须在小范围账号和功能开关下进行，逐份对照基础指标、原视频和知识引用。
未完成本表前不得默认开启自动生成。

| 日期 | 教练/审核人 | 样本范围 | 可读性 | 正确性 | 建议可执行性 | 是否存在误导 | 处置 |
|---|---|---|---|---|---|---|---|
| 待填写 | 待指定 | 正常/低置信度/缺失/无 finding/风险措辞 | 待评 | 待评 | 待评 | 待评 | 待决策 |

放量决策需记录：样本数、严重事实错误数、误导性建议数、护栏漏检、provider 成本和
回滚负责人。任何严重事实错误或确定性诊断漏检都应关闭自动生成。关闭两个功能开关后，
需要再次验证基础报告读取和五页 PDF 导出；已保存解释记录只保留审计，不触发新调用。

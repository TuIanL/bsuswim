# Design: improve-report-ai-interpretation

## 决策 D1：归一化指标在投影层派生，而非指标计算层

**决策**：本轮在 `projector.py` 构造 AI 输入时，读取 `AnnotationContext.reference_body_length_px`，为像素距离/波动指标派生归一化事实（新增 `InterpretationFact`，`source_key` 使用 `*_norm`，值 = px / 参考体长），作为既有 px 事实的补充。不修改指标计算器。

**理由**：
- `reference_body_length_px` 已在 `frame_resolver.py:compute_reference_body_length()` 计算并存入 `AnnotationContext`，但解读投影层此前未读取——脚手架已存在，投影层改动最小。
- 本轮目标是把"AI 输出"修正，投影层派生即可覆盖解读链路；指标计算层新增 `*_norm` 会波及指标 schema、计算器、报告装配、前端图表，收益与成本不成比例。
- 参考先例：`review_findings` 适配器已做"Derive hip/head normalized range ratios"，证明投影/适配层派生归一化是既有模式。
- `*_norm` 作为正式计算指标、展示到报告 UI，列入后续 Change（见 Non-Goals）。

**降级策略**：参考体长缺失、样本不足或 `reference_body_length_px` 为 null 时，不派生 `*_norm` 事实，并在该 px 事实的 `limitations` 追加"无法归一化，仅可定性描述"。策略层据此禁止输出具体像素数值。

## 决策 D2：保留现有 InterpretationOutput，不采用知识库自带输出结构

**决策**：输出 schema 保持 `InterpretationOutput`（`plain_language_summary` / `module_explanations` / `training_suggestions` / `retest_targets` / `limitations`）不变。知识库自带的 `llm_report_generation_prompt.md` 输出结构仅作为策略措辞与示例的参考，不落地为新的输出 schema。

**理由**：
- 用户原则：知识库是参考，服务于系统本身已设计的内容。
- 现有输出 schema 已有配套的 validator、签名、Web/PDF 复用、前端 `AIInterpretationPanel`，替换输出 schema 波及面过大。
- 知识库的四层表达（观测→可能解释→潜在影响→建议）通过 `SYSTEM_POLICY` 的表述顺序要求落地，而非通过改变输出字段。

## 决策 D3：知识卡导入系统 schema，指标别名集中管理

**决策**：将 `swim_knowledge_base_v1.jsonl` 的 28 张卡导入为系统 `KnowledgeEntry`（扩展 schema），落盘为新的对齐知识文件（YAML 或 JSONL，位于 `report_interpretation/knowledge/`）。建立集中式**指标别名映射表**（如 `elbow_angle_deg → [left_elbow_angle_deg, right_elbow_angle_deg]`），导入与检索共用。

**理由**：
- 知识卡字段（`domain`/`view`/`evidence`/`forbidden`/`coach_text`/`actions`/`source_records`）比现有 `KnowledgeEntry` 丰富，需扩展 schema 保留这些约束信息。
- 别名错位（改名指标）是检索静默漏检的主因，集中映射表一处维护、导入与检索两处消费。
- 外部目录 `swim_knowledge_base_v1/` 只读参考，不直接作为运行时依赖，保证部署自包含。
- 现有 `swimming_v1.yaml`（4 条）**保留为回退对照**，不删除。新增配置项（如 `ai_interpretation_knowledge_source: v1|v2`）切换知识源，便于 A/B 对比新旧知识库对解读质量的影响；默认 `v2`。

## 决策 D4：检索升级 = 硬过滤 + 别名解析 + 证据等级门控，不引入向量检索

**决策**：`retrieve()` 保持关键词打分排序，但新增：(a) 泳姿/机位硬过滤（按 `stroke`/`view` 元数据，不匹配即排除）；(b) 指标别名解析（事实 key 与知识卡 metrics 经别名表双向匹配）；(c) 证据等级门控（`evidence=low` 或 `governance` 类卡片仅在需要约束语言时参与，不作为训练建议依据）。无匹配时保持既有"仅基于事实解释"的优雅降级。

**理由**：
- 28 张卡规模小，关键词+别名+硬过滤足以精确命中，向量检索的边际收益低、引入 embedding 依赖与维护成本。
- 语义检索可作为知识库规模扩大后的后续优化（见 Non-Goals）。

## 决策 D5：生理类未来卡片标记 inactive

**决策**：知识卡中当前管线无对应指标者（`swolf`、`stroke_rate`、`stroke_length`、`lactate_*`、`vo2peak`、`body_fat_percent`、`dryland_strength`、`session_rpe` 等）导入时 `review_status` 标为 `inactive`（或在知识文件内以 `applicable_pipelines` 标注），不参与检索，但保留条目便于未来链路接入后激活。

**理由**：
- 避免无关卡片被硬过滤误放行、或指标交集打分误命中而污染解读。
- 保留内容而非删除，便于后续增加生理/性能链路时直接激活。

## 决策 D6：策略再平衡保留护栏、放开"有依据地表述"

**决策**：`SYSTEM_POLICY` 从"几乎禁止表述"改为"强制有依据地表述"：(a) 技术解释必须引用 `fact_ref`，使用知识必须引用 `knowledge_ref`；(b) 表述顺序强制"观测→可能解释→潜在影响→建议"；(c) 继续禁止确定性因果、能力缺陷、伤病诊断与未校准评分；(d) 禁止输出原始像素单位，像素量一律转归一化或定性表述。新增 2–3 个 curated 理想输出示例作为 few-shot 注入 user payload。

**理由**：
- 当前"套话"根因是策略既禁止结论又无知识可讲；放开"有依据地表述"+ 知识库扩展后，模型才有话可说且不越界。
- 护栏（非诊断、引用强制、schema 严格）全部保留，validator 与签名链路不动。

**few-shot 引导（不等人工样本）**：当前无人工 curated 的理想输出样本，故示例由知识卡 `coach_text` 表达模板（含 `{placeholder}` 结构）+ 一份基于真实 fixture 报告构造的示范解读自动组装，注入 user payload 作为表达风格引导。示例在代码/配置中明确标记为"可替换占位"——用户日后提供手工修改的理想解读时，直接替换即可，无需改动链路。

## 实现补充（apply 阶段记录）

- **输入预算提升 24000 → 40000 字符**：v2 知识卡更长，完整五页报告（41 facts + 6 卡）实测 26416 字符超出原默认预算；facts/knowledge 按既有设计不可截断，故提高默认 `ai_interpretation_max_input_chars`。40K 字符约 12K tokens，估算成本 ~$0.0017，仍远低于 `ai_interpretation_max_estimated_cost_usd=0.02`。`few-shot` 风格示例内置于 `SYSTEM_POLICY`（`STYLE_EXAMPLES` 常量），并明确标注"禁止照抄示例数值"以防数字被误引用。
- **字典值 px 指标归一化**：`ankle_vertical_range_px` 等值为 `{left, right}` 字典的指标同样逐叶归一化（`left`/`right` 各除以参考体长），非标量 px 值不再被跳过。
- **证据等级门控带降级**：仅当输入知识中存在 `high/moderate` 卡时，训练建议不得只引用 `governance/low` 卡；若全部知识均为低证据卡（如仅命中低证据卡的极端报告），允许基于事实的建议降级通过，避免合法报告整体失败。

## 真实 qwen 冒烟运行（report 276）暴露并修复的问题

用线上 qwen3.7-plus 对真实报告（51–52 facts、参考体长 1522.6px、9 张视觉证据）跑出 3 轮，逐轮暴露并修复：

1. **ratio → 百分比换算缺口**：模型把 `hip_vertical_range_norm=0.0847` 写成 "8.5%" 被拒——validator 只允许 confidence×100，不允许 ratio 值×100。修复：`_allowed_numbers`/`_fact_display_numbers` 对 `unit=ratio` 事实增加 `value×100` 的显示候选，策略同步说明。
2. **训练建议剂量数字冲突**：策略强制建议含剂量（如 `4×25米`），但 validator 把剂量数字当未 grounded 数字拒绝。修复：`DOSE_PATTERN`（米/组/次/分钟/秒/圈/趟 + `×` 连乘）豁免训练块的剂量数字；事实性数字（指标值/比率/百分比/帧号）仍要求引用。
3. **px 护栏有漏洞 → 收紧为绝对禁止**：原实现"引用了 ratio 事实即放行 px"导致 `36.808 px/frame` 泄漏。修复：px 单位（含 px/frame）出现即拒绝，不再看 norm ref。
4. **px/frame 速度未归一化**：`wrist_velocity_px_per_frame` 单位不是 `px` 被投影层跳过，模型只能裸输出。修复：投影层对 `px/frame` 也派生 `*_norm`（unit=`body_lengths_per_frame`，如 `wrist_velocity_norm`，值 = px/frame ÷ 体长），避免百分比语义混淆（速度不适用 ×100）。

第三轮真实运行 **`valid=True`**：零 px 输出（全部为"占体长比例约18.7%/8.5%/35.4%"及"0.024体长/帧"）、四层结构完整、训练建议含剂量通过、非诊断护栏保持。冒烟脚本保留在 `backend/scripts/smoke_qwen_interpretation.py` 供复跑。

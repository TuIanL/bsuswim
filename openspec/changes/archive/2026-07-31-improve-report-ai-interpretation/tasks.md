# Tasks: improve-report-ai-interpretation

## 1. 像素指标归一化投影

- [x] 1.1 `projector.py` 从报告 context 读取 `reference_body_length_px` 与可用性
- [x] 1.2 为像素距离/波动指标派生 `*_norm` 归一化事实（`InterpretationFact`），保留来源与置信条件
- [x] 1.3 参考体长不可用时降级：不派生 norm，px 事实 limitations 追加"无法归一化，仅可定性描述"
- [x] 1.4 更新 `InterpretationFact` schema 支持派生归一化字段
- [x] 1.5 更新输入 hash / generation signature 兼容新输入结构

## 2. 策略再平衡与 px 输出护栏

- [x] 2.1 重写 `SYSTEM_POLICY`：四层表述顺序、允许有依据的实质解释、禁止原始 px 输出
- [x] 2.2 基于知识卡 `coach_text` 模板 + 真实 fixture 报告构造 2–3 个引导示例（few-shot）注入 user payload，标记为可替换占位
- [x] 2.3 `validator.py` 新增 px 单位输出护栏（`px`/`像素` 未归一化即拒绝）
- [x] 2.4 `validator.py` 校验四层表述结构与建议完整性（目标/练习/复测）
- [x] 2.5 更新 `FakeProvider` 与测试夹具对齐新策略

## 3. 知识库 schema 扩展与导入

- [x] 3.1 `KnowledgeEntry` 扩展：`domain`/`view`/`distance_context`/`evidence_level`/`forbidden`/`coach_text`/`actions`/`audience`/`source_records`/`applicable_pipelines`
- [x] 3.2 建立集中指标别名映射表（`elbow_angle_deg`→左右、`knee_angle_deg`→左右、`head_torso_sync`→`head_body_synchrony`、`wrist_trajectory`→`normalized_wrist_trajectory` 等）
- [x] 3.3 导入 `swim_knowledge_base_v1.jsonl` 28 卡 → 对齐后知识文件（含别名归一与适用性标注）
- [x] 3.4 生理类未来卡片（`swolf`/`lactate`/`vo2peak`/`body_fat_percent` 等）标记 inactive
- [x] 3.5 保留 `swimming_v1.yaml` 为回退对照，新增 `ai_interpretation_knowledge_source` 配置项（v1|v2）切换知识源，默认 v2

## 4. 检索升级

- [x] 4.1 `retrieve()` 按 `stroke`/`view` 硬过滤，不匹配即排除
- [x] 4.2 事实 key 与知识卡指标经别名表双向匹配
- [x] 4.3 证据等级门控：`evidence=low`/`governance` 卡不单独作为训练建议依据
- [x] 4.4 inactive 条目不参与检索；无匹配时保持既有优雅降级
- [x] 4.5 更新 `knowledge_base_version` 计算与审计追溯兼容新知识文件

## 5. 验证与测试

- [x] 5.1 更新 `test_report_interpretation.py` 既有用例适配新输入/策略
- [x] 5.2 新增归一化投影测试（含参考体长可用/缺失两分支）
- [x] 5.3 新增 px 输出护栏测试（拒绝未归一化 px）
- [x] 5.4 新增别名命中与硬过滤测试（改名指标命中、机位不匹配排除、生理卡 inactive）
- [x] 5.5 新增策略平衡测试（有知识背书解释通过、确定性结论拒绝、四层结构校验）
- [x] 5.6 用真实报告 fixture 跑通一次端到端解读（fake provider）

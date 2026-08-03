## Why

当前 AI 报告解读（`llm-assisted-report-interpretation`）产出不理想，用户反馈三类问题：(1) 输出套话化、过度保守，几乎全部是"建议结合原视频复核"；(2) 重点抓不对，该强调的关键指标没强调；(3) 输出原始像素单位（如"偏移 12px"），对用户没有物理意义且跨视频不可比。

根因诊断：
- **px 问题**：波动类指标（`hip_vertical_range_px` 等）直接暴露原始像素，系统已计算 `reference_body_length_px`（`AnnotationContext`）并有归一化先例（`normalized_wrist_trajectory`），但解读投影层未使用。
- **套话问题**：`SYSTEM_POLICY` 约束过严，几乎禁止一切实质性技术表述；同时知识库仅 4 条且全是"复核注意事项"，模型想说也无话可说。
- **知识库薄**：外部已整理一份 28 张知识卡的知识库（`swim_knowledge_base_v1`，来源含 World Aquatics、同行评审论文与官方教练指南），质量可靠且直接命中 px 问题，但指标名与系统实际指标存在改名、假设不存在的归一化指标、以及生理类未来指标三类错位，直接接入无法检索命中。

本 Change 在**保留系统既有指标体系与输出 schema 的前提下**（知识库作为参考而非主干），把 px 归一化、策略再平衡、知识库对齐接入一次性落地，直接修复"px 荒谬 + 套话 + 重点抓不对"。

## What Changes

- **归一化指标投影**：解读投影层读取 `reference_body_length_px`，为像素距离/波动指标派生归一化比率事实（`*_norm`），供模型使用；参考体长不可用时降级为"仅可定性描述"
- **策略再平衡**：重写 `SYSTEM_POLICY`，采用"观测→可能解释→潜在影响→建议"四层表述，允许在事实与知识支撑下给出实质技术解释，同时保留并强化非诊断护栏；输出示例使用知识卡 `coach_text` 表达模板引导（few-shot 占位，后续可用人工修改的理想输出替换）
- **px 输出护栏**：本地 validator 拒绝输出原始像素单位；要求技术含义块同时具备 `fact_ref` 与（使用知识时）`knowledge_ref`
- **知识库对齐接入**：导入 `swim_knowledge_base_v1` 28 张知识卡，转成系统 `KnowledgeEntry` schema（扩展元数据字段）；建立指标别名映射表（`elbow_angle_deg`→`left/right_elbow_angle_deg` 等）；按泳姿/机位硬过滤
- **适用性标注**：当前管线无对应指标的生理类卡片（`swolf`/`lactate`/`vo2peak` 等）标记为 `inactive`，不参与检索
- **检索升级**：`KnowledgeRegistry.retrieve()` 支持泳姿/机位硬过滤、指标别名解析与证据等级门控；无匹配时保持既有优雅降级
- 输出 schema（`InterpretationOutput`）保持不变，Web 与 PDF 复用链路不变

## Capabilities

### Modified Capabilities

- `llm-assisted-report-interpretation`：新增"像素指标归一化"、"知识检索按泳姿/机位过滤与指标别名解析"、"策略平衡下有依据地表述但保持非诊断"三类需求，其余既有 11 条需求行为不变。

## Impact

- `backend/app/services/report_interpretation/projector.py`（归一化派生事实）
- `backend/app/services/report_interpretation/prompt.py`（策略重写 + few-shot）
- `backend/app/services/report_interpretation/knowledge.py`（检索升级 + 别名解析）
- `backend/app/services/report_interpretation/knowledge/`（新增对齐后知识卡文件；`swimming_v1.yaml` 保留为回退对照，新增配置项切换知识源）
- `backend/app/schemas/report_interpretation.py`（`KnowledgeEntry` 扩展、`InterpretationFact` 归一化字段）
- `backend/app/services/report_interpretation/validator.py`（px 输出护栏）
- `backend/tests/test_report_interpretation.py`（新增/更新测试）
- 知识库来源：`/Users/tuian/Documents/大学/竞赛/大创/游泳/swim_knowledge_base_v1`（只读参考，不修改）

## Non-Goals

- 不改变系统既有指标体系与计算层（不新增 `*_norm` 计算指标，本轮在投影层派生）
- 不改变 `InterpretationOutput` 输出 schema，不采用知识库自带 `llm_report_generation_prompt.md` 的输出结构
- 不实现 agent/tool-use 或交互式问答助手（后续独立 Change）
- 不实现语义向量检索（本轮保持关键词+别名+硬过滤）
- 不做教练版/学员版双输出
- 不修改前端
- 不实现知识卡线上维护/管理界面

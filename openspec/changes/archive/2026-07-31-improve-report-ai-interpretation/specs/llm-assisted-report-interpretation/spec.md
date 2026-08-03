## ADDED Requirements

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

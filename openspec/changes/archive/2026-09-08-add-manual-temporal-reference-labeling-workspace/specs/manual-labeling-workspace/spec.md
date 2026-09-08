## ADDED Requirements

### Requirement: 人工标注工作台页面

`frontend-vue` SHALL 提供人工时序参考标注工作台页面，绑定 `session_video_id`，支持在同一时间线上标注媒体片段区间。

#### Scenario: 打开标注工作台

- **WHEN** 用户打开 `/sessions/{sessionId}/videos/{sessionVideoId}/labels`
- **THEN** 系统 MUST 加载该视频的播放源、annotation set 列表与当前 draft revision 的区间

#### Scenario: 视频存在多个绑定机位

- **WHEN** 训练记录下有多个 session video
- **THEN** 工作台 MUST 展示当前标注视频的机位与文件名，并保持标注上下文与所选视频一致

#### Scenario: 视频无法加载

- **WHEN** 视频文件缺失或 URL 不可访问
- **THEN** 工作台 MUST 显示稳定错误状态并保留返回入口，MUST NOT 把不可用状态渲染为正常标注界面

### Requirement: 左右臂分轨 timeline

工作台 SHALL 按 `side` 将区间分为左臂与右臂两条轨道渲染，同轨内按 `cycle_id` 分组。

#### Scenario: 左右臂区间分别渲染

- **WHEN** revision 中存在 `side = left` 与 `side = right` 的区间
- **THEN** 工作台 MUST 在两条独立轨道上渲染，MUST NOT 混合到同一轨

#### Scenario: 同侧周期分组展示

- **WHEN** 右臂存在多个 cycle
- **THEN** 工作台 MUST 按 `cycle_id` 分组排列，并展示每组的 `cycle_index`

#### Scenario: 左右臂区间重叠正常显示

- **WHEN** 左臂与右臂区间在时间轴上重叠
- **THEN** 工作台 MUST 正常并列显示，MUST NOT 提示为错误

#### Scenario: timeline 与播放位置同步

- **WHEN** 视频播放到某一时间点
- **THEN** timeline MUST 高亮当前时间所在区间，MUST NOT 伪造不存在的区间高亮

### Requirement: 区间创建与起止秒设定

用户 SHALL 能够自由设定区间的起始秒与结束秒，并为其指定技术环节标签。

#### Scenario: 通过数值输入创建区间

- **WHEN** 用户输入起始秒、结束秒并选择环节后保存
- **THEN** 系统 MUST 创建 segment，`start_time_sec` / `end_time_sec` 与用户输入一致

#### Scenario: 使用当前播放位置快速设定

- **WHEN** 用户点击"设为起点"或"设为终点"
- **THEN** 系统 MUST 使用视频当前 `currentTime` 填充对应字段

#### Scenario: 拖拽区间端点调整

- **WHEN** 用户拖拽已有区间的端点
- **THEN** 系统 MUST 更新对应起止秒，MUST NOT 改变该区间的 `cycle_id` 与 `side`

#### Scenario: 环节标签使用展示名

- **WHEN** 用户选择环节标签
- **THEN** 界面 MUST 显示中文展示名（入水 / 抱水 / 推水 / 移臂），提交 MUST 使用稳定 code

#### Scenario: 可查看环节边界的人工判据

- **WHEN** 用户查看某环节标签的帮助入口
- **THEN** 界面 MUST 展示该环节对应边界的 `annotation_guidance` 与 `operational_definition`，使不同标注员依据同一判据标注

#### Scenario: side 未判明时可临时标记

- **WHEN** 标注员暂无法判明左右臂
- **THEN** 界面 MUST 允许在 draft 中选择 `both` / `unknown`，并 MUST 提示提交复核前需收敛为 `left` / `right`

#### Scenario: 起止时间非法时阻止保存

- **WHEN** 起始秒大于或等于结束秒
- **THEN** 工作台 MUST 阻止保存并给出明确提示

### Requirement: 区间编辑与删除

用户 SHALL 能够编辑与删除 draft revision 中的区间。

#### Scenario: 编辑 draft 区间

- **WHEN** 用户修改 draft revision 中某区间的起止秒或备注
- **THEN** 系统 MUST 保存更新并刷新 timeline

#### Scenario: 编辑已发布 revision 被阻止

- **WHEN** 当前 revision 状态为 `in_review` / `reviewed` / `frozen`
- **THEN** 工作台 MUST 禁用编辑与删除操作，并 MUST 提供从该 revision fork 的入口

#### Scenario: 并发编辑冲突被提示

- **WHEN** 另一个标签页已修改同一 draft revision，当前标签页写请求返回 409
- **THEN** 工作台 MUST 提示用户刷新后重试，MUST NOT 自动重试覆盖

#### Scenario: 删除区间

- **WHEN** 用户删除某区间
- **THEN** 系统 MUST 执行 soft delete，该区间 MUST 从 timeline 消失，但 MUST 保留审计记录

#### Scenario: 备注可编辑

- **WHEN** 用户为区间填写备注
- **THEN** 系统 MUST 保存至该 segment 的 `note`

### Requirement: 生命周期状态展示与操作

工作台 SHALL 展示当前 revision 的生命周期状态，并提供与状态匹配的操作入口。

#### Scenario: draft 状态可提交复核

- **WHEN** 当前 revision 为 `draft`
- **THEN** 工作台 MUST 提供"提交复核"入口，并 MUST 在提交前执行 L1 与 L2 校验

#### Scenario: 校验失败展示具体冲突

- **WHEN** L2 校验发现同侧同周期重叠
- **THEN** 工作台 MUST 展示冲突区间与阶段，MUST NOT 仅提示"校验失败"

#### Scenario: 已发布 revision 提供 fork 入口

- **WHEN** 当前 revision 为 `reviewed` 或 `frozen`
- **THEN** 工作台 MUST 提供"从此版本继续编辑"入口，执行后 MUST 跳转到新的 draft revision

#### Scenario: fork 保留 lineage 提示

- **WHEN** 用户从某 revision fork
- **THEN** 工作台 MUST 显示新 revision 的来源版本，使用户能识别标注谱系

### Requirement: 不展示未实现能力

工作台 MUST NOT 把尚未实现的数据集导出、自动阶段识别、多人 adjudication 等能力渲染为可用功能。

#### Scenario: 未实现的导出入口不出现

- **WHEN** 用户查看标注工作台
- **THEN** 界面 MUST NOT 提供数据集导出、train/val/test 拆分等未实现入口

#### Scenario: 派生区间明确标注为派生

- **WHEN** timeline 上展示由 imported events 派生的区间
- **THEN** 工作台 MUST 明确标记其为派生结果，MUST NOT 与人工标注混淆

#### Scenario: partial derivation 明示不可用

- **WHEN** 派生因缺少 `hand_exit` 而无法生成 `push` / `recovery`
- **THEN** 工作台 MUST 显示该阶段不可用及原因，MUST NOT 显示猜测出来的区间

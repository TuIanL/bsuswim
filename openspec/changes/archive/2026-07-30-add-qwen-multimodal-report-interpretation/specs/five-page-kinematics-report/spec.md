## ADDED Requirements

### Requirement: Five-page report exposes stable references for AI evidence selection

五页报告 SHALL 为可用于 AI 多模态证据包的已生成关键姿态资产和时序资产保留稳定资产身份、来源 revision、模块、媒体类型和关联指标/发现信息，且不改变现有五页顺序、内容边界或打印页数。

#### Scenario: Report contains current visual artifacts
- **WHEN** 五页报告装配包含当前关键姿态或时序资产
- **THEN** 每个可选资产 SHALL 保留供服务端解析的稳定引用与来源追溯信息
- **AND** 报告页面 SHALL 继续按既有结构渲染该资产

#### Scenario: Report has no suitable visual asset
- **WHEN** 页面没有当前、可读取的关键姿态或时序资产
- **THEN** 报告 SHALL 保持可用并呈现既有质量说明
- **AND** AI 解读 SHALL 能降级为不含视觉证据的文本模式

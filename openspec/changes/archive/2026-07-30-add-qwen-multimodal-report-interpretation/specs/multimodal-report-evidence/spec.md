## ADDED Requirements

### Requirement: System builds a bounded multimodal evidence bundle from current report assets

系统 SHALL 仅从当前基础报告及其当前 revision 的已生成派生资产构建版本化多模态证据包；证据包 SHALL 包含关联事实、资产身份和选择理由，并 SHALL 设置每模块与每请求的数量、像素、字节和曲线点数上限。

#### Scenario: Eligible keyframes and time-series assets exist
- **WHEN** 当前报告包含可读取且属于技术模块的关键姿态图或时序图
- **THEN** 系统 SHALL 为每个模块选择不超过配置上限的证据项
- **AND** 每个项 SHALL 包含稳定 evidence ID、asset ID、内容 hash、模块、媒体类型、关联 fact refs、关联 finding、帧或曲线范围和选择理由

#### Scenario: Asset is stale, unreadable, or outside the current report scope
- **WHEN** 候选资产的 revision、generation signature、访问授权或读取状态无效
- **THEN** 系统 SHALL NOT 将该资产发送给 provider
- **AND** SHALL 将结构化排除原因写入生成审计

### Requirement: Curve evidence remains machine-verifiable

系统 SHALL 为发送给 provider 的每张时序图提供限长数值摘要，且 SHALL 保留单位、横轴语义、降采样规则和缺失数据说明。

#### Scenario: A time-series chart is selected
- **WHEN** 证据包选择一张时序图
- **THEN** 系统 SHALL 同时投影受上限控制的曲线数值摘要及其关联 metric fact refs
- **AND** SHALL NOT 将完整逐帧关键点坐标作为曲线摘要发送

### Requirement: Multimodal evidence preserves data minimization

系统 SHALL NOT 在证据包或 provider 请求中包含原始视频、视频片段、完整逐帧关键点、未筛选标注文件、姓名、联系方式、访问 token、绝对存储路径或无关内部 ID。

#### Scenario: Provider payload is assembled
- **WHEN** 系统准备发送多模态请求
- **THEN** payload SHALL 仅含受控事实、已审核知识、允许的上下文、evidence manifest、受限曲线摘要和选定派生图像
- **AND** 应用日志与持久化审计 SHALL NOT 保存图像二进制或完整 provider 请求正文

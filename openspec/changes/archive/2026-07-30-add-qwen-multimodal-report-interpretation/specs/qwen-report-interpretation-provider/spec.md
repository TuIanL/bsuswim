## ADDED Requirements

### Requirement: AI interpretation supports a Qwen-compatible provider configuration

系统 SHALL 支持通过服务端环境配置选择 Qwen 兼容 API 的 endpoint、模型、凭据、超时、重试和模型能力；凭据 SHALL NOT 出现在客户端响应、日志、报告、OpenSpec 产物或版本控制文件中。

#### Scenario: Qwen provider is correctly configured
- **WHEN** 服务端已配置有效 Qwen endpoint、模型和凭据
- **THEN** 系统 SHALL 使用 Qwen-compatible adapter 发起解读请求
- **AND** SHALL 在解读 trace 中保存 provider、模型和非敏感能力配置

### Requirement: Provider capability determines the request mode

系统 SHALL 在发送含图像的请求前验证所选模型同时支持图像输入和结构化 JSON 输出；不满足任一能力时 SHALL 使用文本模式或失败，且不得声称视觉证据已被模型使用。

#### Scenario: Selected model supports visual structured generation
- **WHEN** Qwen 模型通过视觉输入和结构化输出能力验证
- **THEN** adapter SHALL 将受控 JSON 输入与选定图像以该 API 支持的多段消息格式发送
- **AND** 生成 trace SHALL 记录 `visual_mode=true` 和已使用 evidence IDs

#### Scenario: qwen-plus or another selected model lacks visual capability
- **WHEN** 所选模型不支持图像输入或结构化 JSON 输出
- **THEN** 系统 SHALL 不发送图像二进制或图像 URL
- **AND** SHALL 使用相同事实 catalog 的文本模式，或以结构化能力错误结束生成
- **AND** trace SHALL 记录实际能力与降级原因

### Requirement: Provider failures retain deterministic report availability

Qwen provider 的认证、配额、超时、能力验证或响应解析失败 SHALL 不阻塞基础报告生成、读取或 PDF 导出。

#### Scenario: Qwen request fails
- **WHEN** Qwen provider 返回错误、超时或无效结构
- **THEN** AI 解读 SHALL 进入带错误码的 failed 状态
- **AND** 基础五页报告和最近一次已验证 ready 解读 SHALL 保持可用

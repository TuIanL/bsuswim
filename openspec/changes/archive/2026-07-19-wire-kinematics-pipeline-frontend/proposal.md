## Why

后端已实现完整的运动学子系统（指标计算、可视化生成、诊断发现、5页报告组装），约40个文件的代码已完成，但前端完全不知道这些功能的存在。用户无法看到运动学分析的核心价值：指标图表、关键帧可视化、诊断发现和结构化报告。

## What Changes

- 新增前端 API 调用层，连接后端 metrics、artifacts、review-findings、kinematics-reports 端点
- 新增运动学指标展示组件，显示计算后的运动学数据
- 新增可视化 artifacts 展成组件，显示关键帧图片和图表
- 新增诊断发现展示组件，显示规则引擎生成的建议
- 改进报告页面，支持5页结构化报告的渲染
- 清理前端死代码（UploadView.vue、createAnalysisTask 函数）
- 修复 getAthleteTrend 空实现

## Capabilities

### New Capabilities
- `kinematics-metrics-display`: 前端展示运动学指标数据（身体姿态、上肢、下肢指标）
- `kinematics-artifacts-display`: 前端展示可视化 artifacts（关键帧图片、图表、雷达图）
- `kinematics-review-findings-display`: 前端展示诊断发现和建议
- `frontend-dead-code-cleanup`: 清理前端未使用的代码和死函数

### Modified Capabilities
- `five-page-kinematics-report`: 扩展报告页面，支持渲染5页结构化报告的完整内容
- `guided-side-2d-kinematics-workflow`: 工作流页面添加指标和可视化展示步骤

## Impact

- 后端 API: 新增前端调用的端点（metrics、artifacts、review-findings、kinematics-reports）
- 前端组件: 新增3-4个展示组件，修改2个现有页面
- 前端服务: api.ts 新增多个 API 函数
- 数据流: 分析完成后自动获取并展示运动学结果

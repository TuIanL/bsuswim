## Context

当前状态：
- 后端已完成运动学子系统：metrics计算（16个文件）、kinematic_artifacts可视化生成（10个文件）、diagnostics诊断引擎、kinematics_report 5页报告组装（8个文件）
- 前端仅有基础工作流：上传视频 → 上传标注 → 提交分析 → 查看报告
- 前端完全不知道后端的运动学功能存在，无法调用相关API
- 后端已有对应的API路由（metrics.py、kinematic_artifacts.py、kinematic_review_findings.py、kinematics_reports.py），但前端零调用

约束：
- 前端使用 Vue 3 + TypeScript + Element Plus
- 后端使用 FastAPI + SQLAlchemy
- 必须保持与现有工作流的兼容性

## Goals / Non-Goals

**Goals:**
- 让用户能看到运动学分析的核心价值（指标、可视化、诊断建议）
- 在现有工作流中无缝集成运动学展示，不破坏现有流程
- 支持5页结构化报告的完整渲染
- 清理前端死代码，提高代码质量

**Non-Goals:**
- 不修改后端API结构（后端已实现完毕）
- 不重新设计报告格式（使用现有的 swim-report.v1）
- 不添加新的分析pipeline（仅连接现有功能）
- 不修改PDF导出流程（仅确保新内容可打印）

## Decisions

### Decision 1: 渐进式集成策略

**选择**: 在现有工作流页面（SessionUploadView）中添加运动学展示步骤，而非创建独立页面

**理由**: 
- 用户已经熟悉现有工作流
- 运动学结果是分析流程的自然延伸
- 减少页面跳转，提升用户体验

**替代方案**: 创建独立的运动学展示页面 → 否决，增加用户认知负担

### Decision 2: API调用层设计

**选择**: 在 api.ts 中新增运动学相关API函数，遵循现有的函数命名模式

**理由**:
- 保持代码风格一致性
- 便于维护和测试
- 支持 demo 模式回退

**实现**:
```typescript
// 新增 API 函数
export async function getAnnotationMetrics(normalizedAnnotationId: number): Promise<AnnotationMetricRead>
export async function calculateMetrics(normalizedAnnotationId: number, persist?: boolean): Promise<CalculateMetricsResponse>
export async function getKinematicArtifacts(annotationMetricId: number): Promise<KinematicArtifactSetRead>
export async function generateKinematicArtifacts(annotationMetricId: number, force?: boolean): Promise<GenerateResponse>
export async function getReviewFindings(annotationMetricId: number, ruleSet?: string): Promise<ReviewFindingsReadResponse>
export async function generateReviewFindings(annotationMetricId: number, ruleSet?: string, force?: boolean): Promise<ReviewFindingsGenerateResponse>
export async function assembleFivePageReport(annotationMetricId: number): Promise<FivePageKinematicsReport>
```

### Decision 3: 组件架构

**选择**: 创建独立的展示组件，而非修改现有组件

**理由**:
- 关注点分离：现有组件专注于工作流，新组件专注于展示
- 便于独立测试和维护
- 支持复用（可在报告页面和工作流页面使用）

**组件结构**:
```
components/
  kinematics-workflow/
    KinematicsMetricsPanel.vue      # 指标展示
    KinematicsArtifactsPanel.vue    # 可视化展示
    KinematicsReviewPanel.vue       # 诊断发现展示
  report/
    sections/
      KinematicsMetricsSection.vue  # 报告中的指标章节
      KinematicsArtifactsSection.vue # 报告中的可视化章节
```

### Decision 4: 数据流设计

**选择**: 分析完成后自动触发运动学计算，结果通过轮询获取

**理由**:
- 与现有分析流程一致（已使用轮询）
- 后端已支持异步计算
- 用户无需手动触发

**流程**:
1. 分析任务完成
2. 前端检测到任务状态变为 `completed`
3. 前端调用 `calculateMetrics` 获取指标
4. 前端调用 `generateKinematicArtifacts` 获取可视化
5. 前端调用 `generateReviewFindings` 获取诊断建议
6. 结果展示在工作流页面

### Decision 5: 清理策略

**选择**: 删除死代码，修复空实现

**具体操作**:
- 删除 `UploadView.vue`（未使用）
- 删除 `api.ts` 中的 `createAnalysisTask` 函数（死代码）
- 实现 `getAthleteTrend` API 调用（或移除趋势图功能）

## Risks / Trade-offs

### Risk 1: 后端API性能
**风险**: 运动学计算可能较慢，影响用户体验
**缓解**: 
- 使用异步计算 + 轮询模式
- 显示加载状态和进度
- 设置合理的超时时间

### Risk 2: 数据一致性
**风险**: 多个API调用可能返回不一致的状态
**缓解**:
- 使用统一的 `annotation_metric_id` 作为关联键
- 在组件级别处理加载状态
- 提供手动刷新功能

### Risk 3: 报告渲染兼容性
**风险**: 5页报告内容可能与现有报告渲染器不兼容
**缓解**:
- 使用现有的 `ReportSectionRenderer` 组件
- 扩展 `reportAdapter.ts` 支持新字段
- 添加单元测试验证渲染结果

### Trade-off: 功能完整 vs 快速交付
**权衡**: 完整实现所有运动学功能需要较多工作
**选择**: 优先实现核心功能（指标 + 可视化），诊断发现和5页报告作为后续迭代

## 1. 清理前端死代码

- [x] 1.1 删除 `frontend-vue/src/views/UploadView.vue` 文件
- [x] 1.2 删除 `frontend-vue/src/services/api.ts` 中的 `createAnalysisTask` 函数
- [x] 1.3 检查并修复 `getAthleteTrend` 函数（实现真实 API 调用或移除趋势图）
- [x] 1.4 运行前端测试确保清理后功能正常

## 2. 扩展前端 API 层

- [x] 2.1 在 `frontend-vue/src/types.ts` 中添加运动学相关类型定义（AnnotationMetricRead, KinematicArtifactSetRead, ReviewFindingsReadResponse 等）
- [x] 2.2 在 `frontend-vue/src/services/api.ts` 中添加 `getAnnotationMetrics` 函数
- [x] 2.3 在 `frontend-vue/src/services/api.ts` 中添加 `calculateMetrics` 函数
- [x] 2.4 在 `frontend-vue/src/services/api.ts` 中添加 `getKinematicArtifacts` 函数
- [x] 2.5 在 `frontend-vue/src/services/api.ts` 中添加 `generateKinematicArtifacts` 函数
- [x] 2.6 在 `frontend-vue/src/services/api.ts` 中添加 `getReviewFindings` 函数
- [x] 2.7 在 `frontend-vue/src/services/api.ts` 中添加 `generateReviewFindings` 函数
- [x] 2.8 在 `frontend-vue/src/services/api.ts` 中添加 `assembleFivePageReport` 函数

## 3. 创建运动学指标展示组件

- [x] 3.1 创建 `frontend-vue/src/components/kinematics-workflow/KinematicsMetricsPanel.vue` 组件
- [x] 3.2 实现指标数据获取逻辑（调用 calculateMetrics API）
- [x] 3.3 实现指标按维度分组展示（身体姿态、上肢、下肢）
- [x] 3.4 实现指标持久化功能（保存按钮）
- [x] 3.5 实现加载状态和错误处理

## 4. 创建运动学可视化展示组件

- [x] 4.1 创建 `frontend-vue/src/components/kinematics-workflow/KinematicsArtifactsPanel.vue` 组件
- [x] 4.2 实现 artifacts 数据获取逻辑（调用 generateKinematicArtifacts API）
- [x] 4.3 实现关键帧图片展示
- [x] 4.4 实现图表展示（使用 ECharts）
- [x] 4.5 实现雷达图展示
- [x] 4.6 实现加载状态和错误处理

## 5. 创建运动学诊断发现展示组件

- [x] 5.1 创建 `frontend-vue/src/components/kinematics-workflow/KinematicsReviewPanel.vue` 组件
- [x] 5.2 实现诊断发现数据获取逻辑（调用 generateReviewFindings API）
- [x] 5.3 实现发现按严重程度分组展示
- [x] 5.4 实现规则集选择功能
- [x] 5.5 实现加载状态和错误处理

## 6. 集成运动学展示到工作流页面

- [x] 6.1 修改 `frontend-vue/src/components/kinematics-workflow/KinematicsWorkflowPage.vue` 组件
- [x] 6.2 在分析进度面板下方添加运动学指标展示区域
- [x] 6.3 在指标区域下方添加可视化 artifacts 展示区域
- [x] 6.4 在可视化区域下方添加诊断发现展示区域
- [x] 6.5 实现结果区域的折叠/展开功能
- [x] 6.6 实现结果数据的手动刷新功能

## 7. 扩展报告页面支持5页报告

- [x] 7.1 修改 `frontend-vue/src/utils/reportAdapter.ts` 支持5页报告数据结构
- [x] 7.2 修改 `frontend-vue/src/types/report.ts` 添加5页报告相关类型
- [x] 7.3 创建 `frontend-vue/src/components/report/sections/KinematicsMetricsSection.vue` 组件
- [x] 7.4 创建 `frontend-vue/src/components/report/sections/KinematicsArtifactsSection.vue` 组件
- [x] 7.5 修改 `frontend-vue/src/components/report/ReportSectionRenderer.vue` 支持新章节类型
- [x] 7.6 修改 `frontend-vue/src/views/ReportView.vue` 支持5页报告渲染

## 8. 打印和PDF导出优化

- [x] 8.1 修改 `frontend-vue/src/views/PrintReportView.vue` 支持5页报告打印
- [x] 8.2 优化打印样式确保每页独立成页
- [x] 8.3 添加页面溢出检测和错误处理
- [x] 8.4 测试打印和PDF导出功能

## 9. 测试和验证

- [x] 9.1 运行前端单元测试确保所有组件正常
- [x] 9.2 运行前端构建确保无编译错误
- [x] 9.3 手动测试完整工作流（上传视频 → 上传标注 → 提交分析 → 查看结果）
- [x] 9.4 手动测试报告页面5页渲染
- [x] 9.5 手动测试打印和PDF导出功能
- [x] 9.6 验证与现有功能的兼容性

## ADDED Requirements

### Requirement: 系统 SHALL 清理前端未使用的代码

系统 SHALL 删除前端未使用的文件和函数，提高代码质量和可维护性。

#### Scenario: 删除未使用的 UploadView.vue

- **WHEN** 代码审查发现 `UploadView.vue` 文件未在路由中注册
- **AND** 该文件已被 `SessionUploadView.vue` 完全取代
- **THEN** 系统 SHALL 删除 `frontend-vue/src/views/UploadView.vue` 文件
- **AND** SHALL 确保没有其他组件引用该文件

#### Scenario: 删除死函数 createAnalysisTask

- **WHEN** 代码审查发现 `api.ts` 中的 `createAnalysisTask` 函数在真实后端模式下抛出异常
- **AND** 该函数仅在 demo 模式下可用
- **THEN** 系统 SHALL 删除 `api.ts` 中的 `createAnalysisTask` 函数
- **AND** SHALL 确保没有组件调用该函数

#### Scenario: 修复空实现 getAthleteTrend

- **WHEN** 代码审查发现 `api.ts` 中的 `getAthleteTrend` 函数在非 demo 模式下返回空数组
- **AND** 该函数被 `AthleteProfileView.vue` 调用
- **THEN** 系统 SHALL 实现真实的 API 调用（如果后端支持）
- **OR** SHALL 移除趋势图功能并更新 `AthleteProfileView.vue`

### Requirement: 系统 SHALL 确保代码清理后的功能完整性

系统 SHALL 在清理代码后确保现有功能不受影响。

#### Scenario: 清理后运行测试

- **WHEN** 代码清理完成
- **THEN** 系统 SHALL 运行前端单元测试
- **AND** SHALL 运行前端构建
- **AND** SHALL 确保所有测试通过，构建成功

#### Scenario: 清理后功能验证

- **WHEN** 代码清理完成
- **THEN** 系统 SHALL 验证登录功能正常
- **AND** SHALL 验证运动员管理功能正常
- **AND** SHALL 验证训练记录创建功能正常
- **AND** SHALL 验证视频上传功能正常
- **AND** SHALL 验证分析提交功能正常
- **AND** SHALL 验证报告查看功能正常

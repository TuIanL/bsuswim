## Why

当前上传页（`KinematicsWorkflowPage`）底部渲染了"后续扩展机位"面板（正面 / 俯视 / 水下 / 半水下 四张卡片），创建任务页的步骤说明也写"侧面、正面、俯视、水下与半水下视频"，暗示存在多机位选择。但系统端到端只使用侧面机位：分析引擎 `metrics_service.py` 硬性只接受 `side`，`analysis_service.py` 只捞 `view_type == SIDE`，上传也仅绑定 `side`。这些"占位"机位既不可上传、也不参与分析，反而让用户误以为需要在机位间做选择，造成困惑。经验证，当前阶段唯一真实需要的机位就是侧面，因此应移除其余机位的上传/选择展示，把上传页收敛为单一侧面上传。

## What Changes

- 从上传页（`KinematicsWorkflowPage`）移除 `<FutureCameraViewsPanel>` 组件用法及其 import，不再渲染"后续扩展机位"区域。
- 删除组件文件 `FutureCameraViewsPanel.vue`（其余机位上传已不需要，占位组件无保留意义）。
- 修改 `CreateSessionView.vue` 的步骤说明文案：去掉正面 / 俯视 / 水下 / 半水下的多机位表述，改为"上传侧面视频（本次仅分析侧面机位）"，并相应修正"多机位视频上传"等措辞。
- 顺带消除一处数据模型不一致：前端出现的 `semi_underwater`（半水下）在后端 `view_type` 枚举（SIDE / FRONT / TOP / UNDERWATER / OTHER）中并不存在，随该面板删除自然消失。
- 后端 `view_type` 枚举本次**不收窄**：用户明确"先"删除前端 UI，保留枚举以便将来恢复多机位，可逆、零迁移风险。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `guided-side-2d-kinematics-workflow`：修改"主流程固定侧面机位与 CVAT"需求——移除"正面 / 俯视 / 水下 / 半水下 作为只读后续扩展机位区域"的既有要求，改为上传步骤 SHALL 仅呈现侧面机位，不得向用户展示任何其他机位的可选入口或"后续扩展"占位区域。

## Impact

- 前端代码：
  - `frontend-vue/src/components/kinematics-workflow/KinematicsWorkflowPage.vue`（移除面板用法与 import）
  - `frontend-vue/src/components/kinematics-workflow/FutureCameraViewsPanel.vue`（整文件删除）
  - `frontend-vue/src/views/CreateSessionView.vue`（修正步骤说明文案）
- 用户行为：上传页不再出现任何非侧面机位 UI，用户无需在机位间选择。
- 数据 / 后端：无 schema 变更；分析引擎与 `view_type == SIDE` 过滤逻辑保持不变。
- 依赖：无新增依赖。

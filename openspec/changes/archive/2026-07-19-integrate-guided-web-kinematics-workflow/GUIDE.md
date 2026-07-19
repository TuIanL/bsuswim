# 集成式网页二维运动学引导工作流 — 使用与验证文档

> 对应 Change：`integrate-guided-web-kinematics-workflow`
> 适用范围：游泳技术分析平台前端 `/sessions/:id/upload` 六步侧视角 2D 运动学引导工作流，以及后端读取契约扩展。

---

## 17.1 六步用户工作流

上传/分析页被重构为以「侧视角视频」为中心的线性引导流程（Stepper 仅用于展示进度，不构成独立路由）：

1. **侧面视频（Side Video）**：必须先绑定一条 `view_type=side` 的 session video。未绑定前，后续所有步骤均被阻断。允许在显式确认下替换当前侧面视频。
2. **CVAT 标注（Annotation）**：主标注入口固定为 CVAT 骨架标注（`.xml`）。展示上传中 / 解析中 / 质量检查中等不确定进度态；成功后展示 parse summary；对 `parse_failed` 文件提供「重新解析」，对 `invalid` 标注提供替换上传。
3. **质量与模块就绪（Quality & Module Readiness）**：整体质量状态、质量分数、blocking/warning/info 计数；按严重级别分组展示问题（优先 `user_message`）。四张模块卡片：`body_posture` / `upper_limb` / `lower_limb` / `head_trunk`，状态统一为 `ready | degraded | blocked`。
4. **提交分析（Submit）**：CTA 为「生成二维运动学报告」。前置条件：已绑定 side 视频 + 已选 normalized annotation + `analysis_readiness.can_submit=true` + 无活跃 annotation pipeline 任务。提交显式携带 `annotation_kinematics` / `side_2d_v1`。
5. **分析进度（Progress）**：渲染后端返回的 `pipeline_progress.steps` 真实有序阶段序列；每步标记 `pending|running|completed|failed`；展示进度百分比与 `attempt_count`，以及 pipeline warnings。
6. **报告就绪（Report）**：检测已完成且报告实体真实存在的 annotation pipeline 任务，提供「查看 HTML 报告」与 PDF 导出/下载。报告缺失时复用 `analysis_failed` + 合成错误 `REPORT_METADATA_MISSING`，提供「使用当前标注重新生成」。

> 工作流阶段（`WorkflowPhase`）由 `deriveWorkflowPhase` 纯函数从前端与后端数据推导，**顺序归后端**，前端不维护独立的规范阶段顺序。

---

## 17.2 三类「就绪 / 可用」的区别（易混点）

| 概念 | 含义 | 数据来源 | 用户动作 |
| --- | --- | --- | --- |
| **annotation readiness** | 当前标注「能否提交分析」的前置判断（`can_submit` / `requires_acknowledgement`） | `AnnotationFileListItem.analysis_readiness` | 决定提交按钮是否可用；warning 需显式确认 |
| **metric availability** | 分析产物（指标/图表）是否可用，是「执行结果」维度 | 任务 `pipeline_progress` 各阶段完成态 | 进度面板展示；失败阶段可重试/重提 |
| **report availability** | 最终 HTML/PDF 报告是否真实存在且新鲜 | `ReportMetadata`（由 `reportFreshness` 基于 `ReportMetadata.task_id` 所指任务的 annotation revision 推导） | 报告页动作；缺失时重新生成 |

关键点：**三者相互独立**。标注就绪 ≠ 报告就绪；报告缺失（任务 completed 但无 `ReportMetadata`）不应被误判为「报告可用」，前端据此切换到失败恢复 UI。

---

## 17.3 retry 与 resubmit 语义

错误恢复动作由后端集中注册表 `ERROR_RECOVERY_POLICY` 决定（`analysis_pipelines/errors.py`），前端仅按 `task.actions` 渲染按钮：

- **retry（重试当前任务）**：适用于执行阶段类错误（`METRIC_PERSIST_FAILED` / `METRIC_REVISION_MISMATCH` / `ARTIFACT_GENERATION_FAILED` / `REVIEW_FINDINGS_GENERATION_FAILED` / `REPORT_ASSEMBLY_FAILED` / `PIPELINE_INTERNAL_ERROR`）。复用同一任务，从失败处继续。
- **resubmit（使用当前标注重新生成）**：适用于输入/版本类错误（`ANNOTATION_REVISION_DRIFT` / `NO_KEYPOINT_FRAMES` / `UNSUPPORTED_VIEW` 等），以及 **报告缺失** `REPORT_METADATA_MISSING`。以当前选中的 normalized annotation + 当前 revision 新建一个分析任务，并刷新选中态。
- **details（查看详情）**：非用户可恢复类（`UNSUPPORTED_PIPELINE_VERSION` / `TASK_OWNER_UNAVAILABLE` / `QUALITY_BLOCKED`）仅展示信息。
- **并发保护**：已有活跃 annotation pipeline 任务时再次提交，后端返回 `409 ANALYSIS_TASK_ALREADY_ACTIVE`（含 `existing_task_id`），前端直接绑定并恢复该任务进度，禁止重复创建。

---

## 17.4 运行后端测试

```bash
cd backend
pytest tests/test_guided_workflow_contract.py -q   # 引导工作流读取契约（16.1–16.7）
pytest tests -q                                    # 全量回归
```

契约测试覆盖：标注列表返回 parse/quality/模块就绪、status 返回 pipeline_progress、analysis list 过滤、retry/resubmit 分类、并发 409、报告缺失合成 `REPORT_METADATA_MISSING`、重复解析归属。

> 注意：集成测试需要可用的 PostgreSQL（Docker）。无 DB 时仅 unit 级用例可运行。

---

## 17.5 运行前端类型检查与构建

```bash
cd frontend-vue
npm run test        # vitest 单测（16.8–16.16 行为 + 失败/报告面板渲染）
npm run build       # vue-tsc --noEmit && vite build
```

前端单测覆盖：工作流阶段推导（无视频/有视频无标注/可提交/warning 确认/invalid 阻断/运行中恢复/失败展示/完成报告动作/非 side 机位/报告缺失 resubmit/端到端提交/restoreSelection），以及进度面板与报告面板的失败/新鲜度分支渲染。

---

## 17.6 验证现有 ReportView 与 PDF 导出未被修改

- `WorkspaceView` 仅新增对 `swim-analysis.annotation-kinematics.v1` 的识别与空 keypoint frames 守卫（`overlayResult` 不把空 annotation-pipeline 帧传入旧 OverlayCanvas）；旧 `model_service` 工作台行为保持不变。
- 报告查看与 PDF 导出复用既有 `/reports/:sessionId`、`/sessions/:id/report/pdf` 与 `getReportPdfStatus` / `exportReportPdf` 接口，本变更未修改其契约或渲染逻辑。
- 后端 `ReportMetadata` 模型与 `analysis_results` 持久化结构未改；仅新增读取期投影（`read_analysis_task` / `read_analysis_status` / `build_pipeline_progress` / `build_analysis_common_payload`）。

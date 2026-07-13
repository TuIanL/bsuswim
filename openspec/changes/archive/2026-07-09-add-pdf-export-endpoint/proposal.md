## Why

系统已能生成模块化 `ReportData` 并在前端渲染 section-based 技术报告，但教练和运动员需要一份可下载、可分享、可存档的稳定交付物。当前 `ReportView.vue` 中的导出按钮一直处于 `disabled` 状态，标注"PDF 暂不可用"。为了基地试用和正式交付，需要打通从结构化报告到可下载 PDF 的完整链路。

## What Changes

- 新增 session-level PDF 导出 API，前端无需知道 `report_id`
- 新增前端 `/reports/:sessionId/print` 打印路由，复用现有 section-based renderer
- PDF 生成使用 Playwright 打开前端 print route，不维护后端独立 PDF 模板
- 新增短时 print token 用于 Playwright 鉴权，不暴露无鉴权内部接口
- 新增 `PrintReadyRegistry` 协议，确保图片和图表渲染完成后 Playwright 才打印
- ECharts 雷达图在 print mode 下转为静态 PNG，避免 canvas 打印不稳定
- 新增 `StorageService.save_bytes` 支持 PDF 文件存储
- 跟踪 PDF 导出状态（exporting/exported/failed/stale），防止并发导出
- **BREAKING**: `ReportMetadata` 表新增 `pdf_path`, `pdf_status`, `pdf_exported_at`, `pdf_error`, `pdf_version` 字段

## Capabilities

### New Capabilities
- `pdf-export-service`: 基于 Playwright + 前端 print route 的 PDF 导出能力，包含 print token 鉴权、print-ready 协议、ECharts 静态化、PDF 存储与下载

### Modified Capabilities
- `swim-interactive-performance-report`: PDF 导出从"未来能力"升级为"可用功能"——新增 session-level 导出/下载/状态查询 API，新增 print route 渲染规范

## Impact

- `backend/app/models/report.py`: 新增 PDF 相关字段
- `backend/app/alembic/versions/`: 新增迁移脚本
- `backend/app/services/storage.py`: 新增 `save_bytes()` 方法
- `backend/app/services/pdf_export_service.py`: 新增 PDF 导出服务
- `backend/app/services/playwright_renderer.py`: 新增 Playwright PDF 渲染器
- `backend/app/api/routes/reports.py`: 新增三个 session-level PDF endpoint
- `backend/app/dependencies/`: 可选新增 print token 依赖
- `backend/requirements.txt`: 新增 `playwright`
- `frontend-vue/src/router.ts`: 新增 `/reports/:sessionId/print` 路由
- `frontend-vue/src/views/PrintReportView.vue`: 新增打印页面
- `frontend-vue/src/utils/printReadyRegistry.ts`: 新增 PrintReadyRegistry
- `frontend-vue/src/components/report/shared/ReportRadarChart.vue`: 新增 print mode 支持
- `frontend-vue/src/services/api.ts`: 新增 PDF 导出/下载/状态 API 方法

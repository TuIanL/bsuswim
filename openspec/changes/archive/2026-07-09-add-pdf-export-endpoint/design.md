## Context

系统已完成前 7 个 Change：
- 标注导入 → 标准化 → 指标计算 → 规则诊断 → ReportData 装配 → 前端 section renderer
- 报告页已支持模块化渲染（OverviewSection / ModuleSection / RadarChart）
- 但导出按钮一直处于 disabled 状态

第 8 步目标是把现有结构化报告转换为可交付 PDF，复用前端渲染资产，不维护第二套 PDF 模板。

约束：
- 不重新设计 ReportData
- 不重新计算指标或运行诊断
- 不新增报告编辑器
- 不支持批量导出
- 不可把无鉴权的 print route 暴露给外部

## Goals / Non-Goals

**Goals:**
- 新增 session-level PDF 导出 API（前端只需持有 sessionId）
- 新增前端 `/reports/:sessionId/print` 路由，复用现有 section renderer
- Playwright 打开前端 print route 生成 PDF（选项 A，非 Jinja2）
- 短时 print token 鉴权，不暴露无鉴权内部接口
- PrintReadyRegistry 协议确保图片/图表渲染完成后才打印
- ECharts 雷达图在 print mode 下转为静态 PNG
- 新增 StorageService.save_bytes 支持 PDF 存储
- 跟踪 PDF 导出状态，防止并发导出

**Non-Goals:**
- 不做 Jinja2 后端 PDF 模板
- 不做批量导出
- 不做 Word / PPT 导出
- 不做签名或水印
- 不做异步任务队列（MVP 同步导出 + 超时保护）
- 不做历史导出版本管理（只保留最新版，版本号递增）

## Architecture

```
POST /api/sessions/{session_id}/report/export/pdf
  │
  ├── get_current_user → 校验 session 所有权
  ├── 查找 ReportMetadata（by session_id）
  ├── 状态检查：exporting → 409
  ├── 状态检查：exported + force=false → 直接返回
  │
  ├── pdf_status = exporting
  ├── db.commit()
  │
  ├── DB ops (sync): condition update pdf_status='exporting', commit
  │     (DB session closed before async Playwright work)
  │
  ├── PdfExportService.export_report_pdf(report_id, session_id, user_id):
  │     ├── generate print_token (binding report_id, session_id, user_id, expires_at)
  │     │
  │     ├── Playwright:
  │     │     └── open FRONTEND_BASE_URL/reports/{sessionId}/print?token=xxx
  │     │     └── wait_for_function(__REPORT_PRINT_READY__, timeout=35s)
  │     │     └── page.pdf(A4 landscape, print_background=true)
  │     │
  │     ├── save_bytes(reports/{report_id}/report_vN.pdf)
  │     │
  │     └── return pdf_bytes
  │
  ├── DB ops (sync): re-query report, update pdf_path/pdf_status/pdf_version, commit
  │
  └── return { pdf_url, pdf_status, pdf_exported_at }

GET /api/sessions/{session_id}/report/pdf
  ├── 查找 ReportMetadata
  ├── 校验 pdf_path 非空，否则 409（未导出）或 404（文件丢失）
  ├── 通过 StorageService.resolve_path(report.pdf_path) 获取绝对路径
  ├── 返回 FileResponse(absolute_path, media_type="application/pdf")
  └── 文件名: {athlete}_{stroke}_技术报告_{date}.pdf

GET /api/sessions/{session_id}/report/export/pdf/status
  └── 返回 pdf_status, pdf_exported_at, pdf_error
```

## Data Model

```python
class ReportMetadata(Base):
    # existing fields...
    pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_status: Mapped[str] = mapped_column(String(50), default="not_exported")
    pdf_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_error: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_version: Mapped[int] = mapped_column(Integer, default=0)
```

pdf_status 枚举值：`not_exported`, `exporting`, `exported`, `export_failed`, `stale`

## Print Token

```python
class PrintToken(BaseModel):
    token: str
    report_id: int
    session_id: int
    user_id: int
    purpose: str = "pdf_export"
    expires_at: datetime
    consumed: bool = False
```

Token 存储：MVP 使用内存 dict（本地开发）或 Redis（生产）。
有效期：2 分钟。
校验接口：`GET /api/internal/sessions/{session_id}/report/print-data?token=xxx`，不走普通 user session。

## Print Ready Protocol

```ts
class PrintReadyRegistry {
  private pending = 0
  private resolved = 0
  private done = false

  addTask(): () => void        // 返回 resolve 函数
  startTimeout(ms: number)     // 超时兜底
  private check()              // 全部完成后设置 __REPORT_PRINT_READY__
}
```

注册的资源类型：
- 图片：遍历 DOM 中所有 `<img>`，等待 `img.decode()` or `img.complete`
- 雷达图：ECharts `finished` 事件后调用 `getDataURL()` 替换为 `<img>`
- 字体：`document.fonts.ready`
- 无异步资源：立即 `markReady()`

## Chart Staticization

`ReportRadarChart` 新增 `printMode` prop。在 print mode 下：
1. mounted → render ECharts
2. resize 适应容器
3. 监听 `finished` 事件 → `getDataURL({ type:'png', pixelRatio:2, backgroundColor:'#fff' })`
4. 隐藏 canvas，显示 `<img>`
5. 调用 registry 的 resolve 回调

## Storage

```python
class StorageService:
    async def save_bytes(
        self,
        data: bytes,
        relative_path: str,
        content_type: str = "application/pdf",
    ) -> dict:
        destination = self.base_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return {
            "relative_path": relative_path,
            "absolute_path": str(destination),
            "size_bytes": len(data),
        }

PDF 路径：`reports/{report_id}/report_v{pdf_version}.pdf`

数据库 `pdf_path` 存储相对路径，下载时由 `StorageService.resolve_path(relative)` 解析为绝对路径。

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | 选项 A：Playwright + 前端 print route | 保护第 7 步的前端渲染资产，避免视觉漂移 |
| D2 | API 使用 session_id 而非 report_id | 匹配现有前端路由 `/reports/:sessionId` |
| D3 | 短时 print token 鉴权 | 不暴露无鉴权内部页面，Playwright 不需要模拟登录 |
| D4 | PrintReadyRegistry + 超时 | 分布式 ready 信号，比单个布尔值或固定 wait 稳定 |
| D5 | ECharts → PNG 静态化 | canvas 在 PDF 打印中不稳定，PNG 可控 |
| D6 | 条件 update 防并发 | 轻量，不用引入队列系统 |
| D7 | pdf_version 递增 | force=true 时保留版本追踪 |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Playwright + Chromium 增加部署体积 | MVP 阶段在同一容器内安装；后续可拆独立 worker |
| 前端 print route 和普通报告页视觉不一致 | print route 复用同一套 component，仅加打印 CSS |
| 图片 URL 在 Playwright 中解析失败 | print-data 接口返回绝对 URL；缺图时显示 placeholder |
| ECharts `finished` 事件不触发 | 组件内部 5s 短超时兜底 resolve registry task |
| 并发导出状态竞争 | 条件 update + 409；后续可升级 SELECT FOR UPDATE |

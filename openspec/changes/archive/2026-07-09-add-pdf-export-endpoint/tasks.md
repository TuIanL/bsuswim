## 1. Data model and migration

- [x] 1.1 Add PDF export fields to `ReportMetadata` model:
  - `pdf_path: Mapped[str | None]`
  - `pdf_status: Mapped[str]` default `"not_exported"`
  - `pdf_exported_at: Mapped[datetime | None]`
  - `pdf_error: Mapped[str | None]`
  - `pdf_version: Mapped[int]` default `0`
- [x] 1.2 Create Alembic migration for the new columns.
- [x] 1.3 Add pdf_status enum values: `not_exported`, `exporting`, `exported`, `export_failed`, `stale`.
- [x] 1.4 Implement stale trigger in generate_report and build_swim_report endpoints.

## 2. Storage

- [x] 2.1 Add `StorageService.save_bytes()` and `resolve_path()` methods with relative path storage.
- [x] 2.2 `save_bytes` creates parent directories automatically.
- [x] 2.3 PDF paths format: `reports/{report_id}/report_v{pdf_version}.pdf`.

## 3. Print token

- [x] 3.1 Define PrintToken with token, report_id, session_id, user_id, purpose, expires_at, read_count.
- [x] 3.2 Implement in-memory token generation and storage.
- [x] 3.3 Token allows repeated reads within 2-minute lifetime (not consumed on first use).
- [x] 3.4 Token expiry: 2 minutes.

## 4. Backend API endpoints

- [x] 4.1 Add `POST /api/sessions/{session_id}/report/export/pdf` async endpoint with condition update lock.
- [x] 4.2 Add `GET /api/sessions/{session_id}/report/pdf` download endpoint with FileResponse.
- [x] 4.3 Add `GET /api/sessions/{session_id}/report/export/pdf/status` endpoint.
- [x] 4.4 Add `GET /api/internal/sessions/{session_id}/report/print-data?token=xxx` internal endpoint.

## 5. Playwright PDF renderer

- [x] 5.1 Add `playwright` to `requirements.txt`.
- [x] 5.2 Add `backend/app/services/playwright_renderer.py` with async render_pdf_from_url.
- [x] 5.3 Add `backend/app/services/pdf_export_service.py` with PdfExportService.

## 6. Frontend print route

- [x] 6.1 Add `/reports/:sessionId/print` route to router.
- [x] 6.2 Create `PrintReportView.vue` with print CSS, token-based data loading, reuse normalizeReportData.
- [x] 6.3 Add print CSS: A4 landscape, page-break, hidden interactive elements.

## 7. Print readiness

- [x] 7.1 Add `PrintReadyRegistry` class with addTask, startTimeout, __REPORT_PRINT_READY__.
- [x] 7.2 Integrate PrintReadyRegistry into PrintReportView.vue: images, fonts, immediate fallback.

## 8. Chart staticization

- [x] 8.1 Add `printMode` prop to `ReportRadarChart.vue`.
- [x] 8.2 In `printMode`: render ECharts, wait for finished event, getDataURL, replace canvas with `<img>`.

## 9. Frontend export UI

- [x] 9.1 Add PDF export/status/download API methods to `api.ts`.
- [x] 9.2 Update `ReportView.vue`: active export/download button, handle idle/exporting/exported/failed/stale states.

## 10. Deployment

- [x] 10.1 Add `playwright` to `requirements.txt`.
- [x] 10.2 Documented: run `playwright install chromium` in backend setup (manual step).
- [x] 10.3 Add environment config: `FRONTEND_BASE_URL`, `PDF_RENDER_BASE_URL`, `BACKEND_PUBLIC_BASE_URL`.
- [x] 10.4 Documented: server/proxy timeout should exceed 35s (config).

## 11. Tests

- [x] 11.1-11.4 Marked as `@pytest.mark.integration` — skip locally, run in CI.
- [x] 11.5 Save_bytes and storage: 3 unit tests passed.
- [x] 11.6 Print-token: 6 unit tests passed.
- [ ] 11.7 Print route `__REPORT_PRINT_READY__` (needs frontend dev server).
- [ ] 11.8 ReportRadarChart printMode (needs browser/Vue).
- [ ] 11.9-11.11 Marked as `@pytest.mark.integration` — skip locally, run in CI.

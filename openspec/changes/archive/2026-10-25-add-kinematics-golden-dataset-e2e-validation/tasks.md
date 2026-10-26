# Tasks — add-kinematics-golden-dataset-e2e-validation

> **状态：已收敛（2026-10-25 回写）**
>
> 2026-09-09 提交 `deb4ade` 已把原 167 项 granular 清单合并为一套可维护门禁：「将 167 项的 golden dataset change 收敛为一套可维护的开发质量门禁」。
> 本文件按**实际产物**重写：已交付的逐条列证据；未落地的直接移出范围，不再保留为待办。

## 1. Golden fixture 包（已完成）

- [x] 1.1 `backend/tests/fixtures/kinematics_golden_v1/` 建立，含 manifest + source + expected + mutations
- [x] 1.2 source：`annotations.xml`（105 image / 104 骨架）、`frame_mapping.json`（显式帧号表）、`side_view_golden.mp4`（421 帧 / 3840×2160 / 60fps / 20 MB）
- [x] 1.3 expected：`ingest_contract.json`、`metric_contract.json`、`report_contract.json`
- [x] 1.4 mutations：`missing_right_wrist.recipe.json` + `mutations.py`（确定性生成）
- [x] 1.5 `__init__.py` loader：校验 video 与 XML 的 SHA-256，缺失/不匹配即 `GoldenFixtureError`，不回退 synthetic
- [x] 1.6 路径逃逸防护与 manifest 一致性校验 — `tests/golden/test_fixture_contract.py`（6 项）
- [x] 1.7 fixture README 说明坐标、FPS、mapping、授权边界

## 2. CVAT 解析契约（已完成）

- [x] 2.1 真实 XML 解析产出非空帧 — `tests/golden/test_cvat_golden_parser.py:39`
- [x] 2.2 active frame 数 = 104 — `:43`
- [x] 2.3 frame range = 0..104 — `:49`
- [x] 2.4 每帧 17 个 COCO17 关节点 — `:60`
- [x] 2.5 关节点 schema 与 COCO17 完全一致 — `:68`
- [x] 2.6 baseline visibility 非 missing — `:86`
- [x] 2.7 无重复 active frame — `:94`
- [x] 2.8 `native_metadata.parsed_frame_count` 与实际一致 — `:99`
- [x] 2.9 warnings 汇总使用 `all_warnings` 单一变量，无 NameError — `normalized_annotation_service.py`

## 3. 服务层端到端（真数据，不 mock）（已完成）

- [x] 3.1 真实 fixture 走 ingest → metric → artifact → finding → report 全链 — `tests/golden/test_golden_analysis_contract.py:42`
- [x] 3.2 断言 `len(keypoint_frames) == active_frames` 且 `frame_mapping.verified is True`、`revision == 1` — `:80-82`
- [x] 3.3 断言指标 payload 与报告 payload 无 NaN/Infinity — `assert_finite_numbers`
- [x] 3.4 断言 canonical key 集合与计算器一致 — `test_kinematics_report.py`（`assert_canonical_metric_keys`）
- [x] 3.5 五类资产：ready 文件存在、`size_bytes` 与 `checksum_sha256` 与实际一致、`mime_type` 非空 — `:120-127`
- [x] 3.6 资产 URL 指向 `/uploads/` 存储路径 — `test_kinematic_artifacts.py:326`
- [x] 3.7 产物同 revision：artifact / finding / report source_trace — `:108-113`
- [x] 3.8 五页报告契约（5 sections / page_number / 页序 / profile） — `assert_five_page_contract`
- [x] 3.9 claim-bearing 字段禁用词（速度/划幅/SWOLF/推进力/阻力/功率） — `assert_no_unsupported_claims`
- [x] 3.10 缺右腕 mutation：指标序列不可用、`ArtifactSet.status=partial`、存在 skipped+skip_reason、report `status=partial` 且 upper_limb 页 partial/unavailable — `:143`

## 4. HTTP + 浏览器 + PDF E2E（已完成，nightly 门禁）

- [x] 4.1 真实 HTTP：register → login → athlete → session — `tests/e2e/test_golden_full_stack.py`
- [x] 4.2 真实上传 golden MP4 并绑定 side video（带 fixture FPS/resolution）— `:147-175`
- [x] 4.3 multipart ingest 真实 XML → 返回 `normalized_annotation_id` — `:177-195`
- [x] 4.4 提交 annotation_kinematics → 轮询至 completed — `:197-236`
- [x] 4.5 报告 generation signature 与 source_trace 一致 — `:248-251`
- [x] 4.6 PDF 导出 `pdf_status=exported`、下载内容以 `%PDF` 开头 — `:253-271`
- [x] 4.7 PDF 严格 5 页 + 每页 semantic marker — `assert_pdf_page_count` / `assert_pdf_semantic_markers`
- [x] 4.8 独立 workflow：Postgres + Chromium + ffmpeg + 活栈前后端 — `.github/workflows/golden-e2e.yml`

## 5. 打印契约（已完成）

- [x] 5.1 `PrintReadyRegistry` 在图片/图表/字体就绪后才置 ready — `frontend-vue/src/utils/printReadyRegistry.ts`
- [x] 5.2 不得在 `finally` 无条件置 ready；失败写 `__REPORT_PRINT_ERROR__` — `PrintReportView.vue:58`
- [x] 5.3 布局溢出写 `PRINT_LAYOUT_OVERFLOW` 并阻止导出 — `PrintReportView.vue:90`
- [x] 5.4 print route 只输出 5 个 `.print-page`，无额外封面 — `PrintReportView.spec.ts`

## 6. CI 与基线治理（已完成）

- [x] 6.1 每 PR 跑 `tests/golden -m golden_contract` — `.github/workflows/ci.yml`
- [x] 6.2 baseline 只能经 `build_kinematics_golden_fixture.py` 生成候选、`approve_kinematics_golden_baseline.py` 人工审批
- [x] 6.3 CI 只读 baseline，不写回
- [x] 6.4 旧 synthetic snapshot 降级为 `synthetic_five_page_report_contract.json`，普通 pytest 不再写 baseline

---

## 已移出范围（不保留为待办）

| 原条目 | 原因 |
|---|---|
| representative frame 有效性断言（原组 6） | `assert_representative_frame_valid` 定义了但**从未被任何测试调用**；规格中该要求已删除 |
| 时间序列单调 / 相邻帧连续性断言 | `assert_time_series_ordered`、`assert_adjacent_frame_continuity` 从未被调用；规格中已删除 |
| metric categories 独立断言 | `assert_metric_categories` 从未被调用；category 由 `CANONICAL_KEYS` 映射唯一确定，无需重复断言 |
| 资产 URL 返回 HTTP 200 + MIME 一致性 | 只断言 URL 指向 `/uploads/`；无 HTTP 取回与 MIME 比对测试 |
| findings evidence metric/frame 有效性校验 | 只断言 `FindingSet.status == ready` 与报告禁用词；无逐条 evidence 校验 |
| 页面级 quality note 隔离的 `MUST NOT` 断言 | 只有模块级过滤函数与其纯函数单测，无页面级断言 |
| metric tolerance 数值基线批准 | `expected/metric_contract.json` 仍为 `pending_runtime_approval`，仅锁定结构（finite / monotonic 声明 / canonical key 来源），未锁数值 |
| full-stack E2E 每 PR 硬门禁 | 现为 nightly（18:00 UTC）+ `workflow_dispatch`；每 PR 会显著拖慢且需活栈 |
| 陈旧帧号与 affine 假设（`offset=32` / `stride=1` / `0..55` / `32..87` / `356` 帧） | 与真实 fixture 不符（实为 0..104、explicit mapping、`source_original_offset=270`、effective 15fps）；已从规格与任务中删除 |

## 验证方式

```bash
cd swim/backend
python -m pytest -q tests/golden -m golden_contract      # 每 PR 门禁
GOLDEN_E2E_ENABLED=1 python -m pytest -q tests/e2e -m golden_e2e   # 需活栈
```

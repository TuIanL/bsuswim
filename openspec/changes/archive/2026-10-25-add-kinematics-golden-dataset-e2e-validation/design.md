## Context

`annotation_kinematics` pipeline 已能编排指标、资产、发现、报告与 ReportMetadata，但测试底座原以合成数据与 service-level 调用为主：`build_golden_annotation(50)` 这类程序生成数据，`golden_five_page_report.json` 快照由测试运行期间自动覆盖。

本 Change 的目标不是重复子模块单测，而是验证真实输入跨越所有系统边界后仍满足共同契约。真实数据暴露了四个只有真跑才会显现的缺陷，均已修复：

- `normalized_annotation_service.py` 在 CVAT 分支引用未定义局部变量 `warnings`，真实 XML ingestion 触发 `NameError`。
- `PrintReportView.vue` 先渲染独立封面页再遍历 5 个 section，PDF 实际 6 页；`finally` 中无条件置 ready。
- `_build_video_context` 从 `VideoFile` 读取 `fps`/`width`/`height`，但该模型没有这些列，报告 FPS 恒为 null。
- `artifact_quality_notes` 全局传入 P2–P5，未按页面来源模块过滤。

> 2026-10-25 收敛：本文档只保留**已落地**的设计决策；未实现的设计已移入文末「已放弃的设计决策」。

## Goals / Non-Goals

**Goals**

1. 用真实衍生数据验证生产链路，而非在测试中直接构造 NormalizedAnnotation。
2. 验证 API、数据库、文件系统、视频解码、前端与 Playwright 之间的集成。
3. 关节点缺失时只降级受影响模块，整条任务不得失败。
4. 保证 HTML 与 PDF 来源于同一份 ReportData。
5. 防止无数据依据的指标与结论进入报告。

**Non-Goals**

1. 不对浮点值做逐字 snapshot 或固定二进制 hash 比较。
2. 不在测试中静默重新生成并接受新 baseline。
3. 不新增运动学指标、不改诊断阈值、不训练或接入新模型。
4. 不对其他 report profile 做推测性视频元数据修复。

## Decisions

### Decision 1: 使用版本化真实衍生 fixture

profile 固定为 `kinematics-golden.v1`，目录：

```
kinematics_golden_v1/
├── README.md
├── fixture_manifest.json
├── __init__.py                  # loader + SHA-256 校验
├── source/{annotations.xml, frame_mapping.json, side_view_golden.mp4}
├── expected/{ingest,metric,report}_contract.json
└── mutations/missing_right_wrist.recipe.json + mutations.py
```

视频经授权、脱敏、重编码后直接入库（421 帧 / 3840×2160 / 60fps / 20 MB），避免 Git LFS 与私有 artifact 依赖。fixture 缺失或 checksum 不匹配时直接失败，不回退 synthetic。

### Decision 2: 帧映射用显式帧号表，不用 affine

实际素材的标注间隔并非等距（101 段 ×4 + 1 段 ×8），任何 `stride × n + offset` 公式都会漂移。因此：

- `frame_mapping.mode = explicit`
- 逐条记录 annotation frame ↔ XML 原始帧号 ↔ 裁剪视频帧号 ↔ 是否有骨架
- `source_original_offset = 270`（XML 帧号 270 对应裁剪视频帧 0）
- `annotation_fps_effective = 15`，`verified = true`，`verification_reason = user_confirmed_source_frame_manifest`

### Decision 3: Golden contract 只锁结构，不锁数值

- **精确契约**：schema version、calculator/generator/rule set/assembler version、active frame 数与 range、joint schema 与 count、canonical metric key 集合（以 `calculator.CANONICAL_KEYS` 为权威，不写死 23）、五种 artifact type、section count/page number/page type/顺序、annotation revision。
- **自洽契约**：动态数据库 ID 只断言非空且相互引用一致；generation signature 只断言非空且 API 与 source_trace 一致；资产 checksum 与实际文件一致；PDF 页数 = 5 且含 semantic marker。

`expected/metric_contract.json` 当前只锁定结构（finite、time_series_monotonic 声明、canonical_keys_source），数值包络尚未人工批准，status 保持 `pending_runtime_approval`。

### Decision 4: 有效帧与 visibility 基线

真实 XML 含 105 个 `<image>`，其中 104 帧带骨架（id=95 / 原始帧 650 缺）。active frame 为 0..104，每个 active frame 含 COCO17 的 17 个点，baseline 全部非 `missing`。parser 采用 `outside=1 → missing`、`occluded=1 → occluded`、其他 `→ visible`。

### Decision 5: 两层测试

- **Golden contract suite**（`backend/tests/golden/`，标记 `golden_contract`）：真实 XML 解析、真实 ingest、数据库持久化、指标/资产/发现/报告、文件与 revision trace。每 PR 门禁。
- **Full-stack golden E2E**（`backend/tests/e2e/test_golden_full_stack.py`，标记 `golden_e2e`）：真实 HTTP 上传/绑定/ingest/analysis/report、真实前端 print route、真实 Playwright PDF。nightly + 手动触发。

E2E 不得 mock：StorageService、CVAT parser、metrics calculator、artifact renderer、report assembler、前端 print route、Playwright renderer。

### Decision 6: 指标与报告数值安全

递归检查 metrics 与 report payload：禁止 NaN、禁止正负 Infinity。calculator 已有 NaN/Inf → None 的 sanitize，E2E 仍验证持久化后的最终 JSON。

### Decision 7: 五类 artifact 验证

五类：`annotated_keyframe`、`time_series_chart`、`trajectory_chart`、`range_chart`、`radar_chart`。每个 ready artifact 满足：文件存在、`size_bytes` 与实际一致、`checksum_sha256` 与实际一致、`mime_type` 非空、URL 指向 `/uploads/` 存储路径；非 ready 必须带 `skip_reason`。不做像素级截图比较。

### Decision 8: 缺失关节点降级

由 baseline XML 在测试运行时按 recipe 生成 mutation（不维护第二份手写 XML），把所有 active frame 的 `right-wrist` 置为 missing。预期：ingestion 成功、pipeline 完成、`right_elbow_angle_deg` 序列无可用值、`ArtifactSet.status = partial` 且有 skipped+reason、`FindingSet.status = ready`、report `status = partial` 且 `upper_limb_kinematics` 页 partial/unavailable、任务不得 failed。

### Decision 9: HTML 与 PDF 语义一致

打印页带稳定属性：`data-report-generation-signature`、`data-page-number`、`data-page-type`、`data-module-key`，页脚含语义标识（如 `P3 | upper_limb_kinematics`）。验证：API generation signature 与 source_trace 一致、PDF 严格 5 页、每页含对应 marker。

### Decision 10: PrintReportView 严格输出五页

`FivePageKinematicsReport.sections` 即五个页面，print route 不再额外创建封面页。`__REPORT_PRINT_READY__` 仅在 print-data 成功、schema 校验通过、5 个 section 挂载完成、字体 ready、图片完成或明确失败、图表静态化完成后置 true；失败写 `__REPORT_PRINT_ERROR__ = { code, message }`，不得在 `finally` 无条件置 ready。

布局预检：遍历 `.print-page`，`scrollHeight > clientHeight + 2` 则写 `PRINT_LAYOUT_OVERFLOW` 并阻止导出，不用 `overflow:hidden` 静默截断。

### Decision 11: 禁止无依据结论

只检查 claim-bearing paths：`summary.top_findings`、`section.metrics`、`section.findings`、`priority_review_findings`、`objective_metric_summary`、`recommendations/retest metrics`。禁用：`speed_mps`/`average_speed_mps`、`stroke_length_m`、`swolf`、`propulsive_force`、`drag`、`power_w`、`hip_depth_cm` 及中文等价表述。允许出现在 `analysis_boundaries`、`limitations`、`quality_notes`、`disclaimer`，但须明确表达「不提供 / 不可计算 / 需额外数据」。

### Decision 12: Source revision 贯穿全部产物

`NormalizedAnnotation.revision = AnnotationMetric.source_revision = ArtifactSet.source_annotation_revision = FindingSet.source_annotation_revision = report.source_trace.annotation_metric.source_revision`。任一不一致即失败。

### Decision 13: Baseline 不允许自动更新

更新 expected contract 必须走 `scripts/build_kinematics_golden_fixture.py` 生成候选，再由 `scripts/approve_kinematics_golden_baseline.py` 人工审批。CI 只读 baseline。

### Decision 14: synthetic snapshot 降级

`golden_five_page_report.json` 已重命名为 `synthetic_five_page_report_contract.json`，降级为 structure contract；普通 pytest 不再写 baseline。`golden` 一词自此只指真实衍生、人工批准、禁止自动更新的 fixture。

### Decision 15: 视频元数据 provenance

`side_2d_kinematics_5page_v1` 的 video context：`SessionVideo.fps` 为权威 FPS、`SessionVideo.resolution` 为权威分辨率，`VideoFile` 仅提供 id 与 filename，无权威时长时 `duration_sec = null`，不得读取 `VideoFile.fps/width/height/duration_sec`。

生产 Web 路径已落地 ffprobe 探测：上传时 `probe_video_metadata()` 返回 `probed_fps` / `resolution` / `metadata_source=ffprobe` / `fps_verified`，前端绑定 SessionVideo 时透传。

### Decision 16: 模块级 artifact quality notes

`artifact_projection.py` 把 note 丰富为 `{code, level, message, artifact_key, module_key, metric_keys, artifact_status}`；页面组装按本页 `source_module_keys` 过滤后再接收。

## 已放弃的设计决策

| 原设计 | 放弃原因 |
|---|---|
| Decision 原 2：affine mapping（offset=32、stride=1、0..55、32..87） | 与真实素材不符：间隔非等距、帧号从 270 起、共 104 帧。改为显式帧号表 |
| 原 Decision 8：Representative frame 契约（annotation_frame ∈ 0..55 等） | `assert_representative_frame_valid` 定义后从未接入任何测试；规格中已删除该要求 |
| 原 Decision 7 中：角度 [0,180]、time series 单调、adjacent delta 阈值 | 无对应断言；依赖未批准的数值基线 |
| 原 Decision 3 中：key-set SHA-256 锁定 | `expected/metric_contract.json` 未实现 hash 锁定，只记录 `canonical_keys_source` |
| 原 Decision 9 中：public URL 返回 200、Content-Type 与 mime_type 一致 | 只断言 URL 指向 `/uploads/`，无 HTTP 取回与 MIME 比对 |
| 原 Decision 18 中：P2/P4 MUST NOT 出现 upper-limb note 的页面级断言 | 只有模块级过滤函数与纯函数单测，无页面级断言 |
| 原 Migration Plan：golden_e2e 观察 20 次后升级为每 PR required | 未执行；维持 nightly + 手动，不承诺升级时间 |
| 原 Open Questions：视频发布模型、FPS 来源 | 均已定案：视频入库（20 MB 重编码）、后端 ffprobe 探测 |

## Risks / Trade-offs

- **[基础设施型误报]** golden_e2e 依赖 PostgreSQL、Vue、Chromium、Playwright、FFmpeg，任一缺失即红但与代码无关 → 用独立 `E2E_INFRA_ERROR` 码区分环境失败与产品断言失败；PR 门禁只跑 contract。
- **[PDF 渲染漂移]** 不同 OS/字体下 PDF 二进制不一致 → 只验证页数与语义 marker。
- **[内容溢出导致 6 页]** → 严格断言 5 页 + 导出前布局预检。
- **[baseline 漂移]** → 运行时断言 key 集合与 `CANONICAL_KEYS` 一致；数值基线未批准前不锁数值。

## 收敛记录

- 2026-09-09 `deb4ade`：把 167 项 granular 任务收敛为可维护门禁（fixture + contract + nightly E2E）。
- 2026-10-25：删除未落地的要求与决策，修正陈旧帧号/映射假设，回写 `tasks.md` 与 4 份 delta spec。详见 `RECONCILIATION-2026-10-25.md`。

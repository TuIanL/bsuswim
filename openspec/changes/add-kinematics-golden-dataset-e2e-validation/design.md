## Context

当前 annotation_kinematics pipeline 已经编排指标、资产、发现、报告和 ReportMetadata，但测试底座仍以合成数据和 service-level 调用为主。现有 `backend/tests/` 下的 kinematics 测试（test_cvat_parser、test_side_2d_kinematics、test_kinematic_artifacts、test_review_findings、test_kinematics_report）使用 `build_golden_annotation(50)` 这类程序生成数据，且 `test_kinematics_report.py` 中的 `golden_five_page_report.json` 快照由测试运行期间自动覆盖，并非受控 baseline。Change 9 的目标不是重复每个子模块的单元测试，而是验证真实输入跨越所有系统边界后，最终产物仍然满足共同契约。

通过代码核对，确认了若干真实缺陷，它们只有在真实数据下才会显现：

- `normalized_annotation_service.py:332` 在 CVAT 分支引用未定义的局部变量 `warnings`，真实 XML ingestion 会触发 `NameError`。
- `PrintReportView.vue` 先渲染一个独立 cover page，再遍历 5 个 section，使 PDF 实际为 6 页；且 `finally` 中无条件设置 `__REPORT_PRINT_READY__`。
- `kinematics_report/page_builders.py:_build_video_context` 从 `VideoFile` 读取 `fps`/`width`/`height`，但 `VideoFile` 模型只有文件名、路径、MIME、大小、checksum，并不含这些字段，因此报告 FPS 恒为 null、分辨率为 `?x?`。权威字段是 `SessionVideo.fps` 与 `SessionVideo.resolution`。
- `kinematics_report/page_builders.py` 将全局 `artifact_quality_notes` 直接传入 P2/P3/P4/P5，未按页面来源模块过滤，缺失右腕导致的上肢资产警告可能泄漏到无关页面。

本 Change 假设以下能力已实现：CVAT skeleton annotation ingestion、automatic annotation ingestion workflow、side-2d kinematics metrics、kinematic visual artifact generation、2d kinematics review findings、five-page kinematics report、annotation-driven analysis pipeline、guided side-2d Web workflow、pdf-export-service。

## Goals / Non-Goals

**Goals:**

1. 使用真实衍生数据验证生产链路，而不是在测试中直接构造 NormalizedAnnotation。
2. 验证 API、数据库、文件系统、视频解码、前端和 Playwright 之间的集成。
3. 对稳定契约进行精确断言，对浮点结果使用人工批准的容差。
4. 当某一关节点缺失时，验证 affected metric/module 降级，而不是整个任务失败。
5. 保证 HTML 与 PDF 都来源于同一份 ReportData。
6. 防止无数据依据的指标和专业结论进入报告。
7. 修复上述由真实 E2E 暴露的最小生产链路问题。

**Non-Goals:**

1. 不把某次计算产生的所有浮点值逐字 snapshot。
2. 不比较 PNG、SVG 或 PDF 的固定二进制 hash。
3. 不依赖 created_at 判断 current product。
4. 不在测试中静默重新生成并接受新的 baseline。
5. 不将未经授权的原始运动员视频提交到公开仓库。
6. 不增加新的运动学指标，不修改诊断阈值，不训练或接入新模型。
7. 不对其他 report profile 做推测性视频元数据修复。

## Decisions

### Decision 1: 使用版本化真实衍生 fixture

fixture profile 固定为 `kinematics-golden.v1`。推荐目录：

```
backend/tests/fixtures/kinematics_golden_v1/
├── README.md
├── fixture_manifest.json
├── source/
│   ├── annotations.xml
│   ├── instances_default.json
│   └── side_view_golden.mp4
├── expected/
│   ├── ingest_contract.json
│   ├── metric_contract.json
│   └── report_contract.json
└── mutations/
    └── missing_right_wrist.recipe.json
```

真实原始素材不得直接因测试便利而公开提交。提交到仓库的 MP4 必须满足：已获得使用授权；不包含不必要的身份信息；只保留本次 56 帧分析所需的最小片段及必要前置帧；坐标空间与 XML 一致；使用固定编码参数生成；SHA-256 写入 fixture_manifest.json。如果公开视频不被允许提交，则 CI 从受控私有 artifact 下载并校验相同 SHA-256。测试不得在 fixture 缺失时静默改用合成数据。

`mutations/missing_right_wrist.recipe.json` 是 declarative mutation recipe（不是第二份手写 XML），示例：

```json
{
  "operation": "set_visibility",
  "joint": "right-wrist",
  "frames": "all_active",
  "visibility": "missing"
}
```

测试运行时读取 recipe 由 baseline annotations.xml 生成变体，不维护第二份手写 XML。

### Decision 2: 锁定真实帧映射

当前 CVAT image manifest 从 `scene00032.jpg` 开始，因此 annotation frame 0 对应的候选 source video frame 为 32。fixture 使用显式、人工确认的 affine mapping：

```
mode = affine
source_frame_offset = 32
source_frame_stride = 1
confirmed = true
verification_reason = user_confirmed
```

得到 annotation frames 0..55 对应 source video frames 32..87。该映射必须在制作 fixture 时对原始视频逐帧核验；`instances_default.json` 只作为辅助证据，不能单独把 mapping 提升为 verified。golden contract 必须同时断言 `mode == affine`、`verified is True`、`verification_reason == user_confirmed`、`offset == 32`、`stride == 1`，并在 E2E 显式传 confirmed override 后验证最终 `verification_reason` 没有变成 `inferred_from_filename_sequence`。fixture FPS 取自经 ffprobe 核验的原视频，不在测试代码中默认写死 60。

### Decision 3: Golden contract 分为三类

- **A. 精确契约（固定值，CI 必须严格相等）**：schema version、calculator/generator/rule set/assembler version、有效帧数、joint schema 与 joint count、annotation frame range、source video frame range、四个指标 category、canonical metric key 集合与每个 key 的 category（以 `calculator.CANONICAL_KEYS` 为权威来源，不写死数字 23）、五种 artifact type、section count/page number/page type/顺序、annotation revision（baseline 中 ==1）、verified frame mapping 字段、禁止输出的 metric key。
- **B. 带容差数值契约**：`metric_contract.json` 保存经人工审阅的数值包络（min/max/expected_value/absolute_tolerance/max_adjacent_delta），首次通过真实 fixture 计算后由开发者和业务人员人工确认。
- **C. 自洽契约（只验证内部一致，不锁定具体值）**：动态数据库 ID（annotation/metric/artifact/finding 的实际 ID 只断言非空且相互引用一致，不锁定固定值）；generation signature（只断言格式合法、非空、且在 API/HTML/print-data 三处表面完全一致，不锁定某个固定签名值）；图像实际 checksum 与数据库 checksum 一致；PDF 合法且页数=5；PDF 每页存在语义标识；资产 URL 返回内容与 metadata 一致。

注意：canonical key 的权威来源是 `side_2d_kinematics` 计算器的 `CANONICAL_KEYS`；`23` 只是 calculator 1.0.0 的当前结果，不得作为独立于计算器的第二份定义。

### Decision 4: 有效帧和 visibility 基线

基线 fixture 输入契约：CVAT job sequence 为 356 帧；active annotated frame 为 56 帧；active annotation frame 为连续的 0..55；每个 active frame 包含 COCO17 的 17 个点；baseline 中 17 个点均为 visible；all-outside skeleton 只表示上一 track 终止，不形成重复 active frame；每个 frame 只能存在一个 active skeleton。parser 采用 `outside=1 → missing`、`occluded=1 → occluded`、其他 `→ visible`。

### Decision 5: 两层测试，但共同构成 Change 9

- **Golden contract suite**（`backend/tests/golden/test_kinematics_golden_contract.py`，标记 `golden_contract`）：真实 XML parser、真实 ingest、数据库持久化、annotation pipeline、metrics/artifacts/findings/report、存储文件和 revision trace。
- **Full-stack golden E2E**（`backend/tests/e2e/test_kinematics_golden_web_pdf.py`，标记 `golden_e2e`）：实际 HTTP 上传/绑定/ingest/analysis/report、实际前端 print route、实际 Playwright PDF export、PDF 页数与页面语义验证。

full-stack E2E 不得 mock：StorageService、CVAT parser、metrics calculator、artifact renderer、report assembler、前端 print route、Playwright renderer。允许 mock 的只有外部通知等无关服务。

### Decision 6: 完整 E2E 执行流程

1. 创建 coach 和 athlete；2. 创建 freestyle TrainingSession；3. POST /videos/upload 上传 golden MP4；4. POST /sessions/{id}/videos 绑定为 side 并传入 fixture FPS；5. annotation ingest endpoint 上传 annotations.xml；6. parse_options 提供 confirmed affine frame mapping；7. 检查 normalized annotation 与 analysis readiness；8. POST /analysis/submit（pipeline_type=annotation_kinematics，pipeline_version=side_2d_v1，normalized_annotation_id=ingest 响应 ID）；9. 等待任务 completed；10. 读取 AnalysisResult/AnnotationMetric/ArtifactSet/FindingSet；11. GET /reports/{session_id}；12. 打开实际报告页面验证 section DOM；13. 调用 PDF export endpoint；14. 下载 PDF 验证页数与内容。

### Decision 7: 指标安全性和连续性

测试递归检查 metrics payload：禁止 NaN、禁止正负 Infinity、JSON 序列化后不得出现 NaN/Infinity 字面量；角度值位于 [0,180]；sample_count 不得大于有效帧数或合理双侧展开数量；time series 按 annotation frame 单调排列；只对连续 source video frame 计算 adjacent delta；adjacent delta 必须小于 metric_contract 中人工批准的阈值。calculator 已有 NaN/Inf → None 的 sanitize，E2E 仍需验证持久化后的最终 JSON。

### Decision 8: Representative frame 契约

每个非空 representative frame 必须满足：annotation_frame 属于 0..55；annotation_frame 在 NormalizedAnnotation.keypoint_frames 中存在；verified mapping 下 source_video_frame = annotation_frame + 32；source_video_frame 属于 32..87；time_sec 与 FPS、source frame mapping 一致；对应 metric availability 不能为 unavailable；extractable=true 时必须能从 golden MP4 解码到精确帧。

### Decision 9: 五类 artifact 验证

完整基线至少存在五种 artifact type：annotated_keyframe、time_series_chart、trajectory_chart、range_chart、radar_chart。每个 ready artifact 必须满足：storage_path 存在、文件长度大于 0、实际 SHA-256 与数据库 checksum_sha256 相同、MIME 与扩展名一致、width/height 大于 0、public URL 返回 200、Content-Type 与 artifact.mime_type 一致。关键帧资产额外要求 annotation_frame/source_video_frame 合法且 source_annotation_revision 与 metric.source_revision 一致。不进行固定像素截图比较。

### Decision 10: 缺失关节点降级测试

由 baseline annotations.xml 在测试运行时生成 mutation（不维护第二份手写 XML），将所有 active frame 的 `right-wrist` 设为 `outside=1`。预期：ingestion 成功、pipeline 完成、right_elbow_angle_deg unavailable 且 sample_count=0、left_elbow_angle_deg 仍 available 或 low_confidence、body_posture/lower_limb/head_trunk 不被错误 blocked、右侧肘部关键帧资产可 skipped、ArtifactSet 可 partial、五页报告仍生成、P3 upper_limb_kinematics 出现对应质量说明、整条任务不得 failed。

### Decision 11: HTML 与 PDF 一致性使用语义比较

前端打印页增加稳定属性：`data-report-generation-signature`、`data-page-number`、`data-page-type`、`data-module-key`，每页底部增加稳定低干扰语义标识（如 `P3 · upper_limb_kinematics`）。验证：API ReportData generation_signature 与 print-data 相同、HTML DOM section 数量为 5、DOM 页序与 API sections 一致、PDF 页数严格为 5、PDF 每页包含对应 page semantic marker、PDF 五个页标题与 ReportData 一致。

### Decision 12: PrintReportView 严格输出五页

FivePageKinematicsReport.sections 已定义五个页面内容，print route 不再额外创建独立封面页。正确结构：

```html
<div class="print-report">
  <section v-for="section in viewModel.sections" class="print-page">
    ...
  </section>
</div>
```

第 1 页 overview section 自身承担概况页职责。`window.__REPORT_PRINT_READY__` 只能在以下条件全部满足后变为 true：print-data 请求成功、ReportData schema 校验成功、五个 section 完成挂载、字体 ready、所有图片完成或被明确标记失败、图表静态化完成。加载失败时设置 `window.__REPORT_PRINT_ERROR__ = { code, message }`，不得在 finally 中无条件设置 ready。Playwright renderer 在观察到 PRINT_ERROR 或 ready 超时后必须失败。

前端增加布局预检：遍历 `.print-page`，若 `scrollHeight > clientHeight + 2` 则设置 `__REPORT_PRINT_ERROR__ = { code: 'PRINT_LAYOUT_OVERFLOW', pageNumber }` 并返回，不通过 `overflow:hidden` 静默截断。CSS 调整：`.print-page { break-after: page; }` 与 `.print-page:last-child { break-after: auto; }`。

### Decision 13: 禁止无依据结论

检测器只检查 claim-bearing paths：summary.top_findings、section.metrics、section.findings、priority_review_findings、objective_metric_summary、recommendations/retest metrics。禁止的 metric key 或确定性结论：speed_mps/average_speed_mps、stroke_length_m、swolf/swolf_value、propulsive_force/propulsion、drag、power_w、hip_depth_cm、真实速度、划幅、SWOLF、推进力、水阻数值、功率。这些词允许出现在 analysis_boundaries、limitations、quality_notes 和 disclaimer 中，前提是语义明确表达"不提供、不可计算或需额外数据"。

### Decision 14: Source revision 必须贯穿全部产物

测试必须验证：NormalizedAnnotation.revision = AnnotationMetric.source_revision = KinematicArtifactSet.source_annotation_revision = KinematicReviewFindingSet.source_annotation_revision = ReportData.source_trace.annotation_metric.source_revision = section assets 的 source_annotation_revision。ReportData 还必须记录 annotation_metric ID、artifact generation signature、finding generation signature、report generation signature。任何一处 revision 不一致都应使 golden test 失败。

### Decision 15: Baseline 不允许自动更新

更新 expected contract 必须显式命令：`scripts/build_kinematics_golden_fixture.py --source-dir ... --output-dir ... --write-candidate`，随后 `scripts/approve_kinematics_golden_baseline.py --candidate ... --reason "<change-id>"`。脚本必须输出修改前后 schema/version、数值差异、findings 差异、asset plan 差异、report page 差异。CI 只能读取 baseline，不能修改 baseline。

### Decision 16: 现有 synthetic snapshot 迁移

`backend/tests/fixtures/golden_five_page_report.json` 重命名为 `synthetic_five_page_report_contract.json`，并降级为 synthetic structure contract。删除普通 pytest 中自动写 baseline 的逻辑；旧文件缩减为真正被断言的结构字段（schema_version、report_profile、sections 数量、page_number、page_type），不继续保存看似完整、实际只比较少量字段的大快照；更新只能通过显式脚本执行。新真实 fixture 使用独立目录 `kinematics_golden_v1/expected/`。"golden"一词以后只指真实衍生、人工批准、禁止自动更新的 Change 9 fixture。Change 9 是对现有测试的补充与升级管理，不是删除现有 parser/metrics/artifact/finding/report 单元测试。

### Decision 17: Kinematics-report 视频元数据 provenance

Change 9 SHALL 纠正视频元数据投影**仅**在 `side_2d_kinematics_5page_v1` 报告路径内。kinematics report 的 video context 应使用：`SessionVideo.fps` 作为权威 FPS；`SessionVideo.resolution` 作为权威分辨率；`VideoFile.id` 与 `original_filename` 仅用于文件身份（checksum 已在底层 source trace / 文件校验中使用，不必额外塞进展示 context）；无权威持久化时长时 `duration_sec = null`。报告构建器 MUST NOT 读取未声明的 `VideoFile.fps`、`VideoFile.width`、`VideoFile.height`、`VideoFile.duration_sec`（这些属性在模型中不存在，当前读取恒为 null）。其他 report profile 不在本 Change；仅在确认存在相同错误后另开 Change 审计处理。

**生产 Web 流程的 FPS 来源**：当前正式上传流程上传视频后用 `{ view_type:'side', sync_offset_ms:0 }` 绑定，前端无从获得 FPS，且 `SessionVideoCreate` 虽支持 `fps` 但上传响应未返回视频 FPS。因此 Change 9 采用**推荐方案**：后端在视频上传时 ffprobe 探测 FPS 与 resolution，`VideoUploadResponse` 返回 `probed_fps` / `resolution` 并标记 `metadata_source=ffprobe`、`verified=true`；前端绑定 SessionVideo 时透传该 FPS/resolution。这样 Change 9 不只证明测试客户端会传 FPS，也证明真实 Web 用户路径会传。若后端探测在特例下不可行，则回退为 fixture manifest 直传 FPS，但生产 guided workflow 的自动探测须另开 Change，不得保留"要求传 FPS 却无来源"的中间状态。

### Decision 18: 模块级 artifact quality notes

`page_builders` 各 `build_*_page` 接收 `artifact_quality_notes` 后应按本页 `source_module_keys` 过滤。缺失右腕导致的 upper-limb 资产降级说明 SHALL 只出现在 P3 upper_limb_kinematics；P2 body_posture_head_trunk 与 P4 lower_limb_kinematics MUST NOT 出现 upper-limb 专项降级说明；P5 review_and_retest 可汇总整体降级情况，但不作为主断言目标。

**上游 enrichment 是前置条件**：当前 `collect_skipped_artifact_quality_notes()` 生成的 note 仅含 `code/level/message`，没有可追溯的模块归属，页面构建器无法过滤。因此必须先在 `artifact_projection.py` 把 note 丰富为：

```python
{
    "code": skip_reason or f"artifact_{status}",
    "level": "warning",
    "message": msg,
    "artifact_key": getattr(art, "artifact_key", None),
    "module_key": getattr(art, "module_key", None),
    "metric_keys": list(getattr(art, "metric_keys", []) or []),
    "artifact_status": status,
}
```

随后页面过滤：

```python
page_notes = [n for n in artifact_quality_notes if n.get("module_key") in source_module_keys]
```

P5 可接收全部模块或专门聚合。tasks 14 必须先完成 enrichment，再实现页面过滤。

## Risks / Trade-offs

- **[基础设施型误报]** golden_e2e 依赖 PostgreSQL、Vue build、Chromium、Playwright、FFmpeg 与私有 fixture，任一缺失会导致红 CI 但与代码无关 → 采用分阶段接入：PR 硬门禁为 golden_contract，golden_e2e 先入 nightly/manual release check，连续约 20 次误报率足够低后升级为每 PR required；基础设施失败标记为独立 `E2E_INFRA_ERROR`，允许自动重试一次，重试仍失败继续阻断发布但清楚区分 product assertion failed 与 environment setup failed，不把 CI 噪声伪装成产品回归或软化成告警。
- **[PDF 渲染漂移]** 不同 OS/字体下 PDF 二进制不一致 → 只验证页数=5 与语义 marker，不比较字节 hash。
- **[内容溢出导致 6 页]** 若某一页内容溢出 A4 landscape，可能生成第 6 页 → PDF 页数严格断言 ==5，前端导出前布局预检直接失败并指出溢出页，而非静默截断。
- **[baseline 漂移]** 计算器变更可能静默改 key 集合 → 双层契约：运行时断言 summary key 集合 == calculator.CANONICAL_KEYS，版本化 golden 契约锁定 calculator_version 与 key-set hash；key-set 变更但未升 calculator version 必须失败。
- **[视频授权]** 真实视频可能不宜公开 → 允许 CI 从受控私有 artifact 下载并校验 SHA-256；fixture 缺失时测试直接失败，不回退合成数据。

## Migration Plan

本 Change 为测试与最小修复，无需数据迁移。部署步骤：1. 合入 fixture 与测试；2. 在 CI 注册 golden_contract（每 PR required）与 golden_e2e（nightly）；3. 观察约 20 次后升级 golden_e2e 为 required check；4. 若需回滚，仅停用对应 CI job 并保留 fixture，不影响生产运行时。

## Open Questions

- **[P0 BLOCKING] 视频 fixture 发布模型**：决定真实 MP4 是提交到仓库（或 Git LFS，极短、脱敏、经授权、尺寸可控）还是仅以受控私有 artifact 存在。这直接决定 CI 架构——若保持私有，则 `golden_contract` 不能依赖视频，须拆分为「每 PR：真实 XML + 固定 normalized fixture + 非视频依赖 golden contract」与「可信分支/nightly/release：私有视频 + 解码 + artifacts + HTML/PDF full E2E」两档。fork PR 无法获取 repository secrets、外部贡献者 PR 无法访问私有 artifact，下载凭证不能暴露给不可信 PR，artifact 服务短暂不可用也不应阻塞所有 PR。须在实现前敲定。
- **[P0 BLOCKING] 生产 Web 流程的 FPS 来源**：已确定采用后端 ffprobe 探测方案（见 Decision 17），但具体探测失败回退策略（fixture manifest 直传 vs 另开 Change）须在实现期定稿。
- golden_e2e 观察期的具体误报率阈值（约 20 次为建议值，可据实际调整）。
- `SessionVideo.resolution` 的存储格式（如 `3840x2176`）是否与报告展示期望一致，需在实现期确认。

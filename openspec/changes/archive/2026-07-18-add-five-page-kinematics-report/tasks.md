## 1. Baseline and contract audit

- [x] 1.1 Confirm current `build_swim_report_data()` behavior and tests
- [x] 1.2 Confirm the exact `swim-side-kinematics.v1` payload contract（`CANONICAL_KEYS` **23 个键**：body_posture 6 / upper_limb 6 / lower_limb 6 / head_trunk 5、四类 category）
- [x] 1.3 Confirm `KinematicArtifactSet.manifest` 与 artifact row contracts（含 `module_key` / `metadata.value`）
- [x] 1.4 Confirm `KinematicReviewFindingSet.findings` contract（`status = review_required`）
- [x] 1.5 Record the legacy and new module-key mismatch
- [x] 1.6 Add behavior-protection tests for the existing legacy report path
- [x] 1.7 Add dynamic assertion `len(CANONICAL_KEYS) == 23` to catch future schema changes

## 2. Define five-page report schemas

- [x] 2.1 Add `backend/app/schemas/kinematics_report.py`
- [x] 2.2 Define `ReportMetric`
- [x] 2.3 Define `ReportAsset`（保留 artifact_type / module_key / metric_keys / annotation_frame / source_video_frame / width / height / mime_type / checksum_sha256 / source_annotation_revision / generator_version / metadata）
- [x] 2.4 Define `ReportFinding`
- [x] 2.5 Define `ReportQualityNote`
- [x] 2.6 Define `FivePageReportSection`（含 `page_number` / `page_type` / `module_key` / `source_module_keys` / `assets` / `metrics` / `findings` / `quality_notes` / `content`）
- [x] 2.7 Define `FivePageReportContext`
- [x] 2.8 Define `FivePageKinematicsReport`（顶层 `assembly_status` 而非笼统 `status`；`status` 仅作兼容别名）
- [x] 2.9 Enforce exactly five sections
- [x] 2.10 Enforce page numbers `[1, 2, 3, 4, 5]`
- [x] 2.11 Enforce unique page types and module keys

## 3. Add input resolution

- [x] 3.1 Add `FivePageReportAssemblyContext`
- [x] 3.2 Resolve AnnotationMetric and NormalizedAnnotation
- [x] 3.3 Verify calculator and schema（`side_2d_kinematics` / `swim-side-kinematics.v1`）
- [x] 3.4 Reject source revision drift（409 metric_revision_stale）
- [x] 3.5 Resolve SessionVideo, VideoFile, TrainingSession and Athlete
- [x] 3.6 Reuse the existing ownership chain
- [x] 3.7 Extract reusable artifact expected-signature calculation from `generate()` without changing its formula
- [x] 3.8 Implement `resolve_current_artifact_set()` (internal, no auth) returning `ArtifactResolutionResult` with `resolution_status` ∈ {current_ready, current_partial, current_generating, current_failed, not_generated}
- [x] 3.9 Keep artifact and review-finding signature formulas separate
- [x] 3.10 Add a regression test proving that report assembly resolves each upstream product through its own signature
- [x] 3.11 Reuse `get_current_review_findings()` for the finding set
- [x] 3.12 Never select stale sets by `created_at`
- [x] 3.13 Convert missing optional inputs into structured warnings
- [x] 3.14 Define artifact resolver state mapping: ready→consume / partial→consume+partial / generating→artifacts_generating+partial / failed→no assets+artifacts_generation_failed+partial / not_generated→artifacts_not_generated+partial
- [x] 3.15 Do ownership validation once in the assembly service, then pass resolved metric/annotation to internal resolvers (no `current_user: None` optional bypass)

## 4. Add metric presentation registry and contract tests

- [x] 4.1 Define labels for all canonical kinematic metric keys in `KINEMATICS_REPORT_METRICS`
- [x] 4.2 Define display order per report page in `PAGE_METRIC_KEYS`
- [x] 4.3 Define decimal formatting
- [x] 4.4 Define complex value formatters for dict-valued metrics (`elbow_rom_deg`, `knee_rom_deg`, `ankle_vertical_range_px`, `kick_periodicity`, `left_right_kick_timing`)
- [x] 4.5 Add reference-basis display labels
- [x] 4.6 Project MetricEnvelope into ReportMetric
- [x] 4.7 Preserve confidence, availability, provenance and details
- [x] 4.8 Omit unavailable metrics from normal metric cards
- [x] 4.9 Add quality notes for unavailable and low-confidence metrics
- [x] 4.10 Do not perform scientific unit conversion in the report layer
- [x] 4.11 Add contract test `test_report_metric_registry_only_uses_canonical_keys`（`set(KINEMATICS_REPORT_METRICS) <= set(CANONICAL_KEYS)`）
- [x] 4.12 Add contract test `test_every_page_metric_key_is_registered`（`page_keys <= set(KINEMATICS_REPORT_METRICS)`）
- [x] 4.13 Audit `PAGE_METRIC_KEYS` against `CANONICAL_KEYS` to confirm no drift
- [x] 4.14 Keep overview stats outside the canonical metric registry (do not add effective_frame_count / joint_completeness to `KINEMATICS_REPORT_METRICS`)

## 5. Build the unified report metric index and overview stats

- [x] 5.1 Implement `build_report_metric_index()` producing immutable `all_report_metrics: dict[str, ReportMetric]` (only 23 canonical keys)
- [x] 5.2 Implement `select_report_metrics(index, keys)` for page builders
- [x] 5.3 Prohibit page builders from re-reading raw summary envelopes for display values
- [x] 5.4 Define `ReportOverviewStat` and `ReportOverviewStatSource` models
- [x] 5.5 Define the exact `effective_frame_count` formula (from annotation)
- [x] 5.6 Define the exact `joint_completeness_ratio` formula; reuse frame-resolver visibility semantics (do not reinvent in report layer)
- [x] 5.7 Build `overview_stats` from annotation + metric quality + `all_report_metrics` availability aggregation
- [x] 5.8 Page 1 consumes `overview_stats`; pages 2-5 consume `all_report_metrics`

## 6. Add artifact projection and page mapping

- [x] 6.1 Extend `project_to_report_assets()` with full trace fields
- [x] 6.2 Map artifact module keys to report pages via `PAGE_PLAN`
- [x] 6.3 Select the cross-side maximum elbow-flexion frame（从 left/right elbow_min 选 `metadata.value` 更小）
- [x] 6.4 Select the cross-side maximum elbow-extension frame（从 left/right elbow_max 选更大）
- [x] 6.5 Select the cross-side maximum knee-flexion frame
- [x] 6.6 Select the cross-side maximum knee-extension frame
- [x] 6.7 Preserve deterministic asset order
- [x] 6.8 Convert skipped artifacts into quality notes
- [x] 6.9 Deduplicate overview assets reused by page 2 and page 5
- [x] 6.10 Pass through `radar_semantics` from `KinematicArtifactSet.manifest`（不得硬编码 disclaimer）
- [x] 6.11 Record radar asset unavailable in quality notes when radar asset missing

## 7. Add review-finding projection

- [x] 7.1 Validate persisted finding payloads through Pydantic
- [x] 7.2 Preserve `status = review_required`
- [x] 7.3 Group findings by category（body_posture / head_trunk / upper_limb / lower_limb）
- [x] 7.4 Sort findings deterministically（priority, -priority_score, ATTENTION_RANK, -confidence, code）
- [x] 7.5 Add page-level finding limits without deleting full findings
- [x] 7.6 Build the cross-page evidence-frame index（去重 + 排序）
- [x] 7.7 Aggregate and deduplicate limitations
- [x] 7.8 Do not map findings into diagnostics
- [x] 7.9 Do not generate training prescriptions
- [x] 7.10 Ensure `next_capture_suggestions` contain only data-acquisition suggestions
- [x] 7.11 Implement `resolve_retest_source_metric_keys()` mapping `FindingEvidenceMetric` → canonical keys (handle `summary.*`, `ranges.*.<stat>`, `reference_body_length.*` paths)
- [x] 7.12 Never assume `finding.evidence_metrics[].key` is a canonical metric key
- [x] 7.13 Preserve `trigger_metric_key`, `derivation`, `statistic` in `RetestMetric`
- [x] 7.14 Define `RETEST_CORE_KEYS` minimal stable set (Change 6 fixed, not deferred to Change 7)
- [x] 7.15 Build `retest_metrics` from `all_report_metrics` with three-tier priority (finding evidence → low_confidence → RETEST_CORE_KEYS)

## 8. Implement page builders

- [x] 8.1 Implement page 1 `build_analysis_overview_page()`
- [x] 8.2 Include athlete and session information
- [x] 8.3 Include video and annotation information
- [x] 8.4 Include effective-frame and joint-completeness information
- [x] 8.5 Include analysis boundaries and module availability
- [x] 8.6 Implement page 2 `build_body_posture_control_page()`（source_module_keys = body_posture + head_trunk）
- [x] 8.7 Include body-posture and head-trunk metrics / assets / findings
- [x] 8.8 Implement page 3 `build_upper_limb_page()`
- [x] 8.9 Include selected flexion/extension keyframes and upper-limb findings
- [x] 8.10 Implement page 4 `build_lower_limb_page()`
- [x] 8.11 Include selected flexion/extension keyframes and lower-limb findings
- [x] 8.12 Implement page 5 `build_review_and_retest_page()`
- [x] 8.13 Build objective metric summary from the shared index
- [x] 8.14 Build priority review findings（排序后最多 8 条，首页摘要最多 3 条）
- [x] 8.15 Build evidence-frame index
- [x] 8.16 Build data-limitations list（聚合去重）
- [x] 8.17 Build data-acquisition suggestions（仅采集层）
- [x] 8.18 Build retest metric list（从 `all_report_metrics` 派生，固定三级优先级）
- [x] 8.19 Include range chart and stability radar（透传 radar semantics）

## 9. Implement top-level assembler

- [x] 9.1 Add `build_five_page_kinematics_report()`
- [x] 9.2 Always emit exactly five sections
- [x] 9.3 Derive section status（ready / partial / unavailable）
- [x] 9.4 Derive top-level `assembly_status`（ready / partial）
- [x] 9.5 Build deterministic summary
- [x] 9.6 Build complete source trace（保留上游原始 `artifact_set.status` / `finding_set.status` / `revision_status`）
- [x] 9.7 Compute report generation signature including `artifact_set.manifest_sha256`, stable `finding_payload_hash`, and `report_config_hash`
- [x] 9.8 Add assembler/profile version constants
- [x] 9.9 Ensure output is JSON safe
- [x] 9.10 Export the new builder through `report_builder.py`
- [x] 9.11 Keep legacy builder behavior unchanged
- [x] 9.12 Implement `PAGE_READINESS_POLICY` and derive each section `status` (unavailable / partial / ready) deterministically
- [x] 9.13 Derive top-level `assembly_status` from section statuses + resolver resolution statuses

## 10. Add assembly service and API

- [x] 10.1 Implement `assemble_five_page_kinematics_report()`
- [x] 10.2 Add ownership validation
- [x] 10.3 Add stale metric rejection（409）
- [x] 10.4 Add unsupported schema rejection（422）
- [x] 10.5 Add optional-input degradation（partial）
- [x] 10.6 Add `kinematics_reports.py` route（`POST /api/v1/annotation-metrics/{id}/reports/five-page/assemble`）
- [x] 10.7 Register route in API router
- [x] 10.8 Return typed `FivePageKinematicsReport`
- [x] 10.9 Do not persist `ReportMetadata`
- [x] 10.10 Document that Change 7 is the persistence/orchestration owner

## 11. Shared report fixtures (replaces old 10.24)

- [x] 11.1 Add `KinematicsReportFixture` dataclass
- [x] 11.2 Add `build_persisted_kinematics_report_fixture()` based on `build_golden_annotation()`
- [x] 11.3 Generate artifact and finding sets through real services（非手写 JSON）
- [x] 11.4 Add fixture variants: complete / missing artifacts / missing findings / empty ready findings / partial artifacts / stale metric / stale artifact only / stale finding only / low-confidence module / unavailable module
- [x] 11.5 Ensure fixture `session.coach_id` matches fixture `user.id` so `generate_review_findings()` ownership validation (`session.coach_id == current_user.id`) succeeds

## 12. Tests

- [x] 12.1 Test exact five-page order
- [x] 12.2 Test required section fields（含 `source_module_keys`）
- [x] 12.3 Test page 1 context projection
- [x] 12.4 Test four-category metric mapping
- [x] 12.5 Test low-confidence metric display
- [x] 12.6 Test unavailable metric handling
- [x] 12.7 Test upper-limb cross-side keyframe selection
- [x] 12.8 Test lower-limb cross-side keyframe selection
- [x] 12.9 Test skipped artifact quality notes
- [x] 12.10 Test review findings remain `review_required`
- [x] 12.11 Test finding category mapping
- [x] 12.12 Test deterministic priority ordering
- [x] 12.13 Test evidence-frame deduplication
- [x] 12.14 Test limitations aggregation
- [x] 12.15 Test next-capture suggestions contain no training prescription
- [x] 12.16 Test generated-empty findings are not treated as missing
- [x] 12.17 Test missing artifact set produces partial report
- [x] 12.18 Test missing finding set produces partial report
- [x] 12.19 Test stale metric returns 409
- [x] 12.20 Test stale artifact/finding sets are never used
- [x] 12.21 Test generation signature stability
- [x] 12.22 Test output changes when source metric hash changes
- [x] 12.23 Test legacy report-builder regression
- [x] 12.24 Add registry contract tests（4.11 / 4.12）
- [x] 12.25 Add signature-separation regression test（3.10）

## 13. Golden assembly verification

- [x] 13.1 Assemble a complete five-page report from the shared fixture
- [x] 13.2 Store only the expected report JSON as the golden snapshot
- [x] 13.3 Layer 1: assert real fields — `generation_signature` non-empty & len 64; `source_trace` IDs match fixture objects; section asset URLs point to corresponding artifacts
- [x] 13.4 Layer 2: normalize dynamic fields (`generated_at`, `generation_signature`, source IDs) and URL dynamic prefix (`/uploads/kinematic-artifacts/<METRIC_ID>/r<REV>/<SIG>/...`) before snapshot comparison; do NOT delete URLs wholesale

## 14. Status namespace and OpenSpec documentation

- [x] 14.1 Add a status namespace reference document（MetricEnvelope.availability / section.status / assembly_status / artifact_set.status / finding_set.status / revision_status）
- [x] 14.2 Add `five-page-kinematics-report` capability spec
- [x] 14.3 Amend `report-data-assembly` capability spec
- [x] 14.4 Document page and module-key registry
- [x] 14.5 Document metric presentation labels
- [x] 14.6 Document report status semantics
- [x] 14.7 Document input readiness and error codes
- [x] 14.8 Document handoff contract for Change 7

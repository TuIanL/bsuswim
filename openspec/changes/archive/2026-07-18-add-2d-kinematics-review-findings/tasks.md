# Tasks: add-2d-kinematics-review-findings

## 1. Define review finding contracts

- [x] 1.1 Add `FindingEvidenceMetric`
- [x] 1.2 Add `FindingEvidenceFrame`
- [x] 1.3 Add `KinematicReviewFinding`
- [x] 1.4 Add `ReviewFindingsSummary`
- [x] 1.5 Add `ReviewFindingsOutput`
- [x] 1.6 Add generate/read API schemas
- [x] 1.7 Fix schema version as `swim-2d-review-findings.v1`

## 2. Add persistence

- [x] 2.1 Add `KinematicReviewFindingSet` model
- [x] 2.2 Add source metric and source revision snapshot fields
- [x] 2.3 Add JSONB findings / summary / skipped_rules / warnings
- [x] 2.4 Add generation_signature
- [x] 2.5 Add unique constraint on annotation_metric_id + signature
- [x] 2.6 Export model from `app.models`
- [x] 2.7 Add Alembic migration

## 3. Implement side 2D review adapter

- [x] 3.1 Validate calculator and metric schema
- [x] 3.2 Unwrap scalar MetricEnvelope values
- [x] 3.3 Preserve availability, confidence and reference_basis
- [x] 3.4 Flatten elbow ROM details
- [x] 3.5 Flatten knee P05 values from ranges
- [x] 3.6 Flatten kick periodicity score and period
- [x] 3.7 Flatten head spike count and frames
- [x] 3.8 Derive hip/head normalized range ratios
- [x] 3.9 Derive elbow asymmetry degree and ratio
- [x] 3.10 Record unavailable and unsupported metrics
- [x] 3.11 Never use fixed pixel thresholds for review rules
- [x] 3.12 Adapter returns a `DiagnosticMetricsContext`-compatible flat context (R1)
- [x] 3.13 Add `ReviewAdapterResult` and `ReviewMetricMeta` (Decision 1b)
- [x] 3.14 Preserve per-derived-metric metadata separately from evaluation context (metric_meta)
- [x] 3.15 Define availability/confidence propagation for derived metrics (worst availability, min confidence)
- [x] 3.16 Derive `kick_periodicity_evaluable` / `kick_periodicity_peak_detected` (KRF006 区分无周期峰)

## 4. Extend rule registry safely

- [x] 4.1 Add `output_kind` to rule-set metadata
- [x] 4.2 Preserve old diagnostic rule validation
- [x] 4.3 Validate review rules require attention_level
- [x] 4.4 Validate evidence_metric_keys
- [x] 4.5 Validate evidence_frame_strategy uses explicit resolver enum (not metric_key/side DSL)
- [x] 4.6 Reject unsupported output_kind
- [x] 4.7 Include rule file checksum in rule version metadata
- [x] 4.8 Validate rule-set output_kind against the selected engine (R6)

## 5. Add `side_2d_kinematics_v1` rule pack

- [x] 5.1 KRF001 body-axis variation
- [x] 5.2 KRF002 hip vertical variation
- [x] 5.3 KRF003 elbow ROM outlier
- [x] 5.4 KRF004 left-right elbow ROM asymmetry
- [x] 5.5 KRF005 large knee flexion
- [x] 5.6 KRF006 weak ankle periodicity (condition distinguishes sample-insufficient vs no-peak-detected)
- [x] 5.7 KRF007 head motion spikes
- [x] 5.8 KRF008 head-trunk coupled movement
- [x] 5.9 Mark thresholds as `project_heuristic_v1`
- [x] 5.10 Add limitations and review_question to every rule

## 6. Implement evidence resolver

- [x] 6.1 Select max-deviation body-axis frames
- [x] 6.2 Resolve hip high/low frames from canonical skeleton
- [x] 6.3 Resolve elbow min/max frames
- [x] 6.4 Resolve knee minimum-angle frame
- [x] 6.5 Resolve ankle peak/trough frames
- [x] 6.6 Resolve explicit head spike frames
- [x] 6.7 Resolve synchronized head/trunk movement frame
- [x] 6.8 Preserve annotation frame when video mapping is unavailable
- [x] 6.9 Set extractable only for verified source-video frames
- [x] 6.10 Limit evidence frames per finding to three
- [x] 6.11 Define evidence source per KRF001–KRF008 (R3)
- [x] 6.12 Permit canonical-frame reconstruction for evidence selection only (R3)
- [x] 6.13 Implement eight explicit resolver functions (body_axis_max_deviation / hip_high_low / elbow_min_max_triggering_side / elbow_asymmetry_bounds / knee_minimum_triggering_side / ankle_peak_trough / head_spike_first_n / head_trunk_sync_max)

## 7. Implement review findings engine

- [x] 7.1 Reuse structured condition evaluator
- [x] 7.2 Check required metrics and availability
- [x] 7.2b Distinguish missing_metric / unavailable_metric / normal non-match (R2)
- [x] 7.3 Resolve attention level
- [x] 7.4 Build typed evidence_metrics from metric_meta (source_metric_keys + derivation)
- [x] 7.5 Attach evidence_frames
- [x] 7.6 Compute confidence from source metrics
- [x] 7.7 Append standard and rule-specific limitations
- [x] 7.8 Sort by priority_score = priority_base × attention_weight × confidence; stable tie-break (priority_score DESC, attention_level DESC, rule_id ASC)
- [x] 7.9 Build non-diagnostic summary
- [x] 7.10 Return skipped rules and warnings
- [x] 7.11 Ensure every output status is `review_required`
- [x] 7.12 Add low-confidence limitation and confidence factor (R2)
- [x] 7.13 Enforce status enum (generating/ready/failed); force regen flows ready→generating→ready; compute-then-overwrite to avoid destroying prior ready data
- [x] 7.14 Enforce title prefix "疑似"/"可能" and forbidden-assertive-phrase scan limited to title/conclusion/reason (R7)

## 8. Add generation service

- [x] 8.1 Resolve AnnotationMetric and NormalizedAnnotation
- [x] 8.2 Enforce ownership
- [x] 8.3 Reject unsupported calculator/schema
- [x] 8.4 Reject stale source revision
- [x] 8.5 Calculate source metric hash
- [x] 8.6 Calculate generation signature
- [x] 8.7 Return existing set for identical signature
- [x] 8.8 Support force regeneration
- [x] 8.9 Persist findings and metadata atomically
- [x] 8.10 Do not mutate AnnotationMetric or AnalysisResult
- [x] 8.11 Regenerate identical signatures in place when force=true (R4)
- [x] 8.12 Resolve current finding set by expected generation signature (R5)

## 9. Add API routes

- [x] 9.1 POST generate endpoint with `rule_set` query param (default side_2d_kinematics_v1)
- [x] 9.2 GET current expected-signature finding set endpoint (not "latest"); accepts `rule_set` param
- [x] 9.3 Add typed error responses (remove `no_reviewable_metrics`; add `rule_output_kind_mismatch`, `review_findings_not_generated`, `invalid_metric_payload`)
- [x] 9.4 Return empty successful result when no rules match (three legit-empty variants)
- [x] 9.5 Register router in API entrypoint
- [x] 9.6 GET returns finding set matching expected signature, not newest row (R5)

## 10. Tests

- [x] 10.1 Envelope unwrapping tests
- [x] 10.2 Normalized pixel ratio tests
- [x] 10.3 Nested elbow ROM flattening tests
- [x] 10.4 Knee P05 derivation tests
- [x] 10.5 Periodicity score flattening tests
- [x] 10.6 All eight rule hit tests
- [x] 10.7 Boundary-value tests for every rule
- [x] 10.8 Low-confidence metric tests
- [x] 10.9 Unavailable metric skip tests
- [x] 10.10 Evidence frame selection tests
- [x] 10.11 Unverified mapping evidence tests
- [x] 10.12 No-match returns empty findings tests
- [x] 10.13 Idempotent generation tests
- [x] 10.14 Stale revision rejection tests
- [x] 10.15 Unsupported legacy metric rejection tests
- [x] 10.16 Ownership isolation tests
- [x] 10.17 Verify existing `test_diagnostics.py` remains unchanged and passes
- [x] 10.18 Run golden fixture against current CVAT sample
- [x] 10.19 Test that trigger decisions never depend on evidence recomputation (R3)
- [x] 10.20 Add forbidden assertive-phrase lint for review rule content (R7)
- [x] 10.21 Verify diagnostic and review engines reject mismatched rule packs (R6)
- [x] 10.22 KRF006 generates finding when peak_detected=0 but evaluable=1 (no-peak ≠ sample-insufficient)
- [x] 10.23 KRF006 skipped as unavailable_metric when evaluable=0 (sample insufficient)
- [x] 10.24 Title prefix "疑似"/"可能" enforced on all eight findings (R7)
- [x] 10.25 Forbidden-assertive-phrase lint scans only title/conclusion/reason, not limitations (R7)
- [x] 10.26 Derived-metric availability/confidence propagation (worst availability, min confidence)
- [x] 10.27 Finding sort order matches priority_score formula and tie-breakers
- [x] 10.28 Force regen computes-then-overwrites; prior ready data preserved on failure
- [x] 10.29 GET with rule_set returns expected-signature set, not newest row

## 11. OpenSpec and documentation

- [x] 11.1 Add `2d-kinematics-review-findings` capability spec
- [x] 11.2 Amend `rule-based-diagnostics` for output_kind support
- [x] 11.3 Document all derived context keys
- [x] 11.4 Document threshold basis and non-normative status
- [x] 11.5 Document limitation taxonomy
- [x] 11.6 Document Change 6 report-consumption contract

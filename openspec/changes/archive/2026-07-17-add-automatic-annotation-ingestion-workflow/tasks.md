## 1. Schemas and contracts

- [x] 1.1 Add `AnnotationIngestResponse` schema
- [x] 1.2 Extend `AnnotationFileListItem` with: normalized_annotation_id, normalized_revision, quality_status, analysis_readiness, parse_warnings, parse_error
- [x] 1.3 Define `ANNOTATION_SELECTION_REQUIRED` error code
- [x] 1.4 Define `ANNOTATION_INPUT_UNAVAILABLE` error code
- [x] 1.5 Define structured ingestion error codes with domain prefix: ANNOTATION_INGEST_UPLOAD_FAILED, ANNOTATION_INGEST_PARSE_FAILED, ANNOTATION_INGEST_INVALID_PARSE_OPTIONS, ANNOTATION_INGEST_UNSUPPORTED_SOURCE
- [x] 1.6 Add `QualityStatus = Literal["valid", "warning", "invalid"]` type

## 2. Backend ingestion orchestration

- [x] 2.1 Add `annotation_ingestion_service.py` with `ingest_annotation()` orchestrator
- [x] 2.2 Reuse `create_annotation()` for file persistence
- [x] 2.3 Reuse `parse_annotation_file()` for parse + upsert
- [x] 2.4 Do not call route functions from service code
- [x] 2.5 Preserve annotation file when parse fails (status = parse_failed)
- [x] 2.6 Return annotation_file_id in parse failure error detail
- [x] 2.7 Preserve existing upload / parse / validate endpoints

## 3. Ingestion API

- [x] 3.1 Add `POST /sessions/{session_id}/videos/{video_id}/annotations/ingest`
- [x] 3.2 Accept multipart fields: file, source, annotation_fps, metadata, parse_options
- [x] 3.3 Reuse existing ownership checks (session to user, video to session)
- [x] 3.4 Return 201 on complete ingestion
- [x] 3.5 Return 201 even when quality.status = invalid
- [x] 3.6 Return structured 422 with annotation_file_id when parse fails after upload

## 4. Annotation list hydration

- [x] 4.1 Add repository query: AnnotationFile LEFT OUTER JOIN NormalizedAnnotation, single query, AnnotationFile as primary entity
- [x] 4.2 Populate normalized_annotation_id and revision
- [x] 4.3 Derive quality_status from normalized quality payload
- [x] 4.4 Derive analysis_readiness using shared readiness function
- [x] 4.5 Return parse_warnings from annotation_metadata.parse.warnings
- [x] 4.6 Return parse_error from annotation_file
- [x] 4.7 Delete frontend N+1 getAnnotationDetail calls per parsed file

## 5. Shared readiness derivation

- [x] 5.1 Move `derive_analysis_readiness()` to `app/services/annotation_quality/readiness.py`
- [x] 5.2 Reuse in parse endpoint
- [x] 5.3 Reuse in ingest endpoint
- [x] 5.4 Reuse in validate endpoint
- [x] 5.5 Reuse in annotation list hydration

## 6. Parse warnings persistence

- [x] 6.1 Compute warnings before composing metadata, assemble into build_metadata before upsert
- [x] 6.2 Write to `annotation_metadata.parse.warnings` and `annotation_metadata.parse.parsed_at`
- [x] 6.3 Overwrite on re-parse, do not append
- [x] 6.4 Do not overwrite on parse failure
- [x] 6.5 Merge with existing parse key in metadata, do not destroy sibling keys
- [x] 6.6 No database migration needed

## 7. Analysis submission ID contract

- [x] 7.1 Three-state judgment:
  - submittable candidates exist + no ID → 422 ANNOTATION_SELECTION_REQUIRED
  - only invalid/failed annotations exist → 422 ANNOTATION_INPUT_UNAVAILABLE
  - no annotations at all → video-only compatible
- [x] 7.2 Filter submittable candidates: status=parsed, quality=valid/warning, view_type=side
- [x] 7.3 Return candidate_normalized_annotation_ids in ANNOTATION_SELECTION_REQUIRED response
- [x] 7.4 Remove revision-based fallback auto-selection
- [x] 7.5 Map AnnotationSelectionRequiredError → 422 in route layer
- [x] 7.6 Map AnnotationInputUnavailableError → 422 in route layer

## 8. Frontend types

- [x] 8.1 Add `cvat` to `AnnotationSource`
- [x] 8.2 Add `AnnotationIngestResponse` interface
- [x] 8.3 Extend `AnnotationFileListItem` with: normalized_annotation_id, normalized_revision, analysis_readiness, parse_warnings, parse_error (quality_status already exists)
- [x] 8.4 Add `AnnotationWorkflowStage` type: idle, selected, ingesting, ready, warning, invalid, failed
- [x] 8.5 Add `ingestAnnotation()` to API service

## 9. Frontend workflow

- [x] 9.1 Replace upload button with "上传并处理标注" calling ingestAnnotation()
- [x] 9.2 Implement workflow stage transitions
- [x] 9.3 Show stage in UI: ingesting spinner, ready/warning/invalid/failed states
- [x] 9.4 Show parse summary after ingestion (frame count, trajectory count, warnings)
- [x] 9.5 Show quality status and affected modules for warning/invalid
- [x] 9.6 Show parse failure error and retry action
- [x] 9.7 Add CVAT source option in source selector
- [x] 9.8 Auto-suggest CVAT for .xml files without overriding user choice

## 10. Annotation selection UI

- [x] 10.1 Add selected annotation state per camera view
- [x] 10.2 Default-select latest submittable ordered by uploaded_at DESC, id DESC
- [x] 10.2a Source-local file version MUST NOT be used as cross-source ordering key
- [x] 10.3 Allow warning annotations with acknowledgement
- [x] 10.4 Disable invalid annotations
- [x] 10.5 Show file version and normalized revision separately

## 11. Analysis submission fix

- [x] 11.1 Remove `annotationId = parsed.id` (AnnotationFile.id as normalized_annotation_id)
- [x] 11.2 Read `selectedAnnotation.normalized_annotation_id` for submission
- [x] 11.3 Never fallback to AnnotationFile.id
- [x] 11.4 Warning acknowledgement dialog before submit
- [x] 11.5 Send acknowledge_quality_warnings only for selected annotation

## 12. Backend tests

- [x] 12.1 Successful CVAT ingestion via ingest endpoint
- [x] 12.2 Successful Kinovea ingestion via ingest endpoint
- [x] 12.3 Ingest returns 201 with quality valid
- [x] 12.4 Ingest returns 201 with quality warning
- [x] 12.5 Ingest returns 201 with quality invalid
- [x] 12.6 Parse failure after upload preserves file with parse_failed status
- [x] 12.7 Unauthorized ingestion returns 404
- [x] 12.8 Video not bound to session returns 404
- [x] 12.9 Invalid parse_options returns structured error
- [x] 12.10 List endpoint returns normalized_annotation_id
- [x] 12.11 List endpoint restores readiness after page refresh
- [x] 12.12 Analysis submission rejects missing ID when candidates exist
- [x] 12.13 Analysis submission allows video-only when no candidates
- [x] 12.14 Existing upload / parse / validate tests remain passing
- [x] 12.15 List endpoint keeps uploaded records without normalized annotation
- [x] 12.16 List endpoint keeps parse_failed records
- [x] 12.17 Invalid-only annotations do not silently fall back to video-only
- [x] 12.18 Candidate selection is limited to side-view annotations
- [x] 12.19 Latest default selection uses uploaded_at across different sources
- [x] 12.20 Re-parse keeps normalized_annotation_id stable and increments revision

## 13. Frontend tests

- [x] 13.1 Upload action calls ingestAnnotation()
- [x] 13.2 Successful ingest stores normalized_annotation_id
- [x] 13.3 Submit sends normalized_annotation_id, not annotation_file_id
- [x] 13.4 Warning annotation requires acknowledgement
- [x] 13.5 Invalid annotation blocks selection
- [x] 13.6 Latest valid annotation is default-selected
- [x] 13.7 Page reload restores ingest state from list response
- [x] 13.8 Parse failure shows retry guidance
- [x] 13.9 CVAT source is selectable

## 14. Verification

- [x] 14.1 Backend compile passes
- [x] 14.2 Backend tests pass
- [x] 14.3 Frontend type-check passes
- [x] 14.4 Frontend build passes
- [x] 14.5 E2E: video → CVAT XML → ingest → normalized_annotation_id → submit analysis

## ADDED Requirements

### Requirement: Golden contract tests SHALL cover the real backend analysis chain
The golden contract suite MUST use the fixture's real annotation and video inputs to exercise ingestion, normalized annotation persistence, metric calculation, artifact planning, findings, report assembly, and source revision traceability. Internal parser, calculator, renderer, and assembler components MUST NOT be replaced by mocks in this suite.

#### Scenario: Complete golden analysis succeeds
- **WHEN** the valid golden fixture is submitted through the backend analysis path
- **THEN** the task completes and metrics, artifacts, findings, and report data are produced with finite values and a consistent source annotation revision

#### Scenario: Invalid fixture mapping is supplied
- **WHEN** the fixture mapping does not match the observed annotation frames
- **THEN** the contract suite fails before accepting report output

### Requirement: Full-stack E2E SHALL exercise HTTP, browser print, and PDF export
The full-stack golden E2E MUST perform the user-visible upload/bind/ingest/analysis/report flow through HTTP and MUST use the real frontend print route and Playwright PDF renderer. It MUST verify that HTML and PDF derive from the same report generation signature.

#### Scenario: User-visible golden report is exported
- **WHEN** a test submits the valid fixture and opens the print route
- **THEN** the browser renders five ordered report pages, PDF export succeeds, and PDF page count is exactly five

#### Scenario: Print asset fails to decode
- **WHEN** a required report image cannot be decoded before printing
- **THEN** the print route exposes a print error and the PDF export fails instead of reporting ready

### Requirement: Missing keypoint data SHALL degrade the affected module
The golden E2E suite MUST apply the declared missing-joint mutation and verify that ingestion and the overall task remain successful while only dependent metrics or artifacts become unavailable or partial.

#### Scenario: Right wrist is missing in all active frames
- **WHEN** the missing-right-wrist mutation is analyzed
- **THEN** right-arm dependent outputs become unavailable or skipped, unrelated modules remain available where supported, and the report still contains five pages with a quality note

### Requirement: Produced metrics and representative frames SHALL be internally valid
The suite MUST reject NaN, positive or negative Infinity, invalid frame references, non-monotonic time series, and representative frames outside the verified annotation/source mapping.

#### Scenario: Metric payload contains a non-finite value
- **WHEN** a persisted metric payload contains NaN or Infinity
- **THEN** the golden contract fails with the metric key and frame context

#### Scenario: Representative frame is outside the mapping
- **WHEN** a report asset references an annotation or source frame not present in the fixture mapping
- **THEN** the contract fails before PDF comparison

### Requirement: Report provenance SHALL be preserved across outputs
The annotation revision, metric source revision, artifact source revision, finding source revision, and report trace MUST refer to the same normalized annotation revision. HTML semantic markers and PDF page markers MUST match the report section order.

#### Scenario: Revision trace is consistent
- **WHEN** the complete report is assembled
- **THEN** every persisted and rendered output points to the same source annotation revision

#### Scenario: Revision trace diverges
- **WHEN** any artifact, finding, or report section references a different annotation revision
- **THEN** the golden contract fails and identifies the divergent producer

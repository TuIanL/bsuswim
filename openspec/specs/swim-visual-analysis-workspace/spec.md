# swim-visual-analysis-workspace Specification

## Purpose
TBD - created by archiving change port-pickleball-platform-to-swim-analysis. Update Purpose after archive.
## Requirements
### Requirement: Video-first swim workspace
The system SHALL provide a swim visual-analysis workspace centered on side-view video review and analysis status.

#### Scenario: User opens demo visual analysis
- **WHEN** the user opens the swim visual workspace without a real job context
- **THEN** the system renders a demo swim analysis experience with a large video-style area, swim session context, and clear demo/source indication

#### Scenario: User opens job-specific visual analysis
- **WHEN** the user opens the visual workspace for a completed swim analysis job
- **THEN** the system renders job metadata, source clarity, available result actions, and the video or demo visual area for that job

### Requirement: Swim-specific visual overlays
The visual workspace SHALL use swim-analysis overlays rather than court or rally overlays.

#### Scenario: User views the demo overlay layer
- **WHEN** the swim demo workspace is visible
- **THEN** the visual area shows swim-specific cues such as lane direction, above-water and underwater capture labels, stitched side-view indicators, keypoint traces, body-angle markers, stroke-phase markers, rhythm ticks, and symmetry cues

#### Scenario: User reads overlay labels
- **WHEN** overlay labels are shown
- **THEN** labels explain swim posture, body line, stroke rhythm, breathing timing, kick consistency, or coach-review context instead of pickleball actions

### Requirement: Layer availability states
The workspace SHALL distinguish available, loading, unavailable, and demo visual layers.

#### Scenario: Keypoint layer is unavailable
- **WHEN** keypoint data is not available for a job
- **THEN** the workspace keeps the base video or demo visual usable and labels the keypoint layer as unavailable without showing unrelated placeholder detections as real output

#### Scenario: Demo overlays are shown
- **WHEN** the workspace renders sample visual layers
- **THEN** the system labels them as demo or simulated content

### Requirement: Workspace result actions
The visual workspace SHALL provide compact navigation to lower-level swim analysis results.

#### Scenario: User reviews completed visual analysis
- **WHEN** a completed swim analysis result is visible
- **THEN** the workspace exposes actions for report review, posture diagnosis, rhythm metrics, training suggestions, and task management

#### Scenario: User selects a result action
- **WHEN** the user selects a result or report action
- **THEN** the system navigates to the corresponding job-aware report or training view without losing the job context

### Requirement: Responsive video workspace
The workspace SHALL keep the primary visual analysis area usable on desktop and mobile.

#### Scenario: User views workspace on desktop
- **WHEN** the viewport is wide enough for a two-column layout
- **THEN** the video area remains dominant and the status or action rail appears adjacent to it

#### Scenario: User views workspace on mobile
- **WHEN** the viewport is narrow
- **THEN** the video area, layer controls, metadata, and result actions stack without overlapping text or controls


## ADDED Requirements

### Requirement: Swim video upload entry
The system SHALL provide a swim-specific video analysis entry point for uploading or demoing training-session footage.

#### Scenario: User opens the new swim analysis page
- **WHEN** the user opens the video analysis entry view
- **THEN** the system displays a swim training video workflow with file selection, session metadata, capture context, and a primary action to start analysis

#### Scenario: User enters swim metadata
- **WHEN** the user fills out the analysis form
- **THEN** the form captures swim-specific metadata such as session title, venue or pool, session date, swimmer label, stroke type, level, and capture mode

### Requirement: Upload form validation
The system SHALL guide users through valid video selection and required swim session context before creating an analysis job.

#### Scenario: User selects a supported video
- **WHEN** the user selects a local video file
- **THEN** the system shows the file name and file size and allows submission only when required metadata is complete

#### Scenario: User submits incomplete analysis input
- **WHEN** required metadata is missing or no video/demo source is selected
- **THEN** the system keeps the start-analysis action disabled or presents a clear validation message

### Requirement: Local demo job creation
The system SHALL support local demo analysis jobs so the workflow can be demonstrated without a backend service.

#### Scenario: User starts a demo analysis
- **WHEN** the user submits a valid demo analysis request
- **THEN** the system creates a completed or simulated swim analysis job, stores it locally, and routes the user to task management or the job status view

#### Scenario: User returns later in the same browser
- **WHEN** locally stored demo jobs exist
- **THEN** the task management view lists those jobs in reverse updated order

### Requirement: Analysis task management
The system SHALL provide a task management view for swim video analysis jobs.

#### Scenario: User opens task management
- **WHEN** the user opens the analysis task view
- **THEN** the system displays job cards or rows with status, progress, session metadata, updated time, and available next actions

#### Scenario: User opens a completed task
- **WHEN** the user selects a completed swim analysis job
- **THEN** the system routes to job-specific visual analysis, report, or details actions for that job

### Requirement: Swim analysis stage states
The system SHALL communicate swim-specific analysis progress and terminal states.

#### Scenario: User opens a processing job
- **WHEN** a swim analysis job is queued or processing
- **THEN** the system displays stage labels such as upload, synchronization, stitching, frame sampling, pose detection, stroke segmentation, metric extraction, visualization, and report generation

#### Scenario: User opens a failed or unavailable job
- **WHEN** a swim analysis job fails or cannot be loaded
- **THEN** the system shows a stable error state with a user-facing reason and actions to return to task management or start a new analysis

### Requirement: Backend-ready analysis client
The frontend SHALL isolate analysis job operations behind a typed client boundary.

#### Scenario: Implementation uses local demo data
- **WHEN** no backend service is configured
- **THEN** the client returns local demo jobs and reports without requiring network access

#### Scenario: Future backend integration is added
- **WHEN** backend endpoints become available
- **THEN** the client boundary can be extended to upload videos, create jobs, poll status, and fetch reports without rewriting platform view components

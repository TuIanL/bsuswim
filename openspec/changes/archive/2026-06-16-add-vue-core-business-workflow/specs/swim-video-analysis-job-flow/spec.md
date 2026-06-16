## MODIFIED Requirements

### Requirement: Swim video upload entry
The system SHALL provide a swim-specific multi-camera video upload entry point for an existing training session.

#### Scenario: User opens the new swim analysis page
- **WHEN** the user opens the video upload entry view for a training session
- **THEN** the system displays a swim training video workflow with current session context, multi-camera file selection, camera view metadata, synchronization offset fields, and actions to save draft or submit analysis

#### Scenario: User enters swim metadata
- **WHEN** the user prepares the training session before upload
- **THEN** the form captures swim-specific metadata such as athlete, session title, venue or pool, session date, stroke type, distance, pool length, scene, and notes

### Requirement: Upload form validation
The system SHALL guide users through valid video selection and required swim session context before submitting an analysis job.

#### Scenario: User selects a supported video
- **WHEN** the user selects a local video file for a camera view
- **THEN** the system shows the file name, file size, camera view, upload status, and allows the video to be bound to the current training session

#### Scenario: User submits incomplete analysis input
- **WHEN** required session context is missing or no session video has been successfully bound
- **THEN** the system keeps the submit-analysis action disabled or presents a clear validation message

### Requirement: Analysis task management
The system SHALL provide a task management view for swim training sessions and video analysis jobs.

#### Scenario: User opens task management
- **WHEN** the user opens the analysis task view
- **THEN** the system displays session or job rows with status, progress, athlete or session metadata, updated time, and available next actions

#### Scenario: User opens a completed task
- **WHEN** the user selects a completed swim analysis job
- **THEN** the system routes to job-specific visual analysis, report, or details actions for that job

#### Scenario: User opens a session awaiting upload
- **WHEN** the user selects a training session that has not finished video upload
- **THEN** the system routes to the session-specific multi-camera upload page

### Requirement: Backend-ready analysis client
The frontend SHALL isolate auth, athlete, training session, video upload, session-video binding, analysis job, workspace, and report operations behind typed client boundaries.

#### Scenario: Implementation uses local demo data
- **WHEN** no backend service is configured
- **THEN** the client returns local demo users, athletes, sessions, videos, jobs, workspaces, and reports without requiring network access

#### Scenario: Future backend integration is added
- **WHEN** backend endpoints become available
- **THEN** the client boundary can be extended to upload videos, create sessions, bind session videos, create jobs, poll status, and fetch reports without rewriting platform view components

### Requirement: Training session preparation flow
系统 SHALL 在真实后端分析前建立用户会话、运动员档案、训练记录和视频绑定关系。

#### Scenario: User prepares backend analysis
- **WHEN** 用户准备提交真实游泳视频分析
- **THEN** 系统 MUST 能够通过后端 API 完成注册或登录、恢复当前用户、创建或选择运动员、创建训练记录、上传一个或多个视频并绑定训练记录视频

#### Scenario: Session has no bound video
- **WHEN** 用户尝试提交没有绑定视频的训练记录进行分析
- **THEN** 系统 MUST 拒绝创建分析任务并返回可读错误原因

#### Scenario: Session has multiple camera videos
- **WHEN** 用户为同一训练记录上传多个机位视频
- **THEN** 系统 MUST 为每个视频保存机位类型和 `sync_offset_ms`，并在上传页展示各机位状态

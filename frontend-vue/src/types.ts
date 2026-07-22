export type TaskStatus = 'uploaded' | 'queued' | 'processing' | 'result_saving' | 'completed' | 'failed'

export type UserRole = 'admin' | 'coach' | 'athlete'

export type StrokeType = 'freestyle' | 'breaststroke' | 'backstroke' | 'butterfly' | 'mixed'

export type TrainingSessionStatus = 'draft' | 'video_uploaded' | 'analyzing' | 'completed' | 'failed'

export type SessionVideoView = 'side' | 'front' | 'top' | 'underwater' | 'semi_underwater'

export type BackendSessionVideoView = 'side' | 'front' | 'top' | 'underwater' | 'other'

export type UploadStatus = 'pending' | 'uploading' | 'success' | 'failed'

export interface User {
  id: number
  username: string
  email?: string | null
  phone?: string | null
  full_name?: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthToken {
  access_token: string
  token_type: string
}

export interface LoginForm {
  username: string
  password: string
  remember?: boolean
}

export interface RegisterForm {
  username: string
  password: string
  full_name?: string
  phone?: string
  email?: string
  role: UserRole
}

export interface Athlete {
  id: number
  name: string
  gender?: 'male' | 'female' | string | null
  birth_date?: string | null
  height_cm?: number | null
  weight_kg?: number | null
  stroke_specialty?: StrokeType | string | null
  level?: string | null
  coach_id?: number | null
  team_id?: number | null
  team_name?: string | null
  notes?: string | null
  current_score?: number | null
  recent_test_at?: string | null
  created_at: string
  updated_at: string
}

export interface AthleteCreateInput {
  name: string
  gender?: string
  birth_date?: string
  height_cm?: number
  weight_kg?: number
  stroke_specialty?: StrokeType | string
  level?: string
  team_id?: number
  notes?: string
}

export interface TrainingSession {
  id: number
  athlete_id: number
  coach_id?: number | null
  title: string
  session_date?: string | null
  venue?: string | null
  stroke_type: StrokeType
  distance_m?: number | null
  pool_length_m?: number | null
  scene?: 'training' | 'competition' | 'course' | 'rehab' | string
  status: TrainingSessionStatus
  notes?: string | null
  score?: number | null
  created_at: string
  updated_at: string
}

export interface CreateSessionForm {
  athlete_id: number | null
  title: string
  session_date?: string
  venue?: string
  stroke_type: StrokeType
  distance_m?: 25 | 50 | 100 | 200 | number
  pool_length_m?: 25 | 50 | number
  scene?: 'training' | 'competition' | 'course' | 'rehab'
  notes?: string
}

export interface SessionVideoCreateInput {
  video_file_id: number
  view_type: BackendSessionVideoView
  fps?: number | null
  resolution?: string | null
  sync_offset_ms: number
}

export interface VideoUploadResponse {
  video: VideoFile
  probed_fps?: number | null
  resolution?: string | null
  metadata_source?: string | null
  fps_verified?: boolean
}

export interface SessionVideo {
  id: number
  session_id: number
  video_file_id: number
  view_type: BackendSessionVideoView | SessionVideoView
  fps?: number | null
  resolution?: string | null
  sync_offset_ms: number
  created_at: string
  video: VideoFile
  upload_status?: UploadStatus
}

export interface AthleteTrendPoint {
  date: string
  score: number
  body_line: number
  stroke_rate: number
  stroke_length: number
  swolf: number
}

export interface TrainingMetadata {
  session_title: string
  venue?: string
  session_date?: string
  swimmer_label?: string
  stroke_type: StrokeType | string
  level?: string
  capture_mode: string
}

export interface VideoFile {
  id: number
  original_filename: string
  stored_filename: string
  storage_path: string
  mime_type?: string
  size_bytes: number
  checksum_sha256: string
  created_at: string
  playback_url: string
}

export interface AnalysisTask {
  id: number
  session_id: number
  status: TaskStatus
  progress: number
  stage: string
  request_payload?: Record<string, any>
  error_message?: string | null
  pipeline_type: string
  pipeline_version: string
  attempt_count: number
  failed_stage?: string | null
  error_code?: string | null
  created_at: string
  updated_at: string
  completed_at?: string | null
  pipeline_progress?: PipelineProgress
  actions: string[]
  video_id?: number
  session_metadata?: TrainingMetadata
  video?: VideoFile
}

export interface PipelineStep {
  key: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  details?: Record<string, any>
  error_code?: string | null
  error_message?: string | null
}

export interface PipelineProgress {
  pipeline_type: string
  pipeline_version: string
  attempt_count: number
  current_stage: string
  failed_stage?: string | null
  error_code?: string | null
  warnings: string[]
  steps: PipelineStep[]
}

export interface AnalysisStatus {
  task_id: number
  session_id: number
  status: TaskStatus
  progress: number
  stage: string
  error_message?: string | null
  pipeline_type: string
  pipeline_version: string
  attempt_count: number
  failed_stage?: string | null
  error_code?: string | null
  pipeline_progress?: PipelineProgress
  actions: string[]
  created_at: string
  updated_at: string
  completed_at?: string | null
}

export interface AnalysisResult {
  id: number
  task_id: number
  schema_version: string
  detections: Array<Record<string, any>>
  keypoint_frames: Array<Record<string, any>>
  phases: Array<Record<string, any>>
  metrics: Record<string, any>
  diagnostics: Array<Record<string, any>>
  created_at: string
}

export interface WorkspaceData {
  task: AnalysisTask
  result?: AnalysisResult | null
  videos?: VideoFile[]
  session_videos?: SessionVideo[]
}

export interface ReportData {
  session_id: number
  task_id: number
  source: string
  generated_at: string
  report: Record<string, any>
}

// ---- annotation file types ----

export type AnnotationSource = 'kinovea' | 'dartfish' | 'manual_json' | 'ai_pose' | 'cvat' | 'unknown'

export type AnnotationFileStatus = 'uploaded' | 'parsed' | 'parse_failed' | 'archived'

export type AnnotationWorkflowStage =
  | 'idle'
  | 'selected'
  | 'ingesting'
  | 'ready'
  | 'warning'
  | 'invalid'
  | 'failed'

export interface AnalysisReadiness {
  can_submit: boolean
  requires_acknowledgement: boolean
  blocking_issue_count: number
  affected_modules: string[]
}

export interface ParseSummary {
  events_count: number
  keypoint_frames_count: number
  trajectories_count: number
  manual_tags_count: number
}

export interface AnnotationIngestResponse {
  annotation_file_id: number
  session_video_id: number
  session_id: number
  video_file_id: number
  source: AnnotationSource
  file_status: AnnotationFileStatus
  file_version: number
  original_filename: string
  normalized_annotation_id: number
  normalized_revision: number
  schema_version: string
  parse_summary: ParseSummary
  quality: Record<string, any>
  analysis_readiness: AnalysisReadiness
  warnings: string[]
}

export interface QualityIssue {
  code: string
  category?: string
  severity?: string
  blocking?: boolean
  status?: string
  message?: string
  user_message?: string
  suggested_action?: {
    label?: string
    kind?: string
  } | null
}

export interface ModuleReadiness {
  status: 'ready' | 'degraded' | 'blocked'
  blocking_issues?: string[]
  warnings?: string[]
}

export interface AnnotationQualityReport {
  schema_version?: string
  status: QualityStatus
  score?: number
  source_revision?: number
  summary?: {
    blocking_count?: number
    error_count?: number
    warning_count?: number
    info_count?: number
  }
  issues?: QualityIssue[]
  module_readiness?: Record<string, ModuleReadiness>
}

export type ModuleReadinessStatus = 'ready' | 'degraded' | 'blocked'

export type KinematicsModuleKey = 'body_posture' | 'upper_limb' | 'lower_limb' | 'head_trunk'

export type KinematicsModuleReadiness = Record<KinematicsModuleKey, ModuleReadinessStatus>

export type ReportFreshness = 'none' | 'current' | 'stale'

export type WorkflowPhase =
  | 'video_required'
  | 'annotation_required'
  | 'annotation_processing'
  | 'annotation_review'
  | 'ready_to_analyze'
  | 'analysis_running'
  | 'analysis_failed'
  | 'report_ready'

export interface AnnotationFileListItem {
  id: number
  session_video_id: number
  source: AnnotationSource
  view_type: BackendSessionVideoView | null
  file_type: string | null
  version: number
  status: AnnotationFileStatus
  original_filename: string
  annotation_fps: number | null
  uploaded_at: string | null
  quality_status?: QualityStatus
  normalized_annotation_id?: number | null
  normalized_revision?: number | null
  analysis_readiness?: AnalysisReadiness | null
  parse_summary?: ParseSummary | null
  quality?: AnnotationQualityReport | null
  kinematics_module_readiness?: Partial<KinematicsModuleReadiness>
  parse_warnings?: string[]
  parse_error?: string | null
}

export interface AnnotationFileDetail {
  id: number
  session_video_id: number
  session_id: number | null
  video_file_id: number | null
  view_type: BackendSessionVideoView | null
  source: AnnotationSource
  original_filename: string
  stored_filename: string
  storage_path: string
  file_type: string | null
  file_size_bytes: number | null
  checksum_sha256: string | null
  annotation_fps: number | null
  frame_count: number | null
  duration_sec: number | null
  version: number
  status: AnnotationFileStatus
  parse_error: string | null
  metadata: Record<string, any>
  uploaded_by: number | null
  uploaded_at: string | null
  created_at: string
  updated_at: string
}

export type QualityStatus = 'valid' | 'warning' | 'invalid'

export interface AnalysisReadiness {
  can_submit: boolean
  requires_acknowledgement: boolean
  blocking_issue_count: number
  affected_modules: string[]
}

export interface AnnotationUploadResponse {
  annotation_file_id: number
  session_video_id: number
  session_id: number
  video_file_id: number
  view_type: string
  source: AnnotationSource
  version: number
  status: AnnotationFileStatus
  original_filename: string
  uploaded_at: string | null
}

// Kinematics Metrics Types
export interface MetricValue {
  name: string
  value: number | null
  unit: string
  availability: 'available' | 'unavailable' | 'partial'
  confidence?: number
}

export interface AnnotationMetricRead {
  id: number
  normalized_annotation_id: number
  calculator: string
  calculator_version: string
  schema_version: string
  metrics: Record<string, MetricValue>
  created_at: string
  updated_at: string
}

export interface CalculateMetricsResponse {
  annotation_metric_id: number
  persisted: boolean
  metrics: Record<string, MetricValue>
}

// Kinematic Artifacts Types
export interface KinematicArtifact {
  artifact_key: string
  module_key: string
  metric_keys: string[]
  status: 'ready' | 'skipped' | 'failed'
  skip_reason?: string
  status_detail?: string
  asset_url?: string
  asset_type?: string
}

export interface KinematicArtifactSetRead {
  id: number
  annotation_metric_id: number
  artifacts: KinematicArtifact[]
  created_at: string
  updated_at: string
}

export interface GenerateResponse {
  artifact_set_id: number
  status: 'generating' | 'ready' | 'failed'
}

// Review Findings Types
export interface ReviewFinding {
  finding_key: string
  severity: 'warning' | 'info' | 'suggestion'
  title: string
  description: string
  metric_keys: string[]
  recommendation?: string
}

export interface ReviewFindingsReadResponse {
  id: number
  annotation_metric_id: number
  rule_set: string
  findings: ReviewFinding[]
  created_at: string
  updated_at: string
}

export interface ReviewFindingsGenerateResponse {
  finding_set_id: number
  status: 'generating' | 'ready' | 'failed'
}

// Five-Page Report Types
export interface FivePageReportSection {
  page_number: number
  page_type: string
  module_key: string
  source_module_keys: string[]
  title: string
  subtitle?: string
  status: 'ready' | 'unavailable'
  metrics: MetricValue[]
  findings: ReviewFinding[]
  assets: KinematicArtifact[]
  quality_notes: Array<{
    code: string
    level: string
    message: string
  }>
}

export interface FivePageKinematicsReport {
  schema_version: string
  report_profile: string
  generation_signature: string
  sections: FivePageReportSection[]
  summary?: {
    title: string
    overall_score?: number
    overall_level?: string
  }
}

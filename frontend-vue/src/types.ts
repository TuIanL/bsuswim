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
  video_id: number
  status: TaskStatus
  progress: number
  stage: string
  session_metadata: TrainingMetadata
  error_message?: string
  created_at: string
  updated_at: string
  completed_at?: string
  video?: VideoFile
  actions: string[]
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
  result?: AnalysisResult
}

export interface ReportData {
  task_id: number
  source: string
  generated_at: string
  report: Record<string, any>
}

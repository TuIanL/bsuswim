export type TaskStatus = 'uploaded' | 'queued' | 'processing' | 'result_saving' | 'completed' | 'failed'

export interface TrainingMetadata {
  session_title: string
  venue?: string
  session_date?: string
  swimmer_label?: string
  stroke_type: string
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

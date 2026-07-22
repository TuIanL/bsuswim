import axios from 'axios'
import type {
  AnalysisReadiness,
  AnalysisTask,
  AnalysisStatus,
  Athlete,
  AthleteCreateInput,
  AthleteTrendPoint,
  AuthToken,
  CreateSessionForm,
  LoginForm,
  RegisterForm,
  ReportData,
  SessionVideo,
  SessionVideoCreateInput,
  TrainingSession,
  User,
  VideoFile,
  VideoUploadResponse,
  WorkspaceData,
  AnnotationIngestResponse,
  AnnotationMetricRead,
  CalculateMetricsResponse,
  KinematicArtifactSetRead,
  GenerateResponse,
  ReviewFindingsReadResponse,
  ReviewFindingsGenerateResponse,
  FivePageKinematicsReport
} from '../types'
import {
  bindDemoSessionVideo,
  createDemoAthlete,
  createDemoSession,
  createDemoVideo,
  demoUser,
  getDemoAthlete,
  getDemoAthleteSessions,
  getDemoAthleteTrend,
  getDemoAthletes,
  getDemoSession,
  getDemoSessions,
  getDemoSessionVideos,
  getDemoTask,
  getDemoTasks,
  getDemoWorkspace,
  getDemoReport,
  submitDemoAnalysis
} from './demoData'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
export const demoMode = !apiBaseUrl

const client = axios.create({
  baseURL: `${apiBaseUrl}/api/v1`
})

let authToken = ''

export function setAuthToken(token?: string | null) {
  authToken = token || ''
}

client.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`
  }
  return config
})

export async function login(input: LoginForm): Promise<AuthToken> {
  if (demoMode) {
    return { access_token: 'demo-access-token', token_type: 'bearer' }
  }

  const form = new URLSearchParams()
  form.set('username', input.username)
  form.set('password', input.password)
  const response = await client.post<AuthToken>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
  return response.data
}

export async function register(input: RegisterForm): Promise<User> {
  if (demoMode) {
    return {
      ...demoUser,
      username: input.username,
      full_name: input.full_name || input.username,
      email: input.email || null,
      phone: input.phone || null,
      role: input.role
    }
  }

  const response = await client.post<User>('/auth/register', input)
  return response.data
}

export async function getCurrentUser(): Promise<User> {
  if (demoMode) return demoUser
  const response = await client.get<User>('/users/me')
  return response.data
}

export async function listAthletes(): Promise<Athlete[]> {
  if (demoMode) return getDemoAthletes()
  const response = await client.get<Athlete[]>('/athletes')
  return response.data
}

export async function createAthlete(input: AthleteCreateInput): Promise<Athlete> {
  if (demoMode) return createDemoAthlete(input)
  const response = await client.post<Athlete>('/athletes', input)
  return response.data
}

export async function getAthlete(athleteId: number): Promise<Athlete | null> {
  if (demoMode) return getDemoAthlete(athleteId)
  const response = await client.get<Athlete>(`/athletes/${athleteId}`)
  return response.data
}

export async function listAthleteSessions(athleteId: number): Promise<TrainingSession[]> {
  if (demoMode) return getDemoAthleteSessions(athleteId)
  const response = await client.get<TrainingSession[]>(`/athletes/${athleteId}/sessions`)
  return response.data
}

export async function getAthleteTrend(athleteId: number): Promise<AthleteTrendPoint[]> {
  if (demoMode) return getDemoAthleteTrend(athleteId)
  try {
    const sessions = await listAthleteSessions(athleteId)
    return sessions
      .filter(s => s.status === 'completed')
      .sort((a, b) => new Date(a.session_date || a.created_at).getTime() - new Date(b.session_date || b.created_at).getTime())
      .map(s => ({
        date: (s.session_date || s.created_at || '').slice(0, 10),
        score: (s as any).technical_score ?? 0,
        body_line: (s as any).body_line_score ?? 0,
        stroke_rate: (s as any).stroke_rate ?? 0,
        stroke_length: (s as any).stroke_length ?? 0,
        swolf: (s as any).swolf ?? 0
      }))
  } catch {
    return []
  }
}

export async function createSession(input: CreateSessionForm): Promise<TrainingSession> {
  if (!input.athlete_id) {
    throw new Error('请选择运动员')
  }
  const payload = {
    athlete_id: input.athlete_id,
    title: input.title,
    session_date: input.session_date || undefined,
    venue: input.venue || undefined,
    stroke_type: input.stroke_type,
    distance_m: input.distance_m || undefined,
    pool_length_m: input.pool_length_m || undefined,
    notes: input.notes || undefined
  }
  if (demoMode) return createDemoSession({ ...payload, scene: input.scene })
  const response = await client.post<TrainingSession>('/sessions', payload)
  return response.data
}

export async function listSessions(): Promise<TrainingSession[]> {
  if (demoMode) return getDemoSessions()
  const response = await client.get<TrainingSession[]>('/sessions')
  return response.data
}

export async function getSession(sessionId: number): Promise<TrainingSession | null> {
  if (demoMode) return getDemoSession(sessionId)
  const response = await client.get<TrainingSession>(`/sessions/${sessionId}`)
  return response.data
}

export async function uploadVideo(file: File): Promise<VideoUploadResponse> {
  if (demoMode) {
    const video = createDemoVideo(file)
    return { video, probed_fps: null, resolution: null, metadata_source: null, fps_verified: false }
  }

  const form = new FormData()
  form.append('file', file)
  const response = await client.post<VideoUploadResponse>('/videos/upload', form)
  return response.data
}

export async function bindSessionVideo(sessionId: number, input: SessionVideoCreateInput): Promise<SessionVideo> {
  if (demoMode) {
    const video: VideoFile = {
      id: input.video_file_id,
      original_filename: `demo-${input.video_file_id}.mp4`,
      stored_filename: `demo-${input.video_file_id}.mp4`,
      storage_path: `demo-${input.video_file_id}.mp4`,
      mime_type: 'video/mp4',
      size_bytes: 0,
      checksum_sha256: 'demo',
      created_at: new Date().toISOString(),
      playback_url: ''
    }
    return bindDemoSessionVideo(sessionId, video, input)
  }
  const response = await client.post<SessionVideo>(`/sessions/${sessionId}/videos`, input)
  return response.data
}

export async function bindUploadedSessionVideo(
  sessionId: number,
  video: VideoUploadResponse,
  input: Omit<SessionVideoCreateInput, 'video_file_id'>
): Promise<SessionVideo> {
  const fps = input.fps ?? video.probed_fps ?? null
  const resolution = input.resolution ?? video.resolution ?? null
  if (demoMode) return bindDemoSessionVideo(sessionId, video.video, { ...input, view_type: input.view_type, fps, resolution })
  return bindSessionVideo(sessionId, { ...input, video_file_id: video.video.id, fps, resolution })
}

export async function listSessionVideos(sessionId: number): Promise<SessionVideo[]> {
  if (demoMode) return getDemoSessionVideos(sessionId)
  const response = await client.get<SessionVideo[]>(`/sessions/${sessionId}/videos`)
  return response.data
}

export async function submitAnalysis(
  sessionId: number,
  options?: {
    normalized_annotation_id?: number
    acknowledge_quality_warnings?: boolean
    pipeline_type?: string
    pipeline_version?: string
  }
): Promise<AnalysisTask> {
  if (demoMode) return submitDemoAnalysis(sessionId)
  const response = await client.post<AnalysisTask>('/analysis/submit', {
    session_id: sessionId,
    normalized_annotation_id: options?.normalized_annotation_id,
    acknowledge_quality_warnings: options?.acknowledge_quality_warnings ?? false,
    pipeline_type: options?.pipeline_type,
    pipeline_version: options?.pipeline_version
  })
  return response.data
}

export async function retryAnalysisTask(taskId: number): Promise<AnalysisTask> {
  if (demoMode) return submitDemoAnalysis(taskId)
  const response = await client.post<AnalysisTask>(`/analysis/${taskId}/retry`)
  return response.data
}

export async function listTasks(params?: {
  session_id?: number
  pipeline_type?: string
  limit?: number
}): Promise<AnalysisTask[]> {
  if (demoMode) return getDemoTasks()
  const query: Record<string, any> = {}
  if (params?.session_id != null) query.session_id = params.session_id
  if (params?.pipeline_type != null) query.pipeline_type = params.pipeline_type
  if (params?.limit != null) query.limit = params.limit
  const response = await client.get<AnalysisTask[]>('/analysis', { params: query })
  return response.data
}

export async function getTask(taskId: number): Promise<AnalysisTask> {
  if (demoMode) return getDemoTask(taskId)
  const response = await client.get<AnalysisTask>(`/analysis/${taskId}`)
  return response.data
}

export async function getAnalysisStatus(taskId: number): Promise<AnalysisStatus> {
  if (demoMode) {
    const task = getDemoTask(taskId)
    return {
      task_id: task.id,
      session_id: task.session_id,
      status: task.status,
      progress: task.progress,
      stage: task.stage,
      error_message: task.error_message,
      pipeline_type: task.pipeline_type,
      pipeline_version: task.pipeline_version,
      attempt_count: task.attempt_count,
      failed_stage: task.failed_stage,
      error_code: task.error_code,
      pipeline_progress: task.pipeline_progress ?? undefined,
      actions: task.actions,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at
    }
  }
  const response = await client.get<AnalysisStatus>(`/analysis/${taskId}/status`)
  return response.data
}

export async function getAnalysisResult(taskId: number) {
  if (demoMode) return getDemoWorkspace(taskId).result || null
  const response = await client.get(`/analysis/${taskId}/result`)
  return response.data
}

export async function getAnalysisWorkspace(taskId: number): Promise<WorkspaceData> {
  if (demoMode) return getDemoWorkspace(taskId)
  const response = await client.get<WorkspaceData>(`/analysis/${taskId}/workspace`)
  return response.data
}

export async function getWorkspace(taskId: number): Promise<WorkspaceData> {
  return getAnalysisWorkspace(taskId)
}

export async function generateReport(sessionId: number): Promise<ReportData> {
  if (demoMode) return getDemoReport(sessionId)
  const response = await client.post<ReportData>('/reports/generate', { session_id: sessionId })
  return response.data
}

export async function getReport(
  sessionId: number,
  options?: { demoFormat?: 'legacy' | 'swim_v1' }
): Promise<ReportData> {
  if (demoMode) {
    const format = options?.demoFormat === 'swim_v1' ? 'swim_v1' : 'legacy'
    return getDemoReport(sessionId, format)
  }
  const response = await client.get<ReportData>(`/reports/${sessionId}`)
  return response.data
}

// ---- PDF export APIs ----

export async function exportReportPdf(
  sessionId: number,
  force: boolean = false
): Promise<{ pdf_status: string; pdf_url?: string; pdf_exported_at?: string }> {
  if (demoMode) {
    return { pdf_status: 'exported', pdf_url: '#demo-pdf', pdf_exported_at: new Date().toISOString() }
  }
  const response = await client.post(`/sessions/${sessionId}/report/export/pdf`, { force })
  return response.data
}

export async function getReportPdfUrl(sessionId: number): Promise<string> {
  if (demoMode) return '#demo-pdf'
  return `/api/v1/sessions/${sessionId}/report/pdf`
}

export async function getReportPdfStatus(
  sessionId: number
): Promise<{ pdf_status: string; pdf_exported_at?: string; pdf_error?: string }> {
  if (demoMode) {
    return { pdf_status: 'not_exported' }
  }
  const response = await client.get(`/sessions/${sessionId}/report/export/pdf/status`)
  return response.data
}

// ---- annotation file APIs ----

import type {
  AnnotationFileDetail,
  AnnotationFileListItem,
  AnnotationUploadResponse
} from '../types'

export async function uploadAnnotation(
  sessionId: number,
  videoId: number,
  file: File,
  source: string = 'kinovea',
  annotationFps?: number | null,
  metadata?: Record<string, any> | null
): Promise<AnnotationUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('source', source)
  if (annotationFps != null) form.append('annotation_fps', String(annotationFps))
  if (metadata) form.append('metadata', JSON.stringify(metadata))
  const response = await client.post<AnnotationUploadResponse>(
    `/sessions/${sessionId}/videos/${videoId}/annotations`,
    form
  )
  return response.data
}

export async function ingestAnnotation(
  sessionId: number,
  videoId: number,
  file: File,
  source: string = 'kinovea',
  annotationFps?: number | null,
  metadata?: Record<string, any> | null,
  parseOptions?: Record<string, any> | null
): Promise<AnnotationIngestResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('source', source)
  if (annotationFps != null) form.append('annotation_fps', String(annotationFps))
  if (metadata) form.append('metadata', JSON.stringify(metadata))
  if (parseOptions) form.append('parse_options', JSON.stringify(parseOptions))
  const response = await client.post<AnnotationIngestResponse>(
    `/sessions/${sessionId}/videos/${videoId}/annotations/ingest`,
    form
  )
  return response.data
}

export async function listAnnotations(
  sessionId: number,
  videoId: number
): Promise<AnnotationFileListItem[]> {
  const response = await client.get<AnnotationFileListItem[]>(
    `/sessions/${sessionId}/videos/${videoId}/annotations`
  )
  return response.data
}

export async function getAnnotationDetail(
  annotationId: number
): Promise<AnnotationFileDetail> {
  const response = await client.get<AnnotationFileDetail>(`/annotations/${annotationId}`)
  return response.data
}

export function downloadAnnotationUrl(annotationId: number): string {
  return `${apiBaseUrl}/api/v1/annotations/${annotationId}/download`
}

export async function archiveAnnotation(
  annotationId: number
): Promise<{ id: number; status: string }> {
  const response = await client.post<{ id: number; status: string }>(
    `/annotations/${annotationId}/archive`
  )
  return response.data
}

export async function reparseAnnotation(
  annotationFileId: number,
  options?: Record<string, any> | null
): Promise<AnnotationIngestResponse> {
  const response = await client.post<AnnotationIngestResponse>(
    `/annotations/${annotationFileId}/parse`,
    options ?? {}
  )
  return response.data
}

export function resolveMediaUrl(path?: string): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${apiBaseUrl}${path}`
}

// ---- Kinematics Metrics APIs ----

export async function getAnnotationMetrics(normalizedAnnotationId: number): Promise<AnnotationMetricRead> {
  if (demoMode) {
    return {
      id: 1,
      normalized_annotation_id: normalizedAnnotationId,
      calculator: 'side_view_metrics',
      calculator_version: '1.0.0',
      schema_version: 'swim-side-kinematics.v1',
      metrics: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  }
  const response = await client.get<AnnotationMetricRead>(
    `/normalized-annotations/${normalizedAnnotationId}/metrics`
  )
  return response.data
}

export async function calculateMetrics(
  normalizedAnnotationId: number,
  persist: boolean = false,
  calculator: string = 'side_view_metrics'
): Promise<CalculateMetricsResponse> {
  if (demoMode) {
    return {
      annotation_metric_id: 1,
      persisted: persist,
      metrics: {}
    }
  }
  const response = await client.post<CalculateMetricsResponse>(
    `/normalized-annotations/${normalizedAnnotationId}/calculate-metrics`,
    null,
    { params: { persist, calculator } }
  )
  return response.data
}

// ---- Kinematic Artifacts APIs ----

export async function getKinematicArtifacts(annotationMetricId: number): Promise<KinematicArtifactSetRead> {
  if (demoMode) {
    return {
      id: 1,
      annotation_metric_id: annotationMetricId,
      artifacts: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  }
  const response = await client.get<KinematicArtifactSetRead>(
    `/annotation-metrics/${annotationMetricId}/artifacts`
  )
  return response.data
}

export async function generateKinematicArtifacts(
  annotationMetricId: number,
  force: boolean = false
): Promise<GenerateResponse> {
  if (demoMode) {
    return {
      artifact_set_id: 1,
      status: 'ready'
    }
  }
  const response = await client.post<GenerateResponse>(
    `/annotation-metrics/${annotationMetricId}/artifacts/generate`,
    null,
    { params: { force } }
  )
  return response.data
}

// ---- Review Findings APIs ----

export async function getReviewFindings(
  annotationMetricId: number,
  ruleSet: string = 'side_2d_kinematics_v1'
): Promise<ReviewFindingsReadResponse> {
  if (demoMode) {
    return {
      id: 1,
      annotation_metric_id: annotationMetricId,
      rule_set: ruleSet,
      findings: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  }
  const response = await client.get<ReviewFindingsReadResponse>(
    `/annotation-metrics/${annotationMetricId}/review-findings`,
    { params: { rule_set: ruleSet } }
  )
  return response.data
}

export async function generateReviewFindings(
  annotationMetricId: number,
  ruleSet: string = 'side_2d_kinematics_v1',
  force: boolean = false
): Promise<ReviewFindingsGenerateResponse> {
  if (demoMode) {
    return {
      finding_set_id: 1,
      status: 'ready'
    }
  }
  const response = await client.post<ReviewFindingsGenerateResponse>(
    `/annotation-metrics/${annotationMetricId}/review-findings/generate`,
    null,
    { params: { rule_set: ruleSet, force } }
  )
  return response.data
}

// ---- Five-Page Report API ----

export async function assembleFivePageReport(annotationMetricId: number): Promise<FivePageKinematicsReport> {
  if (demoMode) {
    return {
      schema_version: 'swim-report.v1',
      report_profile: 'side_2d_kinematics_5page_v1',
      generation_signature: 'demo',
      sections: [],
      summary: {
        title: '游泳专项技术分析报告'
      }
    }
  }
  const response = await client.post<FivePageKinematicsReport>(
    `/annotation-metrics/${annotationMetricId}/reports/five-page/assemble`
  )
  return response.data
}

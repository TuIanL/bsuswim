import axios from 'axios'
import type {
  AnalysisTask,
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
  TrainingMetadata,
  TrainingSession,
  User,
  VideoFile,
  WorkspaceData
} from '../types'
import {
  bindDemoSessionVideo,
  createDemoAthlete,
  createDemoSession,
  createDemoVideo,
  demoReport,
  demoTask,
  demoUser,
  demoWorkspace,
  getDemoAthlete,
  getDemoAthleteSessions,
  getDemoAthleteTrend,
  getDemoAthletes,
  getDemoSession,
  getDemoSessions,
  getDemoSessionVideos
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
  return []
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

export async function uploadVideo(file: File): Promise<VideoFile> {
  if (demoMode) {
    return createDemoVideo(file)
  }

  const form = new FormData()
  form.append('file', file)
  const response = await client.post<{ video: VideoFile }>('/videos/upload', form)
  return response.data.video
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
  video: VideoFile,
  input: Omit<SessionVideoCreateInput, 'video_file_id'>
): Promise<SessionVideo> {
  if (demoMode) return bindDemoSessionVideo(sessionId, video, { ...input, view_type: input.view_type })
  return bindSessionVideo(sessionId, { ...input, video_file_id: video.id })
}

export async function listSessionVideos(sessionId: number): Promise<SessionVideo[]> {
  if (demoMode) return getDemoSessionVideos(sessionId)
  const response = await client.get<SessionVideo[]>(`/sessions/${sessionId}/videos`)
  return response.data
}

export async function createAnalysisTask(videoId: number, metadata: TrainingMetadata): Promise<AnalysisTask> {
  if (demoMode) {
    return { ...demoTask, video_id: videoId, session_metadata: metadata }
  }
  const response = await client.post<AnalysisTask>('/tasks', { video_id: videoId, metadata })
  return response.data
}

export async function listTasks(): Promise<AnalysisTask[]> {
  if (demoMode) return [demoTask]
  const response = await client.get<AnalysisTask[]>('/tasks')
  return response.data
}

export async function getTask(taskId: number): Promise<AnalysisTask> {
  if (demoMode) return demoTask
  const response = await client.get<AnalysisTask>(`/tasks/${taskId}`)
  return response.data
}

export async function getWorkspace(taskId: number): Promise<WorkspaceData> {
  if (demoMode) return demoWorkspace
  const response = await client.get<WorkspaceData>(`/tasks/${taskId}/workspace`)
  return response.data
}

export async function getReport(taskId: number): Promise<ReportData> {
  if (demoMode) return demoReport
  const response = await client.get<ReportData>(`/reports/${taskId}`)
  return response.data
}

export function resolveMediaUrl(path?: string): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${apiBaseUrl}${path}`
}

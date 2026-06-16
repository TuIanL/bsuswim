import axios from 'axios'
import type { AnalysisTask, ReportData, TrainingMetadata, VideoFile, WorkspaceData } from '../types'
import { demoReport, demoTask, demoWorkspace } from './demoData'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
export const demoMode = !apiBaseUrl

const client = axios.create({
  baseURL: `${apiBaseUrl}/api/v1`
})

export async function uploadVideo(file: File): Promise<VideoFile> {
  if (demoMode) {
    return {
      id: 9001,
      original_filename: file.name,
      stored_filename: file.name,
      storage_path: file.name,
      mime_type: file.type,
      size_bytes: file.size,
      checksum_sha256: 'demo',
      created_at: new Date().toISOString(),
      playback_url: ''
    }
  }

  const form = new FormData()
  form.append('file', file)
  const response = await client.post<{ video: VideoFile }>('/videos', form)
  return response.data.video
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

import { computed, onUnmounted, ref, shallowRef } from 'vue'
import {
  getAnalysisStatus,
  getReport,
  getSession,
  ingestAnnotation,
  listAnnotations,
  listSessionVideos,
  listTasks,
  reparseAnnotation,
  retryAnalysisTask,
  submitAnalysis as submitBackendAnalysis
} from '../services/api'
import type {
  AnalysisTask,
  AnnotationFileListItem,
  Athlete,
  PipelineStep,
  ReportData,
  SessionVideo,
  TrainingSession,
  WorkflowPhase
} from '../types'
import {
  deriveReportFreshness,
  deriveWorkflowPhase,
  selectedAnnotationFromTasks
} from '../utils/kinematicsWorkflow'
import { getAthlete } from '../services/api'

const ANNOTATION_KINEMATICS = 'annotation_kinematics'
const ACTIVE_STATUSES = ['queued', 'processing', 'result_saving']

export function useKinematicsWorkflow(sessionId: number) {
  const loading = ref(true)
  const session = ref<TrainingSession | null>(null)
  const athlete = ref<Athlete | null>(null)
  const sideVideo = ref<SessionVideo | null>(null)
  const annotations = ref<AnnotationFileListItem[]>([])
  const latestTask = ref<AnalysisTask | null>(null)
  const report = shallowRef<ReportData | null>(null)
  const reportFreshness = ref<'none' | 'current' | 'stale'>('none')
  const selectedAnnotationId = ref<number | null>(null)
  const submitting = ref(false)
  const polling = ref(false)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  const hasSideVideo = computed(() => !!sideVideo.value)
  const pipelineProgress = computed<PipelineStep[]>(
    () => latestTask.value?.pipeline_progress?.steps ?? []
  )
  const activeTask = computed(() =>
    latestTask.value && ACTIVE_STATUSES.includes(latestTask.value.status) ? latestTask.value : null
  )
  const completedTask = computed(() =>
    latestTask.value && latestTask.value.status === 'completed' ? latestTask.value : null
  )
  const failedTask = computed(() =>
    latestTask.value && latestTask.value.status === 'failed' ? latestTask.value : null
  )

  const selectedAnnotation = computed(() =>
    annotations.value.find((a) => a.normalized_annotation_id === selectedAnnotationId.value) ?? null
  )

  const workflowPhase = computed<WorkflowPhase>(() =>
    deriveWorkflowPhase({
      hasSideVideo: hasSideVideo.value,
      annotations: annotations.value,
      activeTask: activeTask.value,
      completedTask: completedTask.value,
      failedTask: failedTask.value,
      reportExists: !!report.value || reportFreshness.value !== 'none'
    })
  )

  const canSubmit = computed(() => {
    const sel = selectedAnnotation.value
    if (!sideVideo.value) return false
    if (!sel || sel.status !== 'parsed' || sel.quality_status === 'invalid') return false
    if (!sel.analysis_readiness?.can_submit) return false
    if (activeTask.value) return false
    return true
  })

  const requiresAck = computed(
    () => selectedAnnotation.value?.analysis_readiness?.requires_acknowledgement ?? false
  )

  async function loadSessionVideos() {
    const videos = await listSessionVideos(sessionId)
    sideVideo.value = videos.find((v) => v.view_type === 'side') ?? null
  }

  async function loadAnnotations() {
    if (!sideVideo.value?.video_file_id) {
      annotations.value = []
      return
    }
    annotations.value = await listAnnotations(sessionId, sideVideo.value.video_file_id)
  }

  async function loadLatestTask() {
    const tasks = await listTasks({
      session_id: sessionId,
      pipeline_type: ANNOTATION_KINEMATICS,
      limit: 1
    })
    latestTask.value = tasks[0] ?? null
  }

  async function loadReport() {
    try {
      const data = await getReport(sessionId)
      report.value = data
      const taskInput = (data as any)?.report?.task_input
        ?? (latestTask.value?.request_payload?.analysis_input)
      const reportTaskAnnotationId = (latestTask.value?.request_payload?.analysis_input?.annotation_id) ?? null
      const reportTaskRevision = (latestTask.value?.request_payload?.analysis_input?.annotation_revision) ?? null
      reportFreshness.value = deriveReportFreshness({
        selectedAnnotationId: selectedAnnotationId.value,
        selectedRevision: selectedAnnotation.value?.normalized_revision ?? null,
        reportTaskAnnotationId,
        reportTaskRevision
      })
    } catch {
      report.value = null
      reportFreshness.value = 'none'
    }
  }

  function restoreSelection() {
    const found = selectedAnnotationFromTasks(annotations.value, activeTask.value, completedTask.value)
    selectedAnnotationId.value = found?.normalized_annotation_id ?? null
  }

  async function refresh() {
    await Promise.all([loadSessionVideos(), loadLatestTask()])
    await loadAnnotations()
    restoreSelection()
    await loadReport()
  }

  function startPolling() {
    if (pollTimer) return
    polling.value = true
    pollTimer = setInterval(async () => {
      try {
        if (latestTask.value) {
          const status = await getAnalysisStatus(latestTask.value.id)
          latestTask.value = { ...latestTask.value, ...status } as AnalysisTask
        } else {
          await loadLatestTask()
        }
        if (activeTask.value) {
          await loadReport()
        } else {
          stopPolling()
        }
      } catch {
        stopPolling()
      }
    }, 2500)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    polling.value = false
  }

  async function init() {
    loading.value = true
    try {
      session.value = await getSession(sessionId)
      if (session.value) athlete.value = await getAthlete(session.value.athlete_id)
      await refresh()
      if (activeTask.value) startPolling()
    } finally {
      loading.value = false
    }
  }

  async function uploadVideoFile(file: File, meta: { fps?: number; resolution?: string; syncOffsetMs?: number }) {
    // 复用现有上传逻辑（由组件调用 api.uploadVideo + bindUploadedSessionVideo）
  }

  async function ingestCvat(file: File) {
    if (!sideVideo.value?.video_file_id) throw new Error('请先绑定侧面视频')
    const result = await ingestAnnotation(sessionId, sideVideo.value.video_file_id, file, 'cvat')
    await loadAnnotations()
    restoreSelection()
    return result
  }

  async function reparse(fileId: number) {
    const result = await reparseAnnotation(fileId)
    await loadAnnotations()
    restoreSelection()
    return result
  }

  async function submit(acknowledge: boolean) {
    if (!canSubmit.value) throw new Error('当前不满足提交条件')
    submitting.value = true
    try {
      const task = await submitBackendAnalysis(sessionId, {
        normalized_annotation_id: selectedAnnotationId.value ?? undefined,
        acknowledge_quality_warnings: acknowledge,
        pipeline_type: ANNOTATION_KINEMATICS,
        pipeline_version: 'side_2d_v1'
      })
      latestTask.value = task
      startPolling()
      return task
    } finally {
      submitting.value = false
    }
  }

  async function retry() {
    if (!failedTask.value) return
    const task = await retryAnalysisTask(failedTask.value.id)
    latestTask.value = task
    startPolling()
    return task
  }

  async function resubmit() {
    if (!selectedAnnotationId.value) throw new Error('请先选择标注')
    const task = await submitBackendAnalysis(sessionId, {
      normalized_annotation_id: selectedAnnotationId.value,
      acknowledge_quality_warnings: true,
      pipeline_type: ANNOTATION_KINEMATICS,
      pipeline_version: 'side_2d_v1'
    })
    latestTask.value = task
    startPolling()
    return task
  }

  onUnmounted(stopPolling)

  return {
    loading,
    session,
    athlete,
    sideVideo,
    annotations,
    latestTask,
    report,
    reportFreshness,
    selectedAnnotationId,
    selectedAnnotation,
    submitting,
    polling,
    hasSideVideo,
    pipelineProgress,
    activeTask,
    completedTask,
    failedTask,
    workflowPhase,
    canSubmit,
    requiresAck,
    init,
    refresh,
    ingestCvat,
    reparse,
    submit,
    retry,
    resubmit,
    startPolling,
    stopPolling
  }
}

import type {
  AnalysisTask,
  AnnotationFileListItem,
  KinematicsModuleKey,
  KinematicsModuleReadiness,
  ModuleReadinessStatus,
  PipelineProgress,
  ReportFreshness,
  SessionVideo,
  WorkflowPhase
} from '../types'

// 流水线阶段的中文展示名称。顺序由后端 pipeline_progress.steps 决定，前端不维护规范顺序。
export const PIPELINE_STAGE_LABELS: Record<string, string> = {
  validating_input: '校验视频与标注',
  calculating_metrics: '计算四类运动学指标',
  generating_artifacts: '生成关键帧与图表',
  running_findings: '生成待复核发现',
  saving_result: '保存分析结果',
  assembling_report: '装配五页报告',
  completed: '报告生成完成',
  model_inference: '模型推理分析',
  queued: '等待执行'
}

export function stageLabel(key: string | null | undefined): string {
  if (!key) return ''
  return PIPELINE_STAGE_LABELS[key] ?? key
}

export const MODULE_LABELS: Record<KinematicsModuleKey, string> = {
  body_posture: '身体姿态与稳定性',
  upper_limb: '上肢运动学',
  lower_limb: '下肢运动学',
  head_trunk: '头部与躯干控制'
}

export const MODULE_STATUS_LABELS: Record<ModuleReadinessStatus, string> = {
  ready: '可分析',
  degraded: '可分析（降级）',
  blocked: '当前不可分析'
}

export function moduleStatusType(status: ModuleReadinessStatus): 'success' | 'warning' | 'danger' {
  return status === 'ready' ? 'success' : status === 'degraded' ? 'warning' : 'danger'
}

// 根据服务端数据推导当前工作流阶段（design Decision 2）
export function deriveWorkflowPhase(input: {
  hasSideVideo: boolean
  annotations: AnnotationFileListItem[]
  activeTask?: AnalysisTask | null
  completedTask?: AnalysisTask | null
  failedTask?: AnalysisTask | null
  reportExists: boolean
}): WorkflowPhase {
  const { hasSideVideo, annotations, activeTask, completedTask, failedTask, reportExists } = input

  if (failedTask && failedTask.status === 'failed') return 'analysis_failed'
  if (activeTask) {
    if (['queued', 'processing', 'result_saving'].includes(activeTask.status)) return 'analysis_running'
  }
  if (completedTask && completedTask.status === 'completed') {
    if (!reportExists) return 'analysis_failed' // 合成 REPORT_METADATA_MISSING
    return 'report_ready'
  }
  const submittable = annotations.some(
    (a) => a.status === 'parsed' && a.quality_status && a.quality_status !== 'invalid' && a.normalized_annotation_id != null
  )
  const processing = annotations.some((a) => a.status === 'uploaded' || a.status === 'parse_failed')
  if (submittable) return 'ready_to_analyze'
  if (annotations.length > 0 || processing) return 'annotation_review'
  if (hasSideVideo) return 'annotation_required'
  return 'video_required'
}

// 报告新鲜度基于 ReportMetadata.task_id 所指任务的 annotation revision（design Decision 20）
export function deriveReportFreshness(input: {
  selectedAnnotationId: number | null
  selectedRevision: number | null
  reportTaskAnnotationId: number | null
  reportTaskRevision: number | null
}): ReportFreshness {
  const { selectedAnnotationId, selectedRevision, reportTaskAnnotationId, reportTaskRevision } = input
  if (reportTaskAnnotationId == null) return 'none'
  if (
    selectedAnnotationId === reportTaskAnnotationId &&
    selectedRevision === reportTaskRevision
  ) {
    return 'current'
  }
  return 'stale'
}

export function selectedAnnotationFromTasks(
  annotations: AnnotationFileListItem[],
  activeTask?: AnalysisTask | null,
  completedTask?: AnalysisTask | null
): AnnotationFileListItem | null {
  const preferredId = activeTask?.request_payload?.analysis_input?.annotation_id
    ?? completedTask?.request_payload?.analysis_input?.annotation_id
  if (preferredId != null) {
    const found = annotations.find((a) => a.normalized_annotation_id === preferredId)
    if (found && found.status === 'parsed' && found.quality_status !== 'invalid') return found
  }
  const submittable = annotations
    .filter((a) => a.status === 'parsed' && a.quality_status && a.quality_status !== 'invalid' && a.normalized_annotation_id != null)
    .sort((a, b) => (b.uploaded_at || '').localeCompare(a.uploaded_at || '') || b.id - a.id)
  return submittable[0] ?? null
}

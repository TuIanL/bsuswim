import type { AnalysisTask, AnnotationFileListItem, AnalysisStatus, PipelineProgress, KinematicsModuleReadiness } from '../types'

const DEFAULT_PROGRESS: PipelineProgress = {
  pipeline_type: 'annotation_kinematics',
  pipeline_version: 'side_2d_v1',
  attempt_count: 1,
  current_stage: 'assembling_report',
  failed_stage: null,
  error_code: null,
  warnings: [],
  steps: [
    { key: 'uploading_video', status: 'completed', progress: 100, details: {} },
    { key: 'parsing_annotation', status: 'completed', progress: 100, details: {} },
    { key: 'validating_input', status: 'completed', progress: 100, details: {} },
    { key: 'computing_metrics', status: 'completed', progress: 100, details: {} },
    { key: 'generating_artifacts', status: 'completed', progress: 100, details: {} },
    { key: 'assembling_report', status: 'completed', progress: 100, details: {} }
  ]
}

export function makeAnnotation(over: Partial<AnnotationFileListItem> = {}): AnnotationFileListItem {
  const moduleReadiness: KinematicsModuleReadiness = {
    body_posture: 'ready',
    upper_limb: 'ready',
    lower_limb: 'ready',
    head_trunk: 'degraded'
  }
  return {
    id: 1,
    session_video_id: 1,
    source: 'cvat',
    view_type: 'side',
    file_type: 'xml',
    version: 1,
    status: 'parsed',
    original_filename: 'skeleton.xml',
    annotation_fps: 30,
    uploaded_at: '2026-07-19T00:00:00Z',
    quality_status: 'valid',
    normalized_annotation_id: 1,
    normalized_revision: 1,
    analysis_readiness: { can_submit: true, requires_acknowledgement: false, blocking_issue_count: 0, affected_modules: [] },
    parse_summary: { events_count: 1, keypoint_frames_count: 96, trajectories_count: 17, manual_tags_count: 0 },
    quality: { schema_version: 'annotation-quality.v2', status: 'valid', score: 90, module_readiness: {} },
    kinematics_module_readiness: moduleReadiness,
    parse_warnings: [],
    parse_error: null,
    ...over
  }
}

export function makeTask(over: Partial<AnalysisTask> = {}): AnalysisTask {
  return {
    id: 1,
    session_id: 1,
    status: 'queued',
    progress: 0,
    stage: 'queued',
    request_payload: { analysis_input: { annotation_id: 1, annotation_revision: 1 } },
    error_message: null,
    created_at: '2026-07-19T00:00:00Z',
    updated_at: '2026-07-19T00:00:00Z',
    completed_at: null,
    pipeline_type: 'annotation_kinematics',
    pipeline_version: 'side_2d_v1',
    attempt_count: 1,
    failed_stage: null,
    error_code: null,
    pipeline_progress: DEFAULT_PROGRESS,
    actions: ['workspace', 'report'],
    ...over
  }
}

export function makeStatusFromTask(task: AnalysisTask): AnalysisStatus {
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
    pipeline_progress: task.pipeline_progress,
    actions: task.actions,
    created_at: task.created_at,
    updated_at: task.updated_at,
    completed_at: task.completed_at
  }
}

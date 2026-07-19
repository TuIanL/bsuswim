import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { useKinematicsWorkflow } from '../composables/useKinematicsWorkflow'
import { makeAnnotation, makeTask } from '../test/factories'

// 全量 mock api 层，按用例注入返回值
const api = vi.hoisted(() => ({
  getSession: vi.fn(),
  getAthlete: vi.fn(),
  listSessionVideos: vi.fn(),
  listTasks: vi.fn(),
  listAnnotations: vi.fn(),
  getReport: vi.fn(),
  getAnalysisStatus: vi.fn(),
  submitAnalysis: vi.fn(),
  retryAnalysisTask: vi.fn(),
  ingestAnnotation: vi.fn(),
  reparseAnnotation: vi.fn()
}))

vi.mock('../services/api', () => ({
  getSession: api.getSession,
  getAthlete: api.getAthlete,
  listSessionVideos: api.listSessionVideos,
  listTasks: api.listTasks,
  listAnnotations: api.listAnnotations,
  getReport: api.getReport,
  getAnalysisStatus: api.getAnalysisStatus,
  submitAnalysis: api.submitAnalysis,
  retryAnalysisTask: api.retryAnalysisTask,
  ingestAnnotation: api.ingestAnnotation,
  reparseAnnotation: api.reparseAnnotation
}))

beforeEach(() => {
  vi.clearAllMocks()
  api.getAthlete.mockResolvedValue({ id: 1, name: 'A' })
  api.listSessionVideos.mockResolvedValue([])
  api.listTasks.mockResolvedValue([])
  api.listAnnotations.mockResolvedValue([])
  api.getReport.mockRejectedValue(new Error('no report'))
})

function boot() {
  const wf = useKinematicsWorkflow(1)
  return wf
}

describe('useKinematicsWorkflow 工作流阶段推导 (16.8–16.16)', () => {
  it('16.8 无 side 视频 → video_required', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    await wf.init()
    expect(wf.workflowPhase.value).toBe('video_required')
  })

  it('16.9 有 side 视频、无标注 → annotation_required', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listAnnotations.mockResolvedValue([])
    await wf.init()
    expect(wf.hasSideVideo.value).toBe(true)
    expect(wf.workflowPhase.value).toBe('annotation_required')
  })

  it('16.10 存在可提交标注 → ready_to_analyze', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listAnnotations.mockResolvedValue([makeAnnotation({ normalized_annotation_id: 1, quality_status: 'valid', analysis_readiness: { can_submit: true, requires_acknowledgement: false, blocking_issue_count: 0, affected_modules: [] } })])
    await wf.init()
    expect(wf.workflowPhase.value).toBe('ready_to_analyze')
    expect(wf.canSubmit.value).toBe(true)
  })

  it('16.11 warning 标注需确认、invalid 标注阻断生成', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    // warning 标注
    api.listAnnotations.mockResolvedValue([
      makeAnnotation({
        normalized_annotation_id: 1,
        quality_status: 'warning',
        analysis_readiness: { can_submit: true, requires_acknowledgement: true, blocking_issue_count: 0, affected_modules: ['upper_limb'] }
      })
    ])
    await wf.init()
    expect(wf.canSubmit.value).toBe(true)
    expect(wf.requiresAck.value).toBe(true)

    // invalid 标注阻断
    api.listAnnotations.mockResolvedValue([
      makeAnnotation({ normalized_annotation_id: 2, quality_status: 'invalid', analysis_readiness: { can_submit: false, requires_acknowledgement: false, blocking_issue_count: 1, affected_modules: [] } })
    ])
    await wf.init()
    expect(wf.canSubmit.value).toBe(false)
  })

  it('16.12 运行中任务刷新后恢复轮询', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listTasks.mockResolvedValue([makeTask({ status: 'processing', pipeline_progress: { ...makeTask().pipeline_progress!, current_stage: 'computing_metrics' } })])
    await wf.init()
    expect(wf.workflowPhase.value).toBe('analysis_running')
    expect(wf.activeTask.value).not.toBeNull()
    expect(wf.polling.value).toBe(true)
  })

  it('16.13 失败任务展示失败阶段与正确动作', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listTasks.mockResolvedValue([
      makeTask({ status: 'failed', failed_stage: 'generating_artifacts', error_code: 'ARTIFACT_GENERATION_FAILED', actions: ['retry', 'details'] })
    ])
    await wf.init()
    expect(wf.workflowPhase.value).toBe('analysis_failed')
    expect(wf.failedTask.value?.error_code).toBe('ARTIFACT_GENERATION_FAILED')
    expect(wf.failedTask.value?.actions).toContain('retry')
  })

  it('16.14 完成任务暴露报告动作', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listTasks.mockResolvedValue([makeTask({ status: 'completed', actions: ['workspace', 'report'] })])
    api.getReport.mockResolvedValue({ report: { task_input: { annotation_id: 1, annotation_revision: 1 } } })
    await wf.init()
    expect(wf.workflowPhase.value).toBe('report_ready')
    expect(wf.completedTask.value?.actions).toContain('report')
  })

  it('16.15 非 side 机位保持非交互（不影响就绪状态）', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    // 仅存在 front 视角，无 side
    api.listSessionVideos.mockResolvedValue([{ id: 2, video_file_id: 98, view_type: 'front' }])
    api.listAnnotations.mockResolvedValue([])
    await wf.init()
    expect(wf.hasSideVideo.value).toBe(false)
    expect(wf.workflowPhase.value).toBe('video_required')
  })

  it('报告缺失（completed 但 getReport 404）→ analysis_failed + resubmit', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listTasks.mockResolvedValue([
      makeTask({ status: 'completed', error_code: 'REPORT_METADATA_MISSING', failed_stage: 'assembling_report', actions: ['resubmit', 'details'] })
    ])
    api.getReport.mockRejectedValue(new Error('404'))
    await wf.init()
    expect(wf.workflowPhase.value).toBe('analysis_failed')
    expect(wf.latestTask.value?.error_code).toBe('REPORT_METADATA_MISSING')
    expect(wf.latestTask.value?.actions).toContain('resubmit')
  })

  it('16.16 端到端链路：提交 annotation pipeline 后进入 running', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listAnnotations.mockResolvedValue([makeAnnotation({ normalized_annotation_id: 7, quality_status: 'valid', analysis_readiness: { can_submit: true, requires_acknowledgement: false, blocking_issue_count: 0, affected_modules: [] } })])
    await wf.init()
    wf.selectedAnnotationId.value = 7
    expect(wf.canSubmit.value).toBe(true)
    const created = makeTask({ id: 50, status: 'queued' })
    api.submitAnalysis.mockResolvedValue(created)
    const task = await wf.submit(false)
    expect(task.id).toBe(50)
    expect(api.submitAnalysis).toHaveBeenCalledWith(1, expect.objectContaining({ pipeline_type: 'annotation_kinematics', pipeline_version: 'side_2d_v1', normalized_annotation_id: 7 }))
    expect(wf.activeTask.value).not.toBeNull()
  })

  it('restoreSelection 优先选中 active 任务所用标注，不选中 invalid', async () => {
    const wf = boot()
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1 })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    api.listAnnotations.mockResolvedValue([
      makeAnnotation({ id: 1, normalized_annotation_id: 1, quality_status: 'valid' }),
      makeAnnotation({ id: 2, normalized_annotation_id: 2, quality_status: 'invalid' })
    ])
    api.listTasks.mockResolvedValue([makeTask({ id: 5, status: 'processing', request_payload: { analysis_input: { annotation_id: 1, annotation_revision: 1 } } })])
    await wf.init()
    expect(wf.selectedAnnotationId.value).toBe(1)
    expect(wf.selectedAnnotation.value?.quality_status).not.toBe('invalid')
  })
})

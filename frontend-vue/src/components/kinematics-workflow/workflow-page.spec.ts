import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import KinematicsWorkflowPage from './KinematicsWorkflowPage.vue'

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

vi.mock('../../services/api', () => ({
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

const router = createRouter({ history: createWebHistory(), routes: [{ path: '/', component: { template: '<div/>' } }] })

beforeEach(() => {
  vi.clearAllMocks()
  api.getAthlete.mockResolvedValue({ id: 1, name: 'A' })
  api.listSessionVideos.mockResolvedValue([])
  api.listTasks.mockResolvedValue([])
  api.listAnnotations.mockResolvedValue([])
  api.getReport.mockRejectedValue(new Error('no'))
})

async function mountPage() {
  const wrapper = mount(KinematicsWorkflowPage, {
    props: { sessionId: '1' },
    global: { plugins: [router] }
  })
  await flush()
  return wrapper
}

function flush() {
  return new Promise((r) => setTimeout(r, 0))
}

describe('KinematicsWorkflowPage (8.5 绑定前阻断后续步骤)', () => {
  it('无 side 视频时不渲染 CVAT 标注步骤', async () => {
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1, title: 'S' })
    const wrapper = await mountPage()
    // 标注步骤块被阻断：CVAT 标注与质量 标题不应出现可操作内容
    expect(wrapper.text()).toContain('请先绑定侧面视频')
    expect(wrapper.findComponent({ name: 'CvatAnnotationStep' }).exists()).toBe(false)
  })

  it('有 side 视频时渲染 CVAT 标注步骤', async () => {
    api.getSession.mockResolvedValue({ id: 1, athlete_id: 1, title: 'S' })
    api.listSessionVideos.mockResolvedValue([{ id: 1, video_file_id: 99, view_type: 'side' }])
    const wrapper = await mountPage()
    expect(wrapper.findComponent({ name: 'CvatAnnotationStep' }).exists()).toBe(true)
    expect(wrapper.text()).not.toContain('请先绑定侧面视频')
  })
})

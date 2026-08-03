import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// 所有 view 替换为 stub，路由测试只关注守卫行为，不渲染真实页面
const { stub } = vi.hoisted(() => ({
  stub: () => ({ default: { template: '<div class="stub" />' } }),
}))

vi.mock('./views/LoginView.vue', stub)
vi.mock('./views/RegisterView.vue', stub)
vi.mock('./views/AthletesView.vue', stub)
vi.mock('./views/AthleteProfileView.vue', stub)
vi.mock('./views/CreateSessionView.vue', stub)
vi.mock('./views/SessionUploadView.vue', stub)
vi.mock('./views/TasksView.vue', stub)
vi.mock('./views/WorkspaceView.vue', stub)
vi.mock('./views/ReportView.vue', stub)
vi.mock('./views/PrintReportView.vue', stub)

function mockApi(demoMode: boolean) {
  vi.doMock('./services/api', () => ({
    demoMode,
    setAuthToken: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn().mockResolvedValue({
      id: 1,
      username: 'demo',
      full_name: 'Demo',
      role: 'coach',
    }),
  }))
}

async function loadRouter() {
  vi.resetModules()
  setActivePinia(createPinia())
  const { router } = await import('./router')
  return router
}

describe('router guard（非 demo 模式）', () => {
  beforeEach(() => mockApi(false))

  it('未登录访问 print 路由放行', async () => {
    const router = await loadRouter()
    await router.push('/reports/1/print')
    expect(router.currentRoute.value.path).toBe('/reports/1/print')
    expect(router.currentRoute.value.meta.public).toBe(true)
  })

  it('未登录访问报告主路由重定向到 /login', async () => {
    const router = await loadRouter()
    await router.push('/reports/1')
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/reports/1')
  })
})

describe('router guard（demo 模式）', () => {
  beforeEach(() => mockApi(true))

  it('demo 模式访问 print 路由放行', async () => {
    const router = await loadRouter()
    await router.push('/reports/1/print')
    expect(router.currentRoute.value.path).toBe('/reports/1/print')
  })
})

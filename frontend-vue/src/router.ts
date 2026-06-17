import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import RegisterView from './views/RegisterView.vue'
import AthletesView from './views/AthletesView.vue'
import AthleteProfileView from './views/AthleteProfileView.vue'
import CreateSessionView from './views/CreateSessionView.vue'
import SessionUploadView from './views/SessionUploadView.vue'
import TasksView from './views/TasksView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import ReportView from './views/ReportView.vue'
import { demoMode } from './services/api'
import { useAuthStore } from './stores/auth'

const authRoutes = new Set(['/login', '/register'])

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/athletes' },
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/register', component: RegisterView, meta: { public: true } },
    { path: '/athletes', component: AthletesView },
    { path: '/athletes/:athleteId', component: AthleteProfileView, props: true },
    { path: '/sessions/new', component: CreateSessionView },
    { path: '/sessions/:sessionId/upload', component: SessionUploadView, props: true },
    { path: '/upload', redirect: '/sessions/new' },
    { path: '/tasks', component: TasksView },
    { path: '/workspace/:taskId', component: WorkspaceView, props: true },
    { path: '/reports/:sessionId', component: ReportView, props: true }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.restore()

  if (authRoutes.has(to.path) && auth.isAuthenticated) {
    return '/athletes'
  }

  if (!to.meta.public && !auth.isAuthenticated && !demoMode) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

import { createRouter, createWebHistory } from 'vue-router'
import UploadView from './views/UploadView.vue'
import TasksView from './views/TasksView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import ReportView from './views/ReportView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/upload' },
    { path: '/upload', component: UploadView },
    { path: '/tasks', component: TasksView },
    { path: '/workspace/:taskId', component: WorkspaceView, props: true },
    { path: '/reports/:taskId', component: ReportView, props: true }
  ]
})

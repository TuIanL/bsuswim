import { defineStore } from 'pinia'
import type { AnalysisTask } from '../types'
import { listTasks } from '../services/api'

export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [] as AnalysisTask[],
    loading: false
  }),
  actions: {
    async refresh() {
      this.loading = true
      try {
        this.tasks = await listTasks()
      } finally {
        this.loading = false
      }
    }
  }
})

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>测试任务</h1>
        <p>查看训练记录状态，继续上传侧面视频，或进入已有工作台与报告。</p>
      </div>
      <div class="action-row">
        <el-button @click="$router.push('/sessions/new')">创建测试</el-button>
        <el-button type="primary" @click="load">刷新</el-button>
      </div>
    </div>

    <el-table class="section" v-loading="loading" :data="rows">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="测试任务" min-width="220" />
      <el-table-column label="泳姿" width="110">
        <template #default="{ row }">{{ strokeLabel(row.stroke_type) }}</template>
      </el-table-column>
      <el-table-column label="距离" width="90">
        <template #default="{ row }">{{ row.distance_m ? `${row.distance_m}m` : '-' }}</template>
      </el-table-column>
      <el-table-column prop="session_date" label="日期" width="130" />
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="tagType(row.displayStatus)">{{ statusLabel(row.displayStatus) }}</el-tag>
          <div v-if="row.task?.error_message" class="muted-text">{{ row.task.error_message }}</div>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="160">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="380" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/sessions/${row.id}/upload`)">上传</el-button>
          <el-button size="small" :disabled="!row.task" @click="$router.push(`/workspace/${row.task.id}`)">工作台</el-button>
          <el-button size="small" :disabled="row.displayStatus !== 'completed'" @click="$router.push(`/reports/${row.id}`)">报告</el-button>
          <el-button size="small" type="danger" plain :loading="deletingId === row.id" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteSession, listSessions, listTasks } from '../services/api'
import type { AnalysisTask, TaskStatus, TrainingSessionStatus, TrainingSession } from '../types'

const sessions = ref<TrainingSession[]>([])
const tasks = ref<AnalysisTask[]>([])
const loading = ref(false)
const deletingId = ref<number | null>(null)
let timer = 0

type DisplayStatus = TrainingSessionStatus | TaskStatus

const rows = computed(() =>
  sessions.value.map((session) => {
    const task = tasks.value
      .filter((item) => item.session_id === session.id)
      .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))[0]
    return {
      ...session,
      task,
      displayStatus: task?.status || session.status,
      progress: task?.progress ?? progressOf(session.status)
    }
  })
)

async function load() {
  loading.value = true
  try {
    const [sessionRows, taskRows] = await Promise.all([listSessions(), listTasks()])
    sessions.value = sessionRows
    tasks.value = taskRows
  } finally {
    loading.value = false
  }
}

async function remove(row: TrainingSession) {
  try {
    await ElMessageBox.confirm(
      `将永久删除“${row.title}”及其视频、标注、分析结果和报告，且无法恢复。`,
      '删除测试任务',
      { confirmButtonText: '永久删除', cancelButtonText: '取消', type: 'warning', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }

  deletingId.value = row.id
  try {
    await deleteSession(row.id)
    await load()
    ElMessage.success('测试任务已删除')
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    ElMessage.error(detail?.message || detail || error?.message || '删除测试任务失败')
  } finally {
    deletingId.value = null
  }
}

function tagType(status: DisplayStatus) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'analyzing' || status === 'queued' || status === 'processing' || status === 'result_saving') return 'warning'
  return 'info'
}

function progressOf(status: DisplayStatus) {
  return { draft: 15, video_uploaded: 45, analyzing: 72, uploaded: 40, queued: 8, processing: 55, result_saving: 85, completed: 100, failed: 100 }[status]
}

function statusLabel(status: DisplayStatus) {
  return {
    draft: '待上传',
    video_uploaded: '已上传',
    analyzing: '分析中',
    uploaded: '已上传',
    queued: '排队中',
    processing: '分析中',
    result_saving: '保存结果',
    completed: '已完成',
    failed: '失败'
  }[status]
}

function strokeLabel(value: string) {
  return { freestyle: '自由泳', breaststroke: '蛙泳', backstroke: '仰泳', butterfly: '蝶泳', mixed: '混合' }[value] || value
}

onMounted(async () => {
  await load()
  timer = window.setInterval(load, 5000)
})

onUnmounted(() => window.clearInterval(timer))
</script>

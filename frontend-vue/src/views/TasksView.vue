<template>
  <div>
    <div class="page-head">
      <div>
        <h1>测试任务</h1>
        <p>查看训练记录状态，继续上传多机位视频，或进入已有工作台与报告。</p>
      </div>
      <div class="action-row">
        <el-button @click="$router.push('/sessions/new')">创建测试</el-button>
        <el-button type="primary" @click="load">刷新</el-button>
      </div>
    </div>

    <el-table class="section" v-loading="loading" :data="sessions">
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
          <el-tag :type="tagType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="160">
        <template #default="{ row }">
          <el-progress :percentage="progressOf(row.status)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/sessions/${row.id}/upload`)">上传</el-button>
          <el-button size="small" @click="$router.push('/workspace/1001')">工作台</el-button>
          <el-button size="small" :disabled="row.status !== 'completed'" @click="$router.push('/reports/1001')">报告</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listSessions } from '../services/api'
import type { TrainingSessionStatus, TrainingSession } from '../types'

const sessions = ref<TrainingSession[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    sessions.value = await listSessions()
  } finally {
    loading.value = false
  }
}

function tagType(status: TrainingSessionStatus) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'analyzing') return 'warning'
  return 'info'
}

function progressOf(status: TrainingSessionStatus) {
  return { draft: 15, video_uploaded: 45, analyzing: 72, completed: 100, failed: 100 }[status]
}

function strokeLabel(value: string) {
  return { freestyle: '自由泳', breaststroke: '蛙泳', backstroke: '仰泳', butterfly: '蝶泳', mixed: '混合' }[value] || value
}

onMounted(load)
</script>
